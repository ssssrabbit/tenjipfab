"""固定幅レイアウト(1行のセル数で並べる)と、語ごとの空白指定。Python 版のみの機能(TS アプリには無い)。"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from tenji.braille import DAKUTEN_MARK, SPACE_MARK
from tenji.japanese import convert
from tenji.layout import build_flat_cells, layout_fixed_width, split_cells_with_rules


def lines_of(text, n, gaps=None):
    mapped = convert(text)
    if gaps:
        for i, g in gaps.items():
            mapped[i].gap = g
    return layout_fixed_width(build_flat_cells(mapped), n)


def s(line):
    return "".join(c.char if c.word_idx != -1 else "_" for c in line)


def test_fixed_width_fills_lines():
    ls = lines_of("点字で作るクマの人形", 8)
    assert all(len(l) <= 8 for l in ls), [s(l) for l in ls]
    # 最後の行以外は、前置符号を割らない範囲でほぼ満ちている(語ごとに改行しない)
    assert all(len(l) >= 7 for l in ls[:-1]), [s(l) for l in ls]
    # 規則どおりの折り返しは語ごとに改行するので行数が多い
    mapped = convert("点字で作るクマの人形")
    rules = split_cells_with_rules(build_flat_cells(mapped), 8)
    assert len(ls) <= len(rules)


def test_prefix_not_split_and_no_leading_space():
    for n in range(2, 12):
        for l in lines_of("がっこうでぱぴぷぺぽを読む、きゃきゅきょ。", n):
            assert l[0].word_idx != -1 and l[-1].word_idx != -1, s(l)       # 行頭・行末に空白なし
            assert l[-1].dots != DAKUTEN_MARK, s(l)                            # 濁点で行が終わらない
    # 前置符号の直後で割れていない: 各行の最後が前置符号でない
    from tenji.layout import PREFIX_MARKS
    for l in lines_of("がっこうでぱぴぷぺぽ", 3):
        assert l[-1].dots not in PREFIX_MARKS or len(l) == 1, s(l)


def test_paragraph_break_kept():
    ls = lines_of("あい\nうえ", 10)
    assert len(ls) == 2


def test_gap_override():
    # 「私」(0)の後ろを1マス、「学校」(2)の後ろを2マスに指定(濁点は別セルなので「゛か」と表示される)
    ls = lines_of("私は学校へ行く", 40, gaps={0: 1, 2: 2})
    t = s(sum(ls, []))
    assert "わたし_わ" in t and "゛かっこー__え" in t, t
    # 0 マス指定で空白が消える(名詞どうしも続けて書ける)
    t2 = s(sum(lines_of("山田太郎", 40, gaps={0: 0}), []))
    assert "_" not in t2, t2


def test_typed_spaces_become_exact_gaps():
    from tenji.japanese import fold_whitespace
    folded = fold_whitespace(convert("てんじ  くまさん"))
    assert [m.orig for m, _ in folded] == ["てんじ", "くま", "さん"] and folded[0][1] == 2 and folded[1][1] == -1, folded
    # 手で入れた空白は自動の空白に足さず、ちょうどその数になる
    mapped = []
    for m, g in fold_whitespace(convert("てんじ くまさん")):
        m.gap = g if g >= 0 else None
        mapped.append(m)
    t = s(sum(layout_fixed_width(build_flat_cells(mapped), 40), []))
    assert t.count("_") == 1 + 0 and "し_く" in t, t        # 空白1つ → 1マス(3マスにならない)
    # 全角空白・先頭の空白
    assert fold_whitespace(convert("　あ　い"))[0][0].orig == "あ"


if __name__ == "__main__":
    for f in (test_fixed_width_fills_lines, test_prefix_not_split_and_no_leading_space, test_paragraph_break_kept, test_gap_override, test_typed_spaces_become_exact_gaps):
        f()
    print("PASS layout_modes")
