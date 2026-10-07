"""Text -> WordMapping[] using Janome (IPAdic, same dictionary family as kuromoji).

Port of tenji-pfab-rn/src/logic/japaneseProcessor.ts (rules and paragraph handling).
"""
from __future__ import annotations

import re

from .brackets import resolve_brackets
from .brackets import CLOSERS as _BR_CLOSE, OPENERS as _BR_OPEN
from .symbols import SPLIT_CHARS, resolve_symbols
from .braille import (
    SPACE_MARK, Cell, WordMapping, fallback_convert, kana_to_cells, katakana_to_hiragana,
)

_tokenizer = None


def _get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        from janome.tokenizer import Tokenizer
        _tokenizer = Tokenizer()
    return _tokenizer


def apply_particle_rule(surface: str, pos: str, reading: str) -> str:
    if pos != "助詞":
        return reading
    return {"は": "わ", "へ": "え"}.get(surface, reading)


# お段・ウ段 + う -> ー
_LONG_VOWEL = re.compile("([おこそとのほもよろをごぞどぼぽぉょうくすつぬふむゆるぐずづぶぷ])う")


def apply_long_vowel_rule(reading: str) -> str:
    prev = None
    while prev != reading:
        prev = reading
        reading = _LONG_VOWEL.sub(r"\1ー", reading)
    return reading


def _indent(start: int) -> WordMapping:
    return WordMapping("", "", [Cell(SPACE_MARK, " "), Cell(SPACE_MARK, " ")],
                       start, start, is_paragraph_start=True)


def resolve_all(mapped: list[WordMapping]) -> None:
    """括弧・波線・矢印のセルを確定する(文脈が要るので、全体が揃ってから呼ぶ)。"""
    resolve_brackets(mapped)
    resolve_symbols(mapped)


def fold_whitespace(mapped: list[WordMapping]) -> list[tuple[WordMapping, int]]:
    """入力中の空白(手で入れた区切り)を、直前の語の「後ろの空白マス数」にまとめる。

    戻り値: [(語, 手で入れた空白のマス数。入れていなければ -1)]。空白だけのトークンは語として残さない。
    N個の空白は、規則で入る自動の空白に足さず、ちょうどNマスになる(Blender アドオン用。TS アプリの挙動は変えない)。
    """
    out: list[list] = []
    for m in mapped:
        if m.orig.strip() == "" and m.orig != "" and m.orig != "\n":
            if out:
                out[-1][1] = max(out[-1][1], 0) + len(m.orig)
            continue
        out.append([m, -1])
    return [(m, g) for m, g in out]


def mapping_from_fields(orig: str, reading: str, pos: str | None, is_para: bool, attach_prev: bool = False,
                        gap: int | None = None) -> WordMapping:
    """UI に保存した (orig, reading, pos, para) から WordMapping を再構築する(読み編集後の再計算用)。"""
    if orig == "\n":
        return WordMapping("\n", "", [], 0, 0)
    if is_para and orig == "":
        return _indent(0)
    return WordMapping(orig, reading, kana_to_cells(reading), 0, len(orig), pos=pos or None, attach_prev=attach_prev, gap=gap)


_SPLIT = set(SPLIT_CHARS) | set(_BR_OPEN) | set(_BR_CLOSE)
# 数字の伏せ字「×」を辞書に渡すときだけ数字に置き換える(「20××年」の「年」をネンと読ませるため)。
# 掛け算(3×4)は対象外: ×が1つで後ろに数字が続く場合は置き換えない。
_MASK_RE = re.compile(r"(?<=[0-9０-９])(×{2,}|×(?![0-9０-９]))")


_SLASH_RUN = re.compile(r"[A-Za-z0-9]+(?:[/／][A-Za-z0-9]+)+")


def _unmask(text: str) -> str:
    return _MASK_RE.sub(lambda m: "0" * len(m.group()), text)


def _tokens(text: str):
    """(surface, reading, pos, detail1)。辞書が「「＃」のように記号と括弧を1トークンにしたもの、
    および置き換えた伏せ字を含む数字トークンは、元の文字列に戻して単独の記号に切り出す。"""
    m = _SLASH_RUN.search(text)
    if m:   # DOS/V, S/N, 125/85 のような英数字のスラッシュ区切りは1語として扱う
        if m.start():
            yield from _tokens(text[:m.start()])
        yield m.group(), m.group(), "名詞", "一般"
        if m.end() < len(text):
            yield from _tokens(text[m.end():])
        return
    off = 0
    for tok in _get_tokenizer().tokenize(_unmask(text)):
        n = len(tok.surface)
        original = text[off:off + n]
        off += n
        if len(original) > 1 and any(c in _SPLIT for c in original):
            run = ""
            for c in original:
                if c in _SPLIT:
                    if run:
                        yield from _tokens(run)
                        run = ""
                    yield c, c, "記号", "一般"
                else:
                    run += c
            if run:
                yield from _tokens(run)
        else:
            parts = tok.part_of_speech.split(",")
            yield original, tok.reading, parts[0], parts[1]


def tokenize_paragraph(text: str, start: int) -> list[WordMapping]:
    result: list[WordMapping] = []
    idx = start
    for orig, reading_raw, pos, detail1 in _tokens(text):
        reading_kata = reading_raw if reading_raw and reading_raw != "*" else orig
        reading = katakana_to_hiragana(reading_kata)
        reading = apply_particle_rule(orig, pos, reading)
        reading = apply_long_vowel_rule(reading)
        result.append(WordMapping(orig, reading, kana_to_cells(reading), idx, idx + len(orig), pos=pos,
                                  attach_prev=bool(result) and pos == "名詞" and detail1 == "接尾"))
        idx += len(orig)
    return result


def convert(text: str) -> list[WordMapping]:
    """段落が複数ある場合は各段落頭に2マスのインデントを入れる。"""
    if not text:
        return []
    lines = text.split("\n")
    multi = len(lines) > 1
    result: list[WordMapping] = []
    idx = 0
    for n, line in enumerate(lines):
        if multi:
            result.append(_indent(idx))
        if line:
            result.extend(tokenize_paragraph(line, idx))
        idx += len(line) + 1
        if multi and n < len(lines) - 1:
            result.append(WordMapping("\n", "", [], idx - 1, idx))
    resolve_all(result)
    return result


__all__ = ["convert", "fallback_convert", "fold_whitespace", "mapping_from_fields", "resolve_all"]
