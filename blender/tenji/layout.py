"""Spacing (分かち書き) and line wrapping for braille cells.

Port of buildFlatCells / splitCellsWithRules in tenji-pfab-rn/src/screens/HomeScreen.tsx.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .symbols import ATTACH_NUMBER, GAP_BEFORE_PARTICLE, LETTERLIKE_CHARS, MASK, TSUNAGI, WAVE
from .braille import (
    BRAILLE_MAP, DAKUTEN_MARK, FOREIGN_INDICATOR, HANDAKUTEN_MARK, NUM_INDICATOR, SPACE_MARK,
    YOON_DAKU_MARK, YOON_HANDAKU_MARK, YOON_MARK, Dots, WordMapping, _d,
)

PREFIX_MARKS = {DAKUTEN_MARK, HANDAKUTEN_MARK, YOON_MARK, YOON_DAKU_MARK, YOON_HANDAKU_MARK,
                NUM_INDICATOR, FOREIGN_INDICATOR}


@dataclass
class FlatCell:
    dots: Dots
    char: str
    word_idx: int          # -1: 空白・改行などの区切り
    orig: str
    is_newline: bool = False


# 文部科学省「点字表記法」第6章第3節(句読法)
#  - 句点・読点・疑問符・感嘆符・中点は直前の語に続けて書く
#  - 句点・疑問符・感嘆符の後ろ(文末)は2マス、読点・中点の後ろは1マス
#  - 疑問符・感嘆符が文中にくる(助詞が続く)場合は後ろ1マス
#  - 閉じ括弧が続くときは空けない
_ATTACH_BEFORE = {"。", "、", "，", "．", "？", "！", "・"} | WAVE   # 波線は前後を空けない
_SENTENCE_END = {"。", "？", "！"}
_EXCL_QUESTION = {"？", "！"}
_CLOSERS = set("」』）〕］｝〉》】)]")
_OPENERS = set("「『（〔［｛〈《【([")   # 囲み符号の内側は続ける(開きの後ろは空けない)
_PARTICLES = ("助詞", "助動詞")


def build_flat_cells(mapped: list[WordMapping]) -> list[FlatCell]:
    flat: list[FlatCell] = []
    for idx, item in enumerate(mapped):
        if item.orig == "\n":
            continue
        if item.is_paragraph_start and flat:
            flat.append(FlatCell(SPACE_MARK, "\n", -1, "(NewLine)", True))
        for c in item.cells:
            flat.append(FlatCell(c.dots, c.char, idx, item.orig))
        nxt = mapped[idx + 1] if idx + 1 < len(mapped) else None
        if nxt is None or nxt.orig == "\n" or nxt.is_paragraph_start or item.is_paragraph_start:
            continue
        if item.gap is not None:              # ユーザーが指定した空白マス数(規則より優先)
            flat.extend(FlatCell(SPACE_MARK, " ", -1, "(Space)") for _ in range(item.gap))
            continue
        if item.orig in _OPENERS or item.orig in WAVE or nxt.attach_prev:
            continue
        if nxt.orig in _ATTACH_BEFORE or nxt.orig in _CLOSERS:
            continue
        if item.orig in GAP_BEFORE_PARTICLE and item.cells and nxt.pos in _PARTICLES:
            n_spaces = 1                      # ％＃＊・伏せ字の後ろの助詞・助動詞は1マス
        elif item.orig == MASK and item.cells:
            continue                          # 伏せ字の後ろは続ける(つなぎ符は後段で挿入)
        elif item.orig in ATTACH_NUMBER and nxt.cells and nxt.cells[0].dots == NUM_INDICATOR:
            continue                          # ＊11 のように数字が続くときは続ける
        elif item.orig in _EXCL_QUESTION and nxt.pos in _PARTICLES:
            n_spaces = 1
        elif nxt.pos in _PARTICLES:
            continue
        elif item.orig in _SENTENCE_END:
            n_spaces = 2
        elif item.orig in _CLOSERS and idx > 0 and mapped[idx - 1].orig in _SENTENCE_END:
            n_spaces = 2                      # 「…？」の後ろ(文末)は2マス
        else:
            n_spaces = 1
        flat.extend(FlatCell(SPACE_MARK, " ", -1, "(Space)") for _ in range(n_spaces))
    return _insert_connectors(flat)


# 第1つなぎ符: 数字は「ア行・ラ行の仮名」と、アルファベットは「仮名」と同形のため、続けて書くときは間に入れる。
_A_RA = set("あいうえおらりるれろ")
_KANA_START = {ch for ch in BRAILLE_MAP if "\u3041" <= ch <= "\u3093" or ch == "ー"} | {"゛", "゜", "拗", "拗゛", "拗゜"}


def _insert_connectors(flat: list[FlatCell]) -> list[FlatCell]:
    out: list[FlatCell] = []
    for cell in flat:
        if out and cell.word_idx != -1 and out[-1].word_idx != -1:
            prev = out[-1].char
            digit_then_a_ra = prev in "0123456789" and cell.char in _A_RA
            letterlike_then_kana = (prev.isascii() and prev.isalpha() or prev in LETTERLIKE_CHARS) and cell.char in _KANA_START
            if digit_then_a_ra or letterlike_then_kana:
                out.append(FlatCell(_d(TSUNAGI), "‐", cell.word_idx, cell.orig))
        out.append(cell)
    return out


def _syllable_units(cells: list[FlatCell]) -> list[list[FlatCell]]:
    units, i = [], 0
    while i < len(cells):
        if cells[i].dots in PREFIX_MARKS and i + 1 < len(cells):
            units.append([cells[i], cells[i + 1]])
            i += 2
        else:
            units.append([cells[i]])
            i += 1
    return units


def split_cells_with_rules(cells: list[FlatCell], max_chars: int) -> list[list[FlatCell]]:
    """日本語点字の行分割。単語は行をまたがない。長すぎる単語は音節単位で切り「ー」で継続。"""
    if max_chars <= 0 or not cells:
        return []
    cont = FlatCell(BRAILLE_MAP["ー"], "ー", -1, "(ー)")

    tokens: list[tuple[str, list[FlatCell]]] = []
    buf: list[FlatCell] = []

    def flush():
        nonlocal buf
        if buf:
            tokens.append(("word", buf))
            buf = []

    for c in cells:
        if c.is_newline:
            flush(); tokens.append(("newline", []))
        elif c.word_idx == -1:
            flush(); tokens.append(("space", []))
        else:
            buf.append(c)
    flush()

    lines: list[list[FlatCell]] = []
    cur: list[FlatCell] = []

    def strip_tail():
        while cur and cur[-1].word_idx == -1:
            cur.pop()

    def commit():
        nonlocal cur
        strip_tail()
        if cur:
            lines.append(list(cur))
        cur = []

    for kind, wcells in tokens:
        if kind == "newline":
            commit(); continue
        if kind == "space":
            if cur and len(cur) < max_chars:
                cur.append(FlatCell(SPACE_MARK, " ", -1, "(Space)"))
            continue

        units = _syllable_units(wcells)
        size = sum(len(u) for u in units)
        if size <= max_chars:
            if len(cur) + size > max_chars:
                commit()
            cur.extend(c for u in units for c in u)
            continue

        strip_tail()
        remaining = list(units)
        while remaining:
            if max_chars - len(cur) <= 0:
                commit(); continue
            k = 0
            while k < len(remaining):
                need = len(remaining[k]) + (0 if k == len(remaining) - 1 else 1)
                if len(cur) + need <= max_chars:
                    cur.extend(remaining[k]); k += 1
                else:
                    break
            if k == 0:
                if cur:
                    commit(); continue
                cur.extend(remaining[0]); k = 1
            remaining = remaining[k:]
            if remaining:
                if len(cur) < max_chars:
                    cur.append(replace(cont))
                commit()

    strip_tail()
    if cur:
        lines.append(cur)
    return lines


def layout_fixed_width(cells: list[FlatCell], max_chars: int) -> list[list[FlatCell]]:
    """「1行のセル数」どおりに左から並べて折り返す(語や分かち書きでは改行しない)。

    - 行が満ちたらそこで折り返す。語の途中でも折り返す(継続符「ー」は入れない)。
    - 濁点・拗音符・数符・外字符などの前置符号は、本字と割らずに同じ行へ置く。
    - 行頭に空白は置かない。行末の空白は取り除く。強制改行(段落)は守る。
    """
    if max_chars <= 0 or not cells:
        return []
    lines: list[list[FlatCell]] = []
    cur: list[FlatCell] = []

    def commit():
        nonlocal cur
        while cur and cur[-1].word_idx == -1:
            cur.pop()
        if cur:
            lines.append(cur)
        cur = []

    i = 0
    while i < len(cells):
        c = cells[i]
        if c.is_newline:
            commit()
            i += 1
        elif c.word_idx == -1:                       # 空白
            if cur and len(cur) < max_chars:
                cur.append(c)
            i += 1
        else:
            unit = [c]
            if c.dots in PREFIX_MARKS and i + 1 < len(cells) and cells[i + 1].word_idx != -1:
                unit.append(cells[i + 1])
            if len(cur) + len(unit) > max_chars:
                commit()
            cur.extend(unit)
            i += len(unit)
            if len(cur) >= max_chars:
                commit()
    commit()
    return lines
