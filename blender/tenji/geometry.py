"""Pure-Python braille geometry (no bpy): dot layout on a plane and dome meshes. Units: mm."""
from __future__ import annotations

import math
from dataclasses import dataclass

from .braille import Dots


@dataclass
class Dims:
    """既定値は JIS 準拠の標準寸法(点間 2.4mm, セル間 6.0mm)。径・高さ・行間は調整可能な仮定値。"""
    dot_pitch: float = 2.4      # 同一セル内の点の間隔
    cell_pitch: float = 6.0     # セル間隔(セル左上点どうしの距離)
    line_pitch: float = 10.0    # 行間隔
    dot_diameter: float = 1.5
    dot_height: float = 0.3
    embed: float = 0.2          # 下へ潜らせる深さ(曲面との隙間防止)


@dataclass
class DotPos:
    line: int
    cell: int
    dot_no: int   # 1..6
    x: float
    y: float


def dot_offset(dot_no: int, dims: Dims) -> tuple[float, float]:
    """点番号1..6 -> セル内オフセット。左列 1,2,3 / 右列 4,5,6、上から下。"""
    col, row = divmod(dot_no - 1, 3)
    return col * dims.dot_pitch, -row * dims.dot_pitch


def line_width(n_cells: int, dims: Dims) -> float:
    return 0.0 if n_cells == 0 else (n_cells - 1) * dims.cell_pitch + dims.dot_pitch


def block_height(n_lines: int, dims: Dims) -> float:
    """最上行の最上段の点から最下行の最下段の点までの高さ。"""
    return 0.0 if n_lines == 0 else (n_lines - 1) * dims.line_pitch + 2 * dims.dot_pitch


def y_offset(n_lines: int, dims: Dims, align: str) -> float:
    """CENTER のときはブロックを原点の上下に対称に置く(行数が変わっても中心が動かない)。LEFT は原点が左上。"""
    return block_height(n_lines, dims) / 2 if align == "CENTER" else 0.0


def layout_dots(lines: list[list[Dots]], dims: Dims, align: str = "LEFT") -> list[DotPos]:
    """各行のセル列 -> 平面上の点位置。LEFT: 原点はブロック左上。CENTER: 原点がブロックの中心(各行は左右中央)。"""
    out: list[DotPos] = []
    y_top = y_offset(len(lines), dims, align)
    for li, cells in enumerate(lines):
        x0 = -line_width(len(cells), dims) / 2 if align == "CENTER" else 0.0
        y0 = y_top - li * dims.line_pitch
        for ci, dots in enumerate(cells):
            for i, on in enumerate(dots):
                if on:
                    ox, oy = dot_offset(i + 1, dims)
                    out.append(DotPos(li, ci, i + 1, x0 + ci * dims.cell_pitch + ox, y0 + oy))
    return out


def dome_mesh(dims: Dims, segments: int = 16, rings: int = 4):
    """閉じた球冠(底面は円柱状の skirt 付き)。原点=接地点、+Z=法線。(verts, faces) を返す。"""
    a, h = dims.dot_diameter / 2, dims.dot_height
    R = (a * a + h * h) / (2 * h)
    zc = h - R
    theta0 = math.asin(min(1.0, a / R))
    profile = []
    if dims.embed > 0:
        profile.append((a, -dims.embed))
    profile.append((a, 0.0))
    for i in range(1, rings):
        th = theta0 * (1 - i / rings)
        profile.append((R * math.sin(th), zc + R * math.cos(th)))

    verts: list[tuple[float, float, float]] = []
    for r, z in profile:
        for s in range(segments):
            ang = 2 * math.pi * s / segments
            verts.append((r * math.cos(ang), r * math.sin(ang), z))
    apex = len(verts)
    verts.append((0.0, 0.0, h))

    faces: list[tuple[int, ...]] = []
    n = len(profile)
    for ri in range(n - 1):
        for s in range(segments):
            s2 = (s + 1) % segments
            faces.append((ri * segments + s, ri * segments + s2, (ri + 1) * segments + s2, (ri + 1) * segments + s))
    for s in range(segments):
        faces.append(((n - 1) * segments + s, (n - 1) * segments + (s + 1) % segments, apex))
    faces.append(tuple(range(segments - 1, -1, -1)))   # 底面(下向き)
    return verts, faces


def dome_smooth_flags(dims: Dims, segments: int = 16, rings: int = 4) -> list[bool]:
    """dome_mesh() の各面を滑らかに陰影するか。ドームの曲面だけを滑らかにし、側面(skirt)と底面は平坦にする。"""
    n_rings = rings + (1 if dims.embed > 0 else 0)          # profile の段数(skirt の段を含む)
    n_bands = n_rings - 1
    flags: list[bool] = []
    for band in range(n_bands):
        flags += [not (dims.embed > 0 and band == 0)] * segments    # 最初の帯が skirt
    flags += [True] * segments                                       # 頂点へ向かう三角形
    flags.append(False)                                              # 底面
    return flags
