#!/bin/bash
# Build the extension, install it into a throw-away Blender profile (your real profile and its add-ons are untouched),
# and run the smoke test. Usage: tools/test_extension.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
B="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/ext" "$T/cfg" "$T/scr"
export BLENDER_USER_EXTENSIONS="$T/ext" BLENDER_USER_CONFIG="$T/cfg" BLENDER_USER_SCRIPTS="$T/scr"
python3 "$ROOT/tools/build_extension.py"
VER=$(python3 -c "import tomllib;print(tomllib.load(open('$ROOT/extension/blender_manifest.toml','rb'))['version'])")
"$B" --factory-startup -b --command extension install-file -r user_default --enable "$ROOT/dist/tenji_braille-$VER.zip" 2>&1 | grep -E "STATUS|ERROR"
"$B" --factory-startup -b --python-exit-code 1 --python "$ROOT/tools/smoke_extension.py" 2>&1 | grep -E "SMOKE OK|Error|Traceback|assert"
