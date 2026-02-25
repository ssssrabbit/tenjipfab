#!/bin/bash

echo "========================================"
echo "  CocoaPodsパス解決 & ビルドスクリプト"
echo "========================================"

# 1. パスの強制解決 (シンボリックリンク作成)
# Flutterが参照する /usr/local/bin に Homebrew版podへのリンクを作成します
echo "[1/3] パス解決のためシンボリックリンクを作成します..."
if [ -f "/opt/homebrew/bin/pod" ]; then
    echo "パスワードを求められた場合は入力してください。"
    sudo ln -sf /opt/homebrew/bin/pod /usr/local/bin/pod
    echo "リンクを作成しました: /usr/local/bin/pod -> /opt/homebrew/bin/pod"
else
    echo "Homebrew版podが見つかりません。インストール後に再試行される可能性があります。"
fi

# 2. CocoaPodsの確認とインストール
if ! command -v pod &> /dev/null; then
    echo "[2/3] CocoaPodsが見つかりません。Homebrewでインストールします..."
    
    # 既存の競合を削除
    sudo gem uninstall cocoapods -aIx > /dev/null 2>&1
    
    # Homebrewでインストール
    brew install cocoapods
    brew link --overwrite cocoapods
else
    echo "[2/3] CocoaPods は既にインストールされています。"
    pod --version
fi

# 3. ビルド実行
echo "[3/3] アプリのビルドを開始します..."

# flutter doctorで認識されているか確認（念のため）
flutter doctor -v | grep "CocoaPods"

# ビルド
flet build macos --product "Tenji P-Fab" --org "com.yourname.tenjipfab"
