"""Whole pipeline: Python (Janome) vs the TS app's real code (kuromoji) -- tests/golden_pipeline.json.
text -> tokens/readings/cells (mapped) -> spacing (flat) -> line wrapping."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from tenji.japanese import convert
from tenji.layout import build_flat_cells, split_cells_with_rules

GOLD = json.loads((ROOT / "golden_pipeline.json").read_text())


def _cells(cells):
    return [["".join(map(str, c.dots)), c.char] for c in cells]


def test_pipeline():
    bad = []
    for g in GOLD:
        mapped = convert(g["text"])
        got = [[m.orig, m.reading, m.pos, m.attach_prev, m.is_paragraph_start, _cells(m.cells)] for m in mapped]
        if got != g["mapped"]:
            diff = next((a, b) for a, b in zip(got, g["mapped"]) if a != b) if len(got) == len(g["mapped"]) else ("len", len(got), len(g["mapped"]))
            bad.append((g["text"], "mapped", diff))
            continue
        flat = build_flat_cells(mapped)
        f = lambda cs: [["".join(map(str, c.dots)), c.char, c.word_idx] for c in cs]
        if f(flat) != g["flat"]:
            bad.append((g["text"], "flat"))
            continue
        for w, want in g["splits"].items():
            if [f(l) for l in split_cells_with_rules(flat, int(w))] != want:
                bad.append((g["text"], "split", w))
    assert not bad, "\n".join(map(str, bad))


if __name__ == "__main__":
    test_pipeline(); print("PASS pipeline")
