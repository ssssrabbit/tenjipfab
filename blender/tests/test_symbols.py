"""つなぎ符・波線・矢印・大文字符: 点の配置は MEXT PDF(第6章第3節 関係符号の用法)の図による。"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from tenji.japanese import convert
from tenji.layout import build_flat_cells


def cells(text):
    """空白は '_'、他は点の6桁。"""
    return ["_" if c.word_idx == -1 else "".join(map(str, c.dots)) for c in build_flat_cells(convert(text))]


def test_connector_number():
    # 図: 100円玉 = 数符 1 0 0 つなぎ符 エ ン ダマ(ゞ)
    c = cells("100円玉")
    assert c[:5] == ["001111", "100000", "010110", "010110", "001001"], c
    assert "_" not in c, "助数詞・接尾語は直前に続ける"


def test_connector_alphabet():
    # 図: X線 = 外字符 大文字符 x つなぎ符 セ ン
    assert cells("X線")[:4] == ["000011", "000001", "101101", "001001"]


def test_capital_runs():
    from tenji.braille import kana_to_cells
    assert "".join(c.char for c in kana_to_cells("DOS")) == "外大大DOS"   # PDF: 外大大dOS
    assert "".join(c.char for c in kana_to_cells("V")) == "外大V"        # PDF: 大V


def test_wave():
    # 波線 = 第1つなぎ符×2、前後は空けない
    c = cells("東京～大阪")
    i = c.index("001001")
    assert c[i:i + 2] == ["001001", "001001"] and c[i - 1] != "_" and c[i + 2] != "_", c


def test_arrow():
    # 矢印 = ーーた(点2,5 / 点2,5 / 点1,3,5)、前後1マス
    c = cells("東京8時36分→長野10時2分")
    arrow = ["010010", "010010", "101010"]
    i = next(k for k in range(len(c)) if c[k:k + 3] == arrow)   # 長音「ー」(点2,5)と混同しない
    assert c[i - 1] == "_" and c[i + 3] == "_", c


def test_no_connector_when_spaced_or_unrelated():
    assert "001001" not in cells("3 あ")            # 空白があれば不要
    assert "001001" not in cells("3か")             # か行は数字と同形ではない


def test_foreign_symbols():
    # 図: 外字符(点5,6) + ％(1,2,3,4) ＆(1,2,3,4,6) ＃(1,4,6) ＊(1,6) ＠(2,4,6)
    expect = {"％": "111100", "＆": "111101", "＃": "100101", "＊": "100001", "＠": "010101"}
    for ch, second in expect.items():
        m = [x for x in convert(ch)][0]
        assert ["".join(map(str, c.dots)) for c in m.cells] == ["000011", second], ch
    # 半角も同じ
    assert [c.dots for c in convert("%")[0].cells] == [c.dots for c in convert("％")[0].cells]


def _find(seq, sub):
    return next(i for i in range(len(seq)) if seq[i:i + len(sub)] == sub)


def test_percent_etc_spacing():
    c = cells("100％だった")
    i = _find(c, ["000011", "111100"])
    assert c[i + 2] == "_", c                                                     # 図: 数100 外ね □ ダッタ
    d = cells("20％引き")
    i = _find(d, ["000011", "111100"])
    assert d[i + 2] == "001001" and "_" not in d, d                               # 図: 数20 外ね つなぎ ビキ
    e = cells("＊11は本社")
    assert e[:3] == ["000011", "100001", "001111"], e                             # 図: 外か 数 1 1 ワ(続ける)
    h = cells("「＃点字」")
    assert h[:3] == ["001001", "000011", "100101"] and h[3] == "_", h             # 図: 「 外く □ テンジ
    a = cells("商品5個＠200円")
    i = _find(a, ["000011", "010101"])
    assert a[i - 1] == "_" and a[i + 2] == "_", a                                 # ＠は前後1マス


def test_mask():
    # 図: 数20××ネン = 数 2 0 [点5][点1-6] [点5][点1-6] つなぎ ネ ン
    c = cells("20××年")
    assert c[:9] == ["001111", "110000", "010110", "000010", "111111", "000010", "111111", "001001", "111100"], c
    # 図: ナイセン □ 数1××4 バン = 数符は最初の1回だけ(伏せ字の後ろの4に数符を付けない)
    d = cells("内線1××4番")
    assert d.count("001111") == 1, d
    assert d[_find(d, ["111111", "000010", "111111"]) + 3] == "100110", d          # 伏せ字の直後に 4(点1,4,5)
    # 掛け算は伏せ字にしない
    assert "111111" not in cells("3×4=12")


def test_punctuation_cells():
    # 図: 読点=点5,6 / 句点=点2,5,6 / 中点=点5 / 点線=点2×3 / 棒線=点2,5×2
    from tenji.braille import BRAILLE_MAP
    assert BRAILLE_MAP["、"] == (0, 0, 0, 0, 1, 1) and BRAILLE_MAP["，"] == BRAILLE_MAP["、"]
    assert BRAILLE_MAP["。"] == (0, 1, 0, 0, 1, 1)
    assert cells("あ・い")[1:2] == ["000010"]
    a = cells("あ…い")
    i = _find(a, ["010000"] * 3)
    assert a[i - 1] == "_" and a[i + 3] == "_", a              # 点線は前後1マス
    b = cells("あ――い")
    j = _find(b, ["010010", "010010"])
    assert b[j - 1] == "_" and b[j + 2] == "_" and b.count("010010") == 2, b    # 棒線は前後1マス・2字で1つ


def test_slash():
    # 図: DOS/V = 外 大 大 d o s / 大 v
    c = cells("DOS/V")
    assert c == ["000011", "000001", "000001", "100110", "101010", "011100", "001100", "000001", "111001"], c
    # 図: S/N比 = 外 大 s / 大 n (つなぎ符 ヒ)
    d = cells("S/N")
    assert d == ["000011", "000001", "011100", "001100", "000001", "101110"], d
    # 図: 125/85 = 数 1 2 5 外 / 数 8 5 (スラッシュの前に外字符、後ろで数符を付け直す)
    e = cells("125/85")
    assert e == ["001111", "100000", "110000", "100010", "000011", "001100", "001111", "110010", "100010"], e


def test_nakaten_between_numbers():
    # 図: 五・六十 = 数5 数60 (数字の区切りに中点は書かない) / 5・15事件 = 数5 数15 □ ジケン
    assert cells("5・60") == ["001111", "100010", "001111", "110100", "010110"], cells("5・60")
    f = cells("5・15事件")
    assert f[:6] == ["001111", "100010", "001111", "100000", "100010", "_"], f   # 数5 数15 □ ジケン
    # 語句の中点は書く: 後ろ1マス、前は続ける
    c = cells("東大寺・春日大社")
    i = c.index("_")                                     # 中点の後ろの1マス
    assert c[i - 1] == "000010" and c[i - 2] == "110011", c   # 「…ジ」の直後に中点(前は空けない)


def test_ellipsis_spacing():
    # 図: シカシ □ 点線 。」 (句読点・閉じ符号が続くときは続ける) / 点線 □ ノヨーナ
    c = cells("「しかし…。」")
    i = _find(c, ["010000"] * 3)
    assert c[i + 3] == "010011" and c[i - 1] == "_", c
    d = cells("…のような")
    assert d[3] == "_", d


if __name__ == "__main__":
    for f in (test_connector_number, test_connector_alphabet, test_capital_runs, test_wave, test_arrow,
              test_no_connector_when_spaced_or_unrelated, test_foreign_symbols, test_percent_etc_spacing, test_mask,
              test_punctuation_cells, test_slash, test_nakaten_between_numbers, test_ellipsis_spacing):
        f()
    print("PASS symbols")
