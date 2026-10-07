#!/usr/bin/env python3
"""Build the Blender Extension (zip) from the repo sources.

  python3 tools/build_extension.py            # -> dist/tenji_pfab-<version>.zip

Repo layout (tests import `tenji` as a top-level pure-Python package) is rearranged into the Extension layout:
  <ext>/__init__.py, core.py   (from tenji_blender/, imports rewritten to the bundled subpackage)
  <ext>/tenji/                 (pure-Python braille logic)
  <ext>/wheels/Janome-*.whl    (downloaded with pip if missing)
  <ext>/blender_manifest.toml  (extension/blender_manifest.toml)
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
MANIFEST = ROOT / "extension" / "blender_manifest.toml"
WHEEL_DIR = ROOT / "extension" / "wheels"          # git-ignored cache


def main() -> None:
    manifest = tomllib.loads(MANIFEST.read_text())
    ext_id, version = manifest["id"], manifest["version"]
    dist = ROOT / "dist"
    out = dist / ext_id
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # 1) sources
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(ROOT / "tenji", out / "tenji", ignore=ignore)
    for name in ("__init__.py", "core.py"):
        text = (ROOT / "tenji_blender" / name).read_text()
        text = re.sub(r"^(\s*)from tenji\.", r"\1from .tenji.", text, flags=re.M)
        if re.search(r"^\s*(from|import) tenji(\.|\s|$)", text, flags=re.M):
            sys.exit(f"unrewritten absolute import of 'tenji' left in {name}")
        (out / name).write_text(text)
    shutil.copy(MANIFEST, out / "blender_manifest.toml")
    shutil.copy(ROOT / "extension" / "LICENSE", out / "LICENSE")   # zip は GPL-3.0-or-later(リポジトリの LICENSE は MIT)

    # 2) wheels
    (out / "wheels").mkdir()
    for rel in manifest.get("wheels", []):
        fname = pathlib.Path(rel).name
        name = fname.split("-")[0]
        cached = WHEEL_DIR / fname
        if not cached.exists():
            WHEEL_DIR.mkdir(parents=True, exist_ok=True)
            ver = fname.split("-")[1]
            subprocess.run([sys.executable, "-m", "pip", "download", f"{name}=={ver}", "--no-deps",
                            "--only-binary=:all:", "-d", str(WHEEL_DIR)], check=True)
        shutil.copy(cached, out / "wheels" / fname)
        # 第三者のライセンス表示(IPAdic の「無保証」条項は配布物に添付する必要がある)を、見つけやすい場所にも出す
        with zipfile.ZipFile(cached) as zf:
            (out / "THIRD_PARTY").mkdir(exist_ok=True)
            for member in zf.namelist():
                base = pathlib.Path(member).name
                if ".dist-info/" in member and base in ("LICENSE.txt", "NOTICE.txt"):
                    (out / "THIRD_PARTY" / f"{name}-{base}").write_bytes(zf.read(member))

    # 3) build + validate with Blender's own tooling
    subprocess.run([BLENDER, "--command", "extension", "build", "--source-dir", str(out),
                    "--output-dir", str(dist)], check=True)
    zip_path = dist / f"{ext_id}-{version}.zip"
    subprocess.run([BLENDER, "--command", "extension", "validate", str(zip_path)], check=True)
    print(f"built {zip_path} ({zip_path.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
