# Tenji P-Fab — ビルド手順

## 必要な環境

| ツール | バージョン | 確認方法 |
|--------|-----------|----------|
| Node.js | 18 以上 | `node -v` |
| npm | 9 以上 | `npm -v` |
| Xcode | 15 以上（iOS ビルド時） | App Store |
| iOS Simulator または実機 | iOS 16 以上 | |

## セットアップ

```bash
# 依存パッケージのインストール
npm install
```

## 開発用起動（Expo Go 不使用・フルネイティブビルド）

iOS シミュレータ:
```bash
npx expo run:ios
```

初回または native module 変更後（クリーンビルド）:
```bash
npx expo run:ios --no-build-cache
```

実機の場合は Mac に接続した状態で Xcode を開き Product → Run を実行。

## 注意事項

- `assets/dict/` に kuromoji 日本語辞書ファイル（約 17 MB）が含まれます
- 初回起動時に辞書がアプリのドキュメントディレクトリへコピーされます（数秒かかります）
- iOS の言語設定が日本語の場合、UI・点字のデフォルト言語が日本語になります

## プロジェクト構成

```
App.tsx                  エントリポイント
src/
  screens/HomeScreen.tsx メイン画面
  components/            UI コンポーネント
  logic/                 点字変換・STL生成ロジック
  stores/historyStore.ts 設定・履歴管理（Zustand）
  constants/colors.ts    カラー定義
assets/
  dict/                  kuromoji 辞書ファイル
  *.png                  アイコン・ロゴ
```

## トラブルシューティング

### `No such module 'Expo'` / `Module map file '…/EXConstants.modulemap' not found`
Xcode で **`ios/TenjiPFab.xcodeproj` を直接開いている** のが原因です(Pods が含まれず、Expo などのモジュールが作られません)。
**`ios/TenjiPFab.xcworkspace` を開いて**ビルドしてください(または `npx expo run:ios`)。
Xcode で開いたファイルは、DerivedData の `info.plist` の `WorkspacePath` でも確認できます。

### `IPHONEOS_DEPLOYMENT_TARGET is set to 13.4, but the range of supported deployment target versions is 15.0 to …`
Xcode 27(iOS 27 SDK)が 15.0 未満の配備ターゲットを受け付けないためです(例: async-storage のリソース用ターゲットが 13.4)。
`plugins/withMinPodDeploymentTarget.js`(`app.json` の `plugins` に登録済み)が、`expo prebuild` 時に Podfile へ補正を入れます。
`ios/` を作り直したときは `npx expo prebuild --platform ios` を実行してください。手元の `ios/Podfile` を直接直した場合は、
`cd ios && LANG=en_US.UTF-8 pod install` で Pods に反映します。
