"""カギ類・カッコ類 (文部科学省「点字表記法」第6章第3節 囲み符号の用法)。

点の配置は同 PDF の図から読み取ったもの(左列=点1,2,3 / 右列=点4,5,6 の順の6桁)。
入力文字 -> 種別:
  「 」 第1カギ(カギの中のカギ・『』 はふたえカギ)   〈 〉 第2カギ
  （ ） 第1カッコ(カッコの中のカッコは二重カッコ)   〔 〕 ［ ］ 第2カッコ
"""
from __future__ import annotations

from .braille import Cell, WordMapping, _d

# 種別 -> (開き符号のセル列, 閉じ符号のセル列)
STYLES: dict[str, tuple[list[str], list[str]]] = {
    "KAGI1":        (["001001"],            ["001001"]),
    "KAGI_FUTAE":   (["000011", "001001"],  ["001001", "011000"]),
    "KAGI2":        (["000011", "001000"],  ["000001", "011000"]),
    "KAKKO1":       (["011011"],            ["011011"]),
    "KAKKO_FUTAE":  (["000011", "011011"],  ["011011", "011000"]),
    "KAKKO2":       (["000010", "011011"],  ["011011", "010000"]),
}

# 文字 -> (系統, 既定の種別)
OPENERS = {"「": ("KAGI", "KAGI1"), "『": ("KAGI", "KAGI_FUTAE"), "〈": ("KAGI", "KAGI2"),
           "（": ("KAKKO", "KAKKO1"), "(": ("KAKKO", "KAKKO1"),
           "〔": ("KAKKO", "KAKKO2"), "［": ("KAKKO", "KAKKO2"), "[": ("KAKKO", "KAKKO2")}
CLOSERS = {"」": ("KAGI", "KAGI1"), "』": ("KAGI", "KAGI_FUTAE"), "〉": ("KAGI", "KAGI2"),
           "）": ("KAKKO", "KAKKO1"), ")": ("KAKKO", "KAKKO1"),
           "〕": ("KAKKO", "KAKKO2"), "］": ("KAKKO", "KAKKO2"), "]": ("KAKKO", "KAKKO2")}


def _cells(patterns: list[str], ch: str) -> list[Cell]:
    return [Cell(_d(p), ch) for p in patterns]


def resolve_brackets(mapped: list[WordMapping]) -> None:
    """括弧トークンのセルを、入れ子の状態を見て決める(in place)。"""
    stack: list[tuple[str, str]] = []   # (系統, 種別)
    for m in mapped:
        ch = m.orig
        if ch in OPENERS:
            family, style = OPENERS[ch]
            if family == "KAGI" and style == "KAGI1" and any(f == "KAGI" and s in ("KAGI1", "KAGI_FUTAE") for f, s in stack):
                style = "KAGI_FUTAE"                       # カギの中のカギ
            elif family == "KAKKO" and any(f == "KAKKO" for f, _ in stack):
                style = "KAKKO_FUTAE"                      # カッコの中のカッコ
            stack.append((family, style))
            m.cells = _cells(STYLES[style][0], ch)
        elif ch in CLOSERS:
            family, style = CLOSERS[ch]
            for i in range(len(stack) - 1, -1, -1):        # 対応する開きを探す
                if stack[i][0] == family:
                    style = stack.pop(i)[1]
                    break
            m.cells = _cells(STYLES[style][1], ch)
