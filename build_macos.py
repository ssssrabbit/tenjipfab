import os
import subprocess
import sys
import glob

def run_command(command, cwd=None, ignore_error=False):
    """コマンドを実行し、エラーがあれば停止する"""
    print(f"Executing: {command}")
    result = subprocess.run(command, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Error executing command: {command}")
        if not ignore_error:
            sys.exit(1)
        return False
    return True

def main():
    print("🚀 Starting macOS Build Process...")

    # デバッグ: カレントディレクトリ情報の表示
    print(f"Current Directory: {os.getcwd()}")
    if not os.path.exists("main.py"):
        print("❌ Error: main.py not found in current directory.")
        sys.exit(1)

    # pyproject.toml があると設定が競合する場合があるため、一時的にリネームして無効化
    renamed_toml = False
    if os.path.exists("pyproject.toml"):
        print("ℹ️ pyproject.toml detected. Temporarily renaming to avoid conflicts...")
        os.rename("pyproject.toml", "pyproject.toml.bak")
        renamed_toml = True

    try:
        # 0. 依存ライブラリの確認とインストール
        if os.path.exists("requirements.txt"):
            print("Installing dependencies from requirements.txt...")
            run_command("pip install -r requirements.txt")
        
        # 修正: FilePicker等の最新機能に対応するため、Fletを強制的にアップグレード
        print("Upgrading flet to the latest version...")
        run_command("pip install --upgrade flet")

        # 1. クリーンアップ
        if os.path.exists("build"):
            print("Cleaning build directory...")
            run_command("rm -rf build")

        # 2. Fletによるベースプロジェクトの生成
        print("Generating Flutter project...")
        
        # 修正: pyproject.tomlに頼らず、コマンドライン引数で全て指定する
        # --module-name main (拡張子なし) を指定
        cmd = (
            'flet build macos '
            '--module-name main '
            '--product "Tenji P-Fab" '
            '--org "com.yourname.tenjipfab" '
            '--no-android --no-ios'
        )
        run_command(cmd)

        # 3. Entitlements（権限ファイル）の検索と修正
        print("Injecting permissions...")
        
        entitlements_path = None
        # 再帰的に検索
        found = glob.glob("build/**/Release.entitlements", recursive=True)
        if found:
            entitlements_path = found[0]
            print(f"Found entitlements at: {entitlements_path}")
        else:
            print("Error: Entitlements file not found. Build may have failed.")
            sys.exit(1)

        print(f"Editing: {entitlements_path}")
        
        # 権限を追加するXML断片
        permissions = """
        <key>com.apple.security.files.user-selected.read-write</key>
        <true/>
        <key>com.apple.security.files.downloads.read-write</key>
        <true/>
        <key>com.apple.security.network.client</key>
        <true/>
        """

        with open(entitlements_path, "r") as f:
            content = f.read()

        if "<key>com.apple.security.files.user-selected.read-write</key>" not in content:
            content = content.replace("</dict>", f"{permissions}\n</dict>")
            with open(entitlements_path, "w") as f:
                f.write(content)
            print("✅ Permissions injected.")
        else:
            print("ℹ️ Permissions already exist.")

        # 4. Flutterによる再ビルド（変更を反映）
        path_parts = entitlements_path.split(os.sep)
        try:
            macos_index = path_parts.index('macos')
            flutter_root = os.sep.join(path_parts[:macos_index])
        except ValueError:
            print("Could not determine Flutter root. Trying 'build/flutter'...")
            flutter_root = "build/flutter"

        print(f"Rebuilding with Flutter in {flutter_root}...")
        
        if not os.path.exists(flutter_root):
            print(f"Error: Flutter root '{flutter_root}' does not exist.")
            sys.exit(1)

        run_command("flutter build macos --release", cwd=flutter_root)

        print("\n🎉 Build Complete!")
        print(f"Check the output in: {flutter_root}/build/macos/Build/Products/Release/")

    finally:
        # 処理終了後（エラー時含む）、pyproject.toml を元に戻す
        if renamed_toml and os.path.exists("pyproject.toml.bak"):
            print("Restoring pyproject.toml...")
            os.rename("pyproject.toml.bak", "pyproject.toml")

if __name__ == "__main__":
    main()