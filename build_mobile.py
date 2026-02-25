import os
import subprocess
import sys
import glob
import argparse

def run_command(command, cwd=None, ignore_error=False):
    print(f"Executing: {command}")
    result = subprocess.run(command, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Error executing command: {command}")
        if not ignore_error:
            sys.exit(1)
        return False
    return True

def inject_ios_permissions(flutter_root):
    """iOSのInfo.plistに権限と設定を追加"""
    plist_path = os.path.join(flutter_root, "ios", "Runner", "Info.plist")
    if not os.path.exists(plist_path):
        print(f"Warning: {plist_path} not found.")
        return

    print(f"Injecting iOS permissions into {plist_path}...")
    
    # 追加する設定
    # UIRequiresFullScreen: iPadでマルチタスクを無効化し全画面にする
    # ITSAppUsesNonExemptEncryption: 輸出コンプライアンスの質問を「いいえ」で自動回答
    permissions = """
    <key>UIRequiresFullScreen</key>
    <true/>
    <key>ITSAppUsesNonExemptEncryption</key>
    <false/>
    <key>LSSupportsOpeningDocumentsInPlace</key>
    <true/>
    <key>UIFileSharingEnabled</key>
    <true/>
    <key>UISupportsDocumentBrowser</key>
    <true/>
    """
    
    with open(plist_path, "r") as f:
        content = f.read()

    # 重複追加を防ぐため、キーの存在確認
    if "<key>UIFileSharingEnabled</key>" not in content:
        # <dict>の直後に追加
        content = content.replace("<dict>", f"<dict>{permissions}")
        with open(plist_path, "w") as f:
            f.write(content)
        print("✅ iOS Permissions injected (inc. FullScreen & Encryption).")
    else:
        print("ℹ️ iOS Permissions already exist.")

def inject_android_permissions(flutter_root):
    """AndroidのAndroidManifest.xmlに権限を追加"""
    manifest_path = os.path.join(flutter_root, "android", "app", "src", "main", "AndroidManifest.xml")
    if not os.path.exists(manifest_path):
        print(f"Warning: {manifest_path} not found.")
        return

    print(f"Injecting Android permissions into {manifest_path}...")
    
    # 追加する権限
    permissions = """
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"/>
    """
    
    with open(manifest_path, "r") as f:
        content = f.read()

    if "android.permission.WRITE_EXTERNAL_STORAGE" not in content:
        # <application>タグの前に追加
        if "<application" in content:
            content = content.replace("<application", f"{permissions}\n    <application")
            with open(manifest_path, "w") as f:
                f.write(content)
            print("✅ Android Permissions injected.")
    else:
        print("ℹ️ Android Permissions already exist.")

def process_build(target, version, build_number):
    """指定されたターゲットのビルドプロセスを実行"""
    print(f"\n🚀 Starting build for {target} [Version: {version}, Build: {build_number}]")

    # 1. クリーンアップ (ターゲット切り替え時に重要)
    if os.path.exists("build"):
        print("Cleaning build directory...")
        run_command("rm -rf build")

    # 2. Fletプロジェクト生成
    print(f"Generating Flutter project for {target}...")
    flet_cmd_base = "flet build apk" if target == "android" else "flet build ipa"
    
    # バージョンオプションを指定してプロジェクト生成
    flet_cmd = f"{flet_cmd_base} --module-name main --no-web"# --build-name {version} --build-number {build_number}"
    run_command(flet_cmd, ignore_error=True)

    # Flutterプロジェクトルートを特定
    flutter_root = "build/flutter"
    if not os.path.exists(flutter_root):
        found = glob.glob("build/**/pubspec.yaml", recursive=True)
        if found:
            flutter_root = os.path.dirname(found[0])
    
    if not os.path.exists(flutter_root):
        print("Error: Could not find generated Flutter project.")
        sys.exit(1)

    print(f"Flutter project root: {flutter_root}")

    # 3. 権限注入 & ビルド
    if target == "ios":
        inject_ios_permissions(flutter_root)
        print("Building for iOS Simulator...")
        # 必要に応じて --simulator を外してください (実機ビルドの場合)
        run_command("flutter build ios --simulator --debug", cwd=flutter_root)
        
        app_path = os.path.join(flutter_root, "build/ios/iphonesimulator/Runner.app")
        print("\n🎉 iOS Build Complete!")
        print(f"App Bundle: {app_path}")

    elif target == "android":
        inject_android_permissions(flutter_root)
        print("Building for Android (APK)...")
        # デバッグ用APK
        run_command("flutter build apk --debug", cwd=flutter_root)
        
        apk_path = os.path.join(flutter_root, "build/app/outputs/flutter-apk/app-debug.apk")
        print("\n🎉 Android Build Complete!")
        print(f"APK File: {apk_path}")

def main():
    parser = argparse.ArgumentParser(description="Build Flet app for Mobile")
    parser.add_argument("target", choices=["ios", "android", "all"], help="Build target (ios, android, or all)")
    parser.add_argument("--version", default="1.0.0", help="App version string (e.g. 1.0.0)")
    parser.add_argument("--build-number", default="1", help="Build number integer (e.g. 2)")
    
    args = parser.parse_args()
    
    # 依存ライブラリインストール (最初だけ実行)
    if os.path.exists("requirements.txt"):
        print("Installing dependencies...")
        run_command("pip install -r requirements.txt")

    targets = ["ios", "android"] if args.target == "all" else [args.target]

    for t in targets:
        process_build(t, args.version, args.build_number)

if __name__ == "__main__":
    main()