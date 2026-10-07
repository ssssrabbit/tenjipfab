"""Compare the Python port against tests/golden.json (generated from the TS app by tools/gen_golden.js)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from tenji.braille import kana_to_cells
from tenji.japanese import _get_tokenizer

G = json.loads((pathlib.Path(__file__).parent / "golden.json").read_text())


def test_kana_cells():
    bad = []
    for c in G["kanaCases"]:
        got = [["".join(map(str, x.dots)), x.char] for x in kana_to_cells(c["text"])]
        if got != c["cells"]:
            bad.append((c["text"], c["cells"], got))
    assert not bad, bad


def test_tokens_match_kuromoji():
    """Informational strictness: surface/reading/pos must match kuromoji."""
    bad = []
    for c in G["tokens"]:
        got = [[t.surface, t.reading, t.part_of_speech.split(",")[0], t.part_of_speech.split(",")[1]] for t in _get_tokenizer().tokenize(c["text"])]
        want = [[s, r or "*", p, d] for s, r, p, d in c["tokens"]]   # 読み無し: kuromoji=null / Janome='*'
        if got != want:
            bad.append((c["text"], want, got))
    assert not bad, "\n".join(map(str, bad))


if __name__ == "__main__":
    for fn in (test_kana_cells, test_tokens_match_kuromoji):
        try:
            fn(); print("PASS", fn.__name__)
        except AssertionError as e:
            print("FAIL", fn.__name__, "\n", e)
