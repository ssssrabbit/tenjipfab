# Tenji P-Fab:Japanese Braille — 日本語点字を3Dモデルの表面に載せる Blender アドオン

日本語の文章を点字に変換し、選択した3Dモデルの表面に点(ドット)として載せる Blender の拡張機能(Extension)です。
点字ラベルや触知案内の3Dプリント用モデルを、Blender 上でテキストを入力しながら作れます。

- **マニュアル**: [docs/index.html](docs/index.html)(GitHub Pages: https://ssssrabbit.github.io/tenjipfab/blender/docs/)
- **配布ファイル**: [releases/tenji_pfab-0.1.0.zip](releases/tenji_pfab-0.1.0.zip)(Blender の「Install from Disk」でインストール)
- 動作確認: Blender 5.2.1 LTS(macOS)のみ。
- ライセンス: GPL-2.0-or-later([LICENSE](LICENSE))。同梱ライブラリは [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) を参照。

## 仕組み
テキスト → 形態素解析で読みと分かち書きを決める(Janome) → 日本語点字の規則(文部科学省「点字表記法」)で点字セルに変換
→ 選択したモデルの表面へ、視点方向にレイキャストして点を載せる。変換規則の詳細は [RULES.md](RULES.md)。

## 開発
```
# 変換ロジックのテスト(Blender 不要。Python 3.11 以降)
for t in tests/test_*.py; do python3 $t; done

# Extension のビルドと、使い捨てプロファイルでの動作確認(Blender が必要)
python3 tools/build_extension.py      # -> dist/tenji_pfab-<version>.zip
tools/test_extension.sh
```
- `tenji/`: Blender に依存しない変換ロジック。`tenji_blender/`: Blender の UI と点の生成。
  ビルド時に `tenji_blender/` と `tenji/` を Extension の構成に組み直し、Janome の wheel(`extension/wheels/`、git 管理外)を同梱する。
- `tests/golden*.json` は、iOS アプリ版(React Native)の変換コードを実際に実行して作った正解データで、
  Python 版との出力が一致することを確かめている。再生成するには、そのアプリのチェックアウトを `TENJI_RN_APP` で指定する
  (`node tools/gen_golden.js` など。入力は `tests/pipeline_texts.json`)。
