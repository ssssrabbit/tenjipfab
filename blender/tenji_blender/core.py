"""Blender-side core: build braille dot meshes projected onto a target surface, and verify them.

Everything here takes plain arguments so it can be driven from the UI, tests, or the bridge.
"""
from __future__ import annotations

import json
import math

import bpy
from mathutils import Matrix, Vector

from tenji.braille import SPACE_MARK
from tenji.geometry import Dims, DotPos, dome_mesh, dome_smooth_flags, layout_dots
from tenji.japanese import mapping_from_fields, resolve_all
from tenji.layout import build_flat_cells, layout_fixed_width, split_cells_with_rules

DOTS_OBJECT = "Tenji_Dots"


def bu_per_mm(scene, target=None, print_size_mm: float = 0.0) -> float:
    """点字寸法(mm)をBlender単位へ換算する係数。

    print_size_mm > 0: 対象モデルの最長辺を「出力時にこのmmにする」とみなす(3Dプリンター出力サイズに合わせて
    モデルを拡縮しても、点字は出力後に指定mmになる)。0 ならシーン単位(unit scale)をそのまま使う。
    """
    if print_size_mm > 0 and target is not None:
        longest = max(target.dimensions)
        if longest <= 0:
            raise ValueError("target has zero size")
        return longest / print_size_mm
    return 0.001 / scene.unit_settings.scale_length


def unicode_braille(dots) -> str:
    return chr(0x2800 + sum(1 << i for i, on in enumerate(dots) if on))


def words_to_lines(words, cells_per_line: int, mode: str = "FIXED"):
    """words: iterable of (orig, reading, pos, is_para, attach_prev, gap) -> list of lines, each a list of FlatCell.

    mode: "FIXED"=1行のセル数で横に並べて折り返す / "RULES"=点字の規則(語を行にまたがせない)で折り返す
    """
    mapped = [mapping_from_fields(o, r, p, para, att, gap) for o, r, p, para, att, gap in words]
    resolve_all(mapped)
    flat = build_flat_cells(mapped)
    if mode == "RULES":
        return split_cells_with_rules(flat, cells_per_line)
    return layout_fixed_width(flat, cells_per_line)


def _basis(normal: Vector, x_ref: Vector) -> Matrix:
    x = x_ref - normal * x_ref.dot(normal)
    if x.length < 1e-6:
        x = Vector((0, 1, 0)) - normal * normal.y
    x.normalize()
    y = normal.cross(x)
    return Matrix((x, y, normal)).transposed()  # columns = x, y, z


def generate(scene, *, lines, target, frame, dims: Dims, align="LEFT", k: float | None = None,
             max_distance_mm=1000.0, warn_angle_deg=45.0, dots=None) -> dict:
    """Project dots onto `target` along -Z of `frame`. `k` = BU per mm (see bu_per_mm).

    `dots`: the working mesh object to update (None -> a new object is created). Returns a report dict
    whose "obj" is the object holding the dots."""
    if k is None:
        k = bu_per_mm(scene)
    cell_dots = [[c.dots for c in line] for line in lines]
    placements: list[DotPos] = layout_dots(cell_dots, dims, align)

    depsgraph = bpy.context.evaluated_depsgraph_get()
    target_eval = target.evaluated_get(depsgraph)
    t_inv = target.matrix_world.inverted()
    t_nrm = t_inv.transposed().to_3x3()
    fm = frame.matrix_world
    ray_dir_w = (fm.to_3x3() @ Vector((0, 0, -1))).normalized()
    x_ref = (fm.to_3x3() @ Vector((1, 0, 0))).normalized()
    d_local = t_inv.to_3x3() @ ray_dir_w
    scale = d_local.length
    d_local.normalize()
    dist_local = max_distance_mm * k * scale

    verts_t, faces_t = dome_mesh(Dims(**{**dims.__dict__, **{
        f: getattr(dims, f) * k for f in ("dot_diameter", "dot_height", "embed")}}))

    verts: list[tuple] = []
    faces: list[tuple] = []
    missed: list[tuple[int, int, int]] = []
    steep: list[dict] = []
    max_angle = 0.0
    for dp in placements:
        origin_w = fm @ Vector((dp.x * k, dp.y * k, 0.0))
        ok, loc, nor, _ = target_eval.ray_cast(t_inv @ origin_w, d_local, distance=dist_local)
        if not ok:
            missed.append((dp.line, dp.cell, dp.dot_no))
            continue
        hit_w = target.matrix_world @ loc
        n_w = (t_nrm @ nor).normalized()
        if n_w.dot(ray_dir_w) > 0:      # 裏面ヒットは法線を反転
            n_w = -n_w
        angle = math.degrees(math.acos(max(-1.0, min(1.0, -n_w.dot(ray_dir_w)))))
        max_angle = max(max_angle, angle)
        if angle > warn_angle_deg:
            steep.append({"line": dp.line, "cell": dp.cell, "dot": dp.dot_no, "angle": round(angle, 1)})
        m = _basis(n_w, x_ref)
        base = len(verts)
        verts.extend(tuple(hit_w + m @ Vector(v)) for v in verts_t)
        faces.extend(tuple(base + i for i in f) for f in faces_t)

    mesh = bpy.data.meshes.new(DOTS_OBJECT)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    flags = dome_smooth_flags(Dims(**{**dims.__dict__, **{f: getattr(dims, f) * k for f in ("dot_diameter", "dot_height", "embed")}}))
    if len(mesh.polygons) == len(flags) * (len(placements) - len(missed)):
        mesh.polygons.foreach_set("use_smooth", flags * (len(placements) - len(missed)))   # ドームだけ滑らかに
        mesh.update()
    obj = dots
    if obj is None:
        obj = bpy.data.objects.new(DOTS_OBJECT, mesh)
        scene.collection.objects.link(obj)
    else:
        old = obj.data
        obj.data = mesh
        if old.users == 0:
            bpy.data.meshes.remove(old)
    obj.matrix_world = Matrix.Identity(4)

    data = {
        "frame": frame.name, "target": target.name, "align": align, "bu_per_mm": k,
        "frame_matrix": [list(row) for row in frame.matrix_world],     # 生成時の枠の位置(確定後に枠を動かしても検証できるように)
        "dims": dims.__dict__,
        "lines": [[{"dots": "".join(map(str, c.dots)), "char": c.char} for c in line] for line in lines],
    }
    obj["tenji_data"] = json.dumps(data, ensure_ascii=False)
    return {
        "obj": obj, "object": obj.name, "cells": sum(len(l) for l in lines), "dots_expected": len(placements),
        "dots_created": len(placements) - len(missed), "missed": missed[:20], "missed_count": len(missed),
        "max_incidence_deg": round(max_angle, 1), "steep_count": len(steep), "steep": steep[:20],
        "braille": ["".join(unicode_braille(c.dots) if c.dots != SPACE_MARK else "⠀" for c in l) for l in lines],
    }


