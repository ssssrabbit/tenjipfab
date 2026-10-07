import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from collections import Counter
from tenji.geometry import Dims, dome_mesh, layout_dots, line_width


def _volume(verts, faces):
    v = 0.0
    for f in faces:
        for k in range(1, len(f) - 1):
            a, b, c = verts[f[0]], verts[f[k]], verts[f[k + 1]]
            v += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6
    return v


def test_dome_closed_and_outward():
    for embed in (0.0, 0.2):
        verts, faces = dome_mesh(Dims(embed=embed))
        edges = Counter()
        for f in faces:
            for i in range(len(f)):
                edges[tuple(sorted((f[i], f[(i + 1) % len(f)])))] += 1
        assert set(edges.values()) == {2}, "mesh must be closed manifold"
        assert _volume(verts, faces) > 0, "normals must point outward"


def test_smooth_flags_match_faces():
    from tenji.geometry import dome_smooth_flags
    for embed in (0.0, 0.2):
        d = Dims(embed=embed)
        verts, faces = dome_mesh(d)
        flags = dome_smooth_flags(d)
        assert len(flags) == len(faces), (embed, len(flags), len(faces))
        assert flags[-1] is False and flags[-2] is True
        assert (flags[0] is False) == (embed > 0)           # skirt の面は平坦


def test_layout():
    d = Dims()
    dots = layout_dots([[(1, 1, 1, 1, 1, 1), (0, 0, 0, 0, 0, 0), (1, 0, 0, 0, 0, 1)]], d)
    assert len(dots) == 6 + 2
    last = dots[-1]
    assert (last.cell, last.dot_no) == (2, 6)
    assert abs(last.x - (2 * 6.0 + 2.4)) < 1e-9 and abs(last.y + 4.8) < 1e-9
    c = layout_dots([[(1, 0, 0, 0, 0, 0)] * 3], d, "CENTER")
    assert abs(c[0].x + line_width(3, d) / 2) < 1e-9


def test_vertical_centering():
    from tenji.geometry import block_height
    d = Dims()
    row = [(1, 0, 1, 0, 0, 0)] * 2          # 各セルの上段と下段(点1,3)だけ
    for n in (1, 2, 5):
        dots = layout_dots([row] * n, d, "CENTER")
        ys = [p.y for p in dots]
        assert abs(max(ys) + min(ys)) < 1e-9, (n, max(ys), min(ys))                # 原点の上下に対称
        assert abs((max(ys) - min(ys)) - ((n - 1) * d.line_pitch + 2 * d.dot_pitch)) < 1e-9
    assert abs(max(p.y for p in layout_dots([row] * 3, d, "LEFT"))) < 1e-9          # LEFT は最上段が原点(従来どおり)


if __name__ == "__main__":
    test_dome_closed_and_outward(); test_smooth_flags_match_faces(); test_layout(); test_vertical_centering(); print("PASS geometry")
