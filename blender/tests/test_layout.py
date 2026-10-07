"""Python layout port vs. the TS app's buildFlatCells / splitCellsWithRules (tests/golden_layout.json)."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from tenji.braille import Cell, WordMapping
from tenji.layout import build_flat_cells, split_cells_with_rules

INPUTS = json.loads((ROOT / "layout_inputs.json").read_text())
GOLD = json.loads((ROOT / "golden_layout.json").read_text())


def _mapped(inp):
    return [WordMapping(m["orig"], m["reading"], [Cell(tuple(c["dots"]), c["char"]) for c in m["cells"]],
                        m["start"], m["end"], m["isParagraphStart"], m["pos"], m["attachPrev"]) for m in inp["mapped"]]


def _ser(cells):
    return [["".join(map(str, c.dots)), c.char, c.word_idx] for c in cells]


def test_layout():
    bad = []
    for inp, g in zip(INPUTS, GOLD):
        flat = build_flat_cells(_mapped(inp))
        if _ser(flat) != g["flat"]:
            bad.append((inp["text"], "flat"))
        for w, want in g["splits"].items():
            got = [_ser(l) for l in split_cells_with_rules(flat, int(w))]
            if got != want:
                bad.append((inp["text"], "split", w))
    assert not bad, bad


def test_punctuation_rules():
    """MEXT 点字表記法: 句点は直前に続け、後ろは2マス。読点は後ろ1マス。"""
    from tenji.japanese import convert
    flat = build_flat_cells(convert("私は行く。明日は晴れ、雨も降る。"))
    s = "".join(c.char if c.word_idx != -1 else "_" for c in flat)
    assert "く。__あ" in s, s
    assert "_。" not in s and "_、" not in s, s
    assert "、_" in s and "、__" not in s, s
    assert s.count("。__") == 1 and s.endswith("。"), s   # 末尾の2マスは付かない
    q = "".join(c.char if c.word_idx != -1 else "_" for c in build_flat_cells(convert("どうして？本当に！そうなの。")))
    assert "？__" in q and "！__" in q and "_？" not in q and "_！" not in q, q
    m = "".join(c.char if c.word_idx != -1 else "_" for c in build_flat_cells(convert("あっ！と叫んだ。")))
    assert "！_と" in m and "！__" not in m, m   # 文中の感嘆符は1マス


if __name__ == "__main__":
    test_layout(); test_punctuation_rules(); print("PASS layout")
