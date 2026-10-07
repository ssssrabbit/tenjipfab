"""Japanese braille tables and kana -> cell conversion.

Port of tenji-pfab-rn/src/logic/brailleLogic.ts. Dots are 6-tuples ordered
(1, 2, 3, 4, 5, 6) i.e. left column top->bottom, then right column top->bottom.
"""
from __future__ import annotations

from dataclasses import dataclass, field

Dots = tuple[int, int, int, int, int, int]


def _d(s: str) -> Dots:
    return tuple(int(c) for c in s)  # type: ignore[return-value]


DAKUTEN_MARK = _d("000010")
HANDAKUTEN_MARK = _d("000001")
YOON_MARK = _d("000100")
YOON_DAKU_MARK = _d("000110")
YOON_HANDAKU_MARK = _d("000101")
NUM_INDICATOR = _d("001111")
FOREIGN_INDICATOR = _d("000011")
SPACE_MARK = _d("000000")
SLASH = _d("001100")               # スラッシュ(点3,4)
CAPITAL_INDICATOR = _d("000001")   # 大文字符(点6)。連続した大文字2字以上は2つ重ねる

# 数字・英字は行頭の1〜0 / a〜j と同形(k〜t は下に dot3 を足した形)。
_ROWS = {
    "1": "100000", "2": "110000", "3": "100100", "4": "100110", "5": "100010",
    "6": "110100", "7": "110110", "8": "110010", "9": "010100", "0": "010110",
    "a": "100000", "b": "110000", "c": "100100", "d": "100110", "e": "100010",
    "f": "110100", "g": "110110", "h": "110010", "i": "010100", "j": "010110",
    "k": "101000", "l": "111000", "m": "101100", "n": "101110", "o": "101010",
    "p": "111100", "q": "111110", "r": "111010", "s": "011100", "t": "011110",
    "u": "101001", "v": "111001", "w": "010111", "x": "101101", "y": "101111", "z": "101011",
    "あ": "100000", "い": "110000", "う": "100100", "え": "110100", "お": "010100",
    "か": "100001", "き": "110001", "く": "100101", "け": "110101", "こ": "010101",
    "さ": "100011", "し": "110011", "す": "100111", "せ": "110111", "そ": "010111",
    "た": "101010", "ち": "111010", "つ": "101110", "て": "111110", "と": "011110",
    "な": "101000", "に": "111000", "ぬ": "101100", "ね": "111100", "の": "011100",
    "は": "101001", "ひ": "111001", "ふ": "101101", "へ": "111101", "ほ": "011101",
    "ま": "101011", "み": "111011", "む": "101111", "め": "111111", "も": "011111",
    "や": "001100", "ゆ": "001101", "よ": "001110",
    "ら": "100010", "り": "110010", "る": "100110", "れ": "110110", "ろ": "010110",
    "わ": "001000", "を": "001110", "ん": "001011",
    "っ": "010000", "ー": "010010", "、": "000011", "，": "000011", "。": "010011", " ": "000000",   # 読点=点5,6 (MEXT PDF の図)
    "？": "010001", "！": "011010",   # 疑問符(2,6)・感嘆符(2,3,5): MEXT「点字表記法」第6章第3節の図による
}
BRAILLE_MAP: dict[str, Dots] = {k: _d(v) for k, v in _ROWS.items()}

# 濁音・半濁音・拗音 -> (種別, 基底文字)
_SPECIAL: dict[str, tuple[str, str]] = {}
for _kind, _pairs in {
    "DAKU": "がか ぎき ぐく げけ ごこ ざさ じし ずす ぜせ ぞそ だた ぢち づつ でて どと ばは びひ ぶふ べへ ぼほ",
    "HANDAKU": "ぱは ぴひ ぷふ ぺへ ぽほ",
    "YOON": "きゃか きゅく きょこ しゃさ しゅす しょそ ちゃた ちゅつ ちょと にゃな にゅぬ にょの "
            "ひゃは ひゅふ ひょほ みゃま みゅむ みょも りゃら りゅる りょろ",
    "YOON_DAKU": "ぎゃか ぎゅく ぎょこ じゃさ じゅす じょそ ぢゃた ぢゅつ ぢょと びゃは びゅふ びょほ",
    "YOON_HANDAKU": "ぴゃは ぴゅふ ぴょほ",
}.items():
    for _p in _pairs.split():
        _SPECIAL[_p[:-1]] = (_kind, _p[-1])

