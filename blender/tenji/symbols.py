"""波線・矢印・外字系の記号・数字の伏せ字 (文部科学省「点字表記法」第6章第3節。点の配置は同PDFの図から)。

波線   = 第1つなぎ符(点3,6)×2。前後を空けない。
矢印   = 「ーーた」(点2,5 / 点2,5 / 点1,3,5)。前後1マス。
外字系 = 外字符(点5,6) + 1セル: ％(点1,2,3,4) ＆(点1,2,3,4,6) ＃(点1,4,6) ＊(点1,6) ＠(点2,4,6)。
         ％は数字の後ろに続ける。＃＊の直後に数字が続くときは続ける。＆＠は前後1マス。
         ％＃＊の後ろに助詞・助動詞が続くときは1マス、ひと続きの語(接尾語など)が続くときはつなぎ符。
中点   = 点5。直前に続け、後ろ1マス。数字の区切りには書かず、後ろの数字に数符を付ける(五・六十 → 数5 数60)。
棒線   = 点2,5 ×2セル(ーー)。前後1マス。「―」「—」「─」の連なり2字につき1つ。
点線   = 点2 ×3セル。「…」1字につき1つ。前後1マス、句読点・閉じ符号が続くときは続ける。
伏せ字 = 数字の伏せ字「×」1つにつき2セル(点5 / 点1〜6)。数符の有効範囲の中なので、後ろの数字に数符は付けない。
         後ろの文字との間はつなぎ符、助詞・助動詞が続くときは1マス。
"""
from __future__ import annotations

from .braille import NUM_INDICATOR, Cell, WordMapping, _d

TSUNAGI = "001001"                      # 第1つなぎ符 (点3,6)
FOREIGN = "000011"                      # 外字符
SYMBOLS: dict[str, list[str]] = {
    "〜": [TSUNAGI, TSUNAGI], "～": [TSUNAGI, TSUNAGI],
    "→": ["010010", "010010", "101010"],
    "…": ["010000"] * 3,                       # 点線
    "・": ["000010"], "･": ["000010"],          # 中点
}
DASHES = set("―—─")                              # 棒線
WAVE = {"〜", "～"}

# 外字符に続くセル。キー: 入力文字(全角・半角)。
_FOREIGN_SYMBOL = {"％": "111100", "＆": "111101", "＃": "100101", "＊": "100001", "＠": "010101"}
_FULLWIDTH = {"%": "％", "&": "＆", "#": "＃", "*": "＊", "@": "＠"}
FOREIGN_SYMBOLS = set(_FOREIGN_SYMBOL) | set(_FULLWIDTH)
MASK = "×"
MASK_CELLS = ["000010", "111111"]
# 後ろに助詞・助動詞が続くとき1マスあける記号
GAP_BEFORE_PARTICLE = {"％", "%", "＃", "#", "＊", "*", MASK, "…"}
# 直後に数字が続くとき空けない記号
ATTACH_NUMBER = {"＃", "#", "＊", "*"}
# つなぎ符の判定で「アルファベット相当」とみなす記号(セル側の文字)
LETTERLIKE_CHARS = set("％＃＊") | {MASK}
# トークン分割の対象(複数文字トークンに混ざっていたら単独に切り出す)
SPLIT_CHARS = FOREIGN_SYMBOLS | {MASK, "→", "〜", "～", "…", "・", "･"} | DASHES


def _is_number(m: WordMapping) -> bool:
    return bool(m.cells) and m.cells[0].dots == NUM_INDICATOR


def _ends_with_digit(m: WordMapping) -> bool:
    return bool(m.cells) and m.cells[-1].char in "0123456789"


def resolve_symbols(mapped: list[WordMapping]) -> None:
    for m in mapped:
        ch = m.orig
        if ch in SYMBOLS:
            m.cells = [Cell(_d(p), ch) for p in SYMBOLS[ch]]
        elif ch in FOREIGN_SYMBOLS:
            full = _FULLWIDTH.get(ch, ch)
            m.cells = [Cell(_d(FOREIGN), "外"), Cell(_d(_FOREIGN_SYMBOL[full]), full)]
            m.attach_prev = full == "％"       # ％は数字の後ろに続ける(他は辞書の品詞に関わらず分かち書き)

    # 中点: 数字の区切りには書かない(後ろの数字の数符が区切りになる)
    for i in range(1, len(mapped) - 1):
        m = mapped[i]
        if m.orig in ("・", "･") and _ends_with_digit(mapped[i - 1]) and _is_number(mapped[i + 1]):
            m.cells = []
            mapped[i + 1].attach_prev = True

    # 棒線: 連なった「―」2字につき1つ(2セル)
    i = 0
    while i < len(mapped):
        if mapped[i].orig and all(c in DASHES for c in mapped[i].orig):
            j, n = i, 0
            while j < len(mapped) and mapped[j].orig and all(c in DASHES for c in mapped[j].orig):
                n += len(mapped[j].orig)
                j += 1
            mapped[i].cells = [Cell(_d("010010"), "ー") for _ in range(2 * ((n + 1) // 2))]
            for k in range(i + 1, j):
                mapped[k].cells = []
                mapped[k].attach_prev = True
            i = j
        else:
            i += 1

    # 数字の伏せ字: 数字の直後の「×」の連なり
    i, n = 0, len(mapped)
    while i < n:
        if mapped[i].orig == MASK and i > 0 and (_ends_with_digit(mapped[i - 1]) or False):
            j = i
            while j < n and mapped[j].orig == MASK:
                j += 1
            nxt = mapped[j] if j < n else None
            # 掛け算(3×4)との区別: 1つだけで後ろに数字が続く場合は伏せ字とみなさない
            if j - i >= 2 or nxt is None or not _is_number(nxt):
                for k in range(i, j):
                    mapped[k].cells = [Cell(_d(p), MASK) for p in MASK_CELLS]
                    mapped[k].attach_prev = True
                if nxt is not None and _is_number(nxt):
                    nxt.cells = nxt.cells[1:]           # 数符の有効範囲内: 数符を付け直さない
                    nxt.attach_prev = True
            i = j
        else:
            i += 1