def verify(scene, obj) -> dict:
    """生成済みメッシュ(obj)から点を逆に読み取り、期待パターンと照合する。"""
    data = json.loads(obj["tenji_data"])
    dims = Dims(**data["dims"])
    k = data["bu_per_mm"]
    to_frame = Matrix(data["frame_matrix"]).inverted() @ obj.matrix_world

    # 連結成分(= 1ドット)ごとの重心を枠座標(mm)で得る
    mesh = obj.data
    parent = list(range(len(mesh.vertices)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for e in mesh.edges:
        a, b = find(e.vertices[0]), find(e.vertices[1])
        if a != b:
            parent[a] = b
    groups: dict[int, list[Vector]] = {}
    for v in mesh.vertices:
        groups.setdefault(find(v.index), []).append(to_frame @ v.co)
    centers = [(sum((p for p in ps), Vector()) / len(ps)) / k for ps in groups.values()]

    # 期待位置(全セルの6点)に最近傍割当て
    line_cells = [[tuple(int(ch) for ch in c["dots"]) for c in line] for line in data["lines"]]
    expected = layout_dots(line_cells, dims, data["align"])
    grid = {}  # (line, cell, dot) -> (x, y) for ALL 6 positions
    from tenji.geometry import dot_offset, line_width, y_offset
    y_top = y_offset(len(line_cells), dims, data["align"])
    for li, cells in enumerate(line_cells):
        x0 = -line_width(len(cells), dims) / 2 if data["align"] == "CENTER" else 0.0
        for ci in range(len(cells)):
            for d in range(1, 7):
                ox, oy = dot_offset(d, dims)
                grid[(li, ci, d)] = (x0 + ci * dims.cell_pitch + ox, y_top - li * dims.line_pitch + oy)
    tol = dims.dot_pitch * 0.5
    found = set()
    unmatched = 0
    for c in centers:
        best = min(grid.items(), key=lambda kv: (kv[1][0] - c.x) ** 2 + (kv[1][1] - c.y) ** 2)
        (bx, by) = best[1]
        if math.hypot(bx - c.x, by - c.y) <= tol:
            found.add(best[0])
        else:
            unmatched += 1
    want = {(d.line, d.cell, d.dot_no) for d in expected}
    decoded = []
    for li, cells in enumerate(line_cells):
        row = []
        for ci in range(len(cells)):
            row.append(unicode_braille([int((li, ci, d) in found) for d in range(1, 7)]))
        decoded.append("".join(row))
    expected_str = ["".join(unicode_braille(c) for c in cells) for cells in line_cells]
    return {
        "ok": found == want and unmatched == 0 and len(centers) == len(want),
        "islands": len(centers), "expected_dots": len(want),
        "missing": sorted(want - found)[:20], "extra": sorted(found - want)[:20], "unmatched": unmatched,
        "decoded": decoded, "expected": expected_str,
    }