_MARKS = {
    "DAKU": (DAKUTEN_MARK, "゛"),
    "HANDAKU": (HANDAKUTEN_MARK, "゜"),
    "YOON": (YOON_MARK, "拗"),
    "YOON_DAKU": (YOON_DAKU_MARK, "拗゛"),
    "YOON_HANDAKU": (YOON_HANDAKU_MARK, "拗゜"),
}


@dataclass
class Cell:
    dots: Dots
    char: str


@dataclass
class WordMapping:
    orig: str
    reading: str
    cells: list[Cell]
    start: int
    end: int
    is_paragraph_start: bool = False
    pos: str | None = None
    attach_prev: bool = False   # 直前の語に続けて書く(接尾語・助数詞)
    gap: int | None = None      # この語の後ろの空白マス数をユーザーが指定(None=規則で自動)

    @property
    def braille(self) -> list[Dots]:
        return [c.dots for c in self.cells]


def katakana_to_hiragana(text: str) -> str:
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in text)


def kana_to_cells(text: str) -> list[Cell]:
    cells: list[Cell] = []
    if not text:
        return cells
    if text.strip() == "":
        return [Cell(SPACE_MARK, " ") for _ in text]

    mode = "kana"
    i = 0
    while i < len(text):
        ch = text[i]
        pair = text[i:i + 2]
        key = pair if len(pair) == 2 and pair in _SPECIAL else ch if ch in _SPECIAL else None
        if key is not None:
            kind, base = _SPECIAL[key]
            mark, mark_char = _MARKS[kind]
            cells.append(Cell(mark, mark_char))
            cells.append(Cell(BRAILLE_MAP.get(base, SPACE_MARK), base))
            i += len(key)
            continue

        if ch in "/／":
            # スラッシュ: 外字符で書くアルファベットの間は外字符の効力が続く。数字の間では前に外字符を置き、
            # 後ろの数字には数符を付け直す(MEXT 点字表記法 第6章第3節 関係符号)
            if mode == "number":
                cells.append(Cell(FOREIGN_INDICATOR, "外"))
                cells.append(Cell(SLASH, "／"))
                mode = "slash"
            elif mode == "foreign":
                cells.append(Cell(SLASH, "／"))
            i += 1
            continue

        if "0" <= ch <= "9":
            if mode != "number":
                cells.append(Cell(NUM_INDICATOR, "#"))
                mode = "number"
            cells.append(Cell(BRAILLE_MAP[ch], ch))
        elif ch.isascii() and ch.isalpha():
            if mode != "foreign":
                cells.append(Cell(FOREIGN_INDICATOR, "外"))
                mode = "foreign"
            if ch.isupper() and not (i > 0 and text[i - 1].isascii() and text[i - 1].isupper()):
                run = 1
                while i + run < len(text) and text[i + run].isascii() and text[i + run].isupper():
                    run += 1
                cells.extend(Cell(CAPITAL_INDICATOR, "大") for _ in range(2 if run >= 2 else 1))
            cells.append(Cell(BRAILLE_MAP[ch.lower()], ch))
        elif ch in BRAILLE_MAP:
            mode = "kana"
            cells.append(Cell(BRAILLE_MAP[ch], ch))
        # 未対応文字はスキップ(TS 版と同じ)
        i += 1
    return cells


def fallback_convert(text: str) -> list[WordMapping]:
    return [WordMapping(ch, ch, kana_to_cells(ch), i, i + 1) for i, ch in enumerate(text)]
