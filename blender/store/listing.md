# extensions.blender.org 掲載用の資料

登録フォームの各項目に、そのまま貼り付ける文章と、アップロードする画像です(フォームは Blender ID でのログインが必要で、必須・任意の区別と画像の指定サイズは、フォームの案内で確認してください)。
Name / Tagline / License / Maintainer などは、zip の `blender_manifest.toml` から読み取られます。

## Description(説明。Markdown)

```markdown
**Project Japanese braille onto the surface of your 3D models.**

Type Japanese text and this add-on converts it to Japanese braille (6-dot) and places the dots on the surface of the selected mesh. It is made for tactile labels and 3D-printable models. Press "更新" (Update) to redo conversion, word spacing, line breaks and dot generation, so you can adjust the text to fit the model. An optional "自動で更新" (auto update) toggle, off by default, does this on every change.

### Features
- Japanese text to braille: readings and word spacing are decided by morphological analysis (Janome); braille rules follow the Japanese Ministry of Education (MEXT) braille notation guidelines (punctuation, brackets, numbers, Latin letters, joining marks and more).
- One button: select a mesh, face the surface you want, press "選択モデルに点字作成" (create braille on the selected model).
- One-button update (optional auto update, off by default). Spaces can be typed in the text or set per word; readings can be edited.
- Line wrapping by braille rules, or a fixed number of cells per line.
- Standard Japanese braille dimensions by default (2.4 mm dot pitch, 6.0 mm cell pitch), all adjustable. The default dot height is a gentle 0.3 mm. "Output size" scales the dots for the size you will print.
- Verification: reads the generated dots back and checks them against the expected braille.
- Flat and gently curved surfaces. Several labels per scene.

### Notes
- Japanese braille only. The user interface is in Japanese.
- Works offline (no network access).
- Tested on Blender 5.2.1 LTS on macOS only; not yet tested with actual 3D prints.
- Bundles Janome 0.5.0 (Apache-2.0) with the MeCab-IPADIC dictionary.
- The source code is available under the MIT license on GitHub; this extension package is distributed under GPL-3.0-or-later.

User manual (Japanese): https://ssssrabbit.github.io/tenjipfab/blender/docs/

---

**日本語の文章を点字に変換し、選択した3Dモデルの表面に点として載せます。**

点字ラベルや、3Dプリント用の触って分かるモデルを作るための拡張機能です。入力するたびに、分かち書き・点字変換・モデル上の点の生成をやり直すので、モデルに合わせて文章や空白を調整できます。点字の規則は、文部科学省「点字表記法」に基づいています。点の間隔・大きさ・高さは調整でき、3Dプリントの出力サイズに合わせた換算もできます。日本語点字のみ対応です。

使い方: モデルを選択 → 点字を載せたい面を正面に向ける → 「選択モデルに点字作成」を押す → テキストを入力。詳しくはマニュアルをご覧ください。
```

## Support(URL)

```
https://github.com/ssssrabbit/tenjipfab/issues
```

(リポジトリ自身の課題管理を、サポートの URL にします。マニュアル: https://ssssrabbit.github.io/tenjipfab/blender/docs/)

## Release notes(0.1.1)

```markdown
**0.1.1**

- Removed all threading (the background dictionary pre-load) and the depsgraph handler that rebuilt the dots when the frame or the target moved.
- New "更新" (Update) button: redoes word splitting, braille conversion and dot generation in one step.
- "自動で更新" (auto update) is now optional and off by default.
- Tag changed to "Add Mesh".

**0.1.0 — Initial release / 初版**

- Create Japanese braille on the surface of the selected mesh with one button ("選択モデルに点字作成").
- Update button: reading, word spacing, braille conversion and dot generation (optional auto update, off by default).
- Braille rules based on the MEXT braille notation guidelines: kana, voiced/semi-voiced/contracted sounds, long vowels, numbers, Latin letters, punctuation, brackets, joining marks, wave dash, arrow, ellipsis, dash, percent, ampersand, number sign, asterisk, at sign, slash, hidden digits.
- Spaces: type them in the text (N spaces = exactly N cells) or set them per word; option to turn automatic spacing off.
- Line wrapping by braille rules or by a fixed number of cells per line.
- Adjustable dimensions; "output size" scaling for 3D printing.
- Verification (read-back) of the generated dots; several labels per scene.
- Tested on Blender 5.2.1 LTS (macOS) only.
```

## 画像

| 項目 | ファイル | サイズ |
|---|---|---|
| アイコン | `icon-256.png` | 256 × 256 |
| Featured image | `featured-1920x1080.png` | 1920 × 1080 |
| Preview 1 | `preview-1-workflow.png` | 1920 × 1080 |
| Preview 2 | `preview-2-curved-surface.png` | 1920 × 1080 |
| Preview 3 | `preview-3-multiple-labels.png` | 1920 × 1080 |
| Preview 4 | `preview-4-panel.png` | 1920 × 1080 |

プレビューの説明文(キャプション)の案:
1. Type text, press "更新", and the braille appears on the model.
2. The dots follow a gently curved surface.
3. Several labels on one model: finish one with "新規点字" and start the next.
4. Select a mesh, face the surface, press "選択モデルに点字作成", type, then press "更新".

画像は `python3 tools/make_store_assets.py` で作り直せます(実際の Blender の画面写真 `docs/images/` と、macOS のフォントを使います)。
