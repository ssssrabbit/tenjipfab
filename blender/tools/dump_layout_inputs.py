"""Dump WordMapping inputs (from the Python converter) for the TS layout golden run."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from tenji.japanese import convert

TEXTS = ["私は東京へ行きました。", "今日はいい天気です", "点字を自動的に変換する", "東京都立大学へ行くつもりです",
         "こんにちは\nさようなら\n\nおやすみなさい", "123円のりんごを買った", "ABCは英語です",
         "きゃきゅきょがっこうぱぴぷぺぽ", "どうして？本当に！そうなの。", "「いいね」。はい、そう。", "先生は、「みんなの前で話すときは『伝えようとする気持ち』が大切です。」と、お話しになった。",
         "（1890年〔明治23年〕に採用された）", "「やあ、元気だった？」自然に声が弾んだ。",
         "100円玉を買う", "X線とDOSとAがある", "3らしい", "東京8時36分→長野10時2分→金沢11時9分", "10時～12時、東京～大阪", "山田さんと5個のりんご", "DOS/Vの規格と血圧は125/85", "5・60と5・15事件", "のれんに腕押し――糠に釘、そして…。", "20××年と内線1××4番", "100％だった20％引き", "＊11は本社の短縮番号", "「＃点字」か「＃braille」", "商品5個＠200円とQ&A", "あっ！と叫んだ。", "え？と聞いた。いいよ。",
         "とてもながいたんごをとてもみじかいはばにおさめる"]
out = []
for t in TEXTS:
    out.append({"text": t, "mapped": [
        {"orig": m.orig, "reading": m.reading, "start": m.start, "end": m.end, "pos": m.pos,
         "isParagraphStart": m.is_paragraph_start, "attachPrev": m.attach_prev,
         "cells": [{"dots": list(c.dots), "char": c.char} for c in m.cells]} for m in convert(t)]})
json.dump(out, open("tests/layout_inputs.json", "w"), ensure_ascii=False)
