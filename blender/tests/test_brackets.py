"""括弧: 点の配置は MEXT PDF(第6章第3節)の図、入れ子と空白は同 PDF の記述・用例による。"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from tenji.japanese import convert
from tenji.layout import build_flat_cells


def dots(text):
    out = []
    for m in convert(text):
        if m.orig in "「」『』〈〉（）〔〕［］":
            out.append([("".join(map(str, c.dots))) for c in m.cells])
    return out


def flat(text):
    return "".join(c.char if c.word_idx != -1 else "_" for c in build_flat_cells(convert(text)))


def test_patterns():
    assert dots("「あ」") == [["001001"], ["001001"]]
    assert dots("『あ』") == [["000011", "001001"], ["001001", "011000"]]
    assert dots("〈あ〉") == [["000011", "001000"], ["000001", "011000"]]
    assert dots("（あ）") == [["011011"], ["011011"]]
    assert dots("〔あ〕") == [["000010", "011011"], ["011011", "010000"]]


def test_nesting():
    # カギの中のカギ -> ふたえカギ
    assert dots("「あ「い」う」") == [["001001"], ["000011", "001001"], ["001001", "011000"], ["001001"]]
    # カッコの中のカッコ -> 二重カッコ(PDF の用例: 点字制定130周年（1890年〔明治23年〕…）)
    assert dots("（あ〔い〕う）") == [["011011"], ["000011", "011011"], ["011011", "011000"], ["011011"]]


def test_spacing():
    s = flat("先生は、「みんなの前で話すときは『伝えようとする気持ち』が大切です。」と、お話しになった。")
    assert "、_「み" in s and "「_" not in s, s              # 開きの後ろは続ける、外側は分かち書き
    assert "。」と" in s and "」_と" not in s, s               # 句点・閉じ・助詞は続ける
    t = flat("「やあ、元気だった？」自然に声が弾んだ。")
    assert "？」__し" in t, t                                    # 文末の閉じの後ろは2マス
    assert flat("（あ）") == "（あ）"


if __name__ == "__main__":
    test_patterns(); test_nesting(); test_spacing(); print("PASS brackets")
