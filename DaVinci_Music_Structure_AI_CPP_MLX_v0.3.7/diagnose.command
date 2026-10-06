#!/bin/bash
set +e
ROOT="$(cd "$(dirname "$0")" && pwd)"
R="$HOME/Library/Application Support/MusicStructureAI_CPP"; V="$R/.venv"; APP="$HOME/Applications/Music Structure AI.app/Contents/MacOS/MusicStructureAI"
echo "=== Music Structure AI v0.3.6 Diagnose ==="
echo "macOS: $(sw_vers -productVersion 2>/dev/null)"
echo "arch: $(uname -m)"
echo "Developer directory: $(xcode-select -p 2>&1)"
echo "xcrun: $(command -v xcrun 2>/dev/null)"
echo "Apple clang++: $(xcrun --sdk macosx --find clang++ 2>&1)"
SDK="$(xcrun --sdk macosx --show-sdk-path 2>/dev/null)"
echo "macOS SDK: ${SDK:-NOT FOUND}"
if [[ -n "$SDK" ]]; then
  H="$SDK/System/Library/Frameworks/Cocoa.framework/Headers/Cocoa.h"
  if [[ -f "$H" ]]; then echo "Cocoa header: OK ($H)"; else echo "Cocoa header: MISSING ($H)"; fi
  echo "Cocoa compile preflight:"
  printf '#import <Cocoa/Cocoa.h>\nint main(){return 0;}\n' | xcrun --sdk macosx clang++ -x objective-c++ -fblocks -fsyntax-only -isysroot "$SDK" - && echo "  OK" || echo "  FAILED"
  if [[ -f "$ROOT/controller/main.mm" ]]; then
    echo "Controller full syntax check:"
    xcrun --sdk macosx clang++ -std=c++17 -fobjc-arc -fblocks -fsyntax-only -isysroot "$SDK" -mmacosx-version-min=14.0 "$ROOT/controller/main.mm" && echo "  OK" || echo "  FAILED"
  fi
fi

echo "MLX weights:"
W="$R/mlx-weights"
MISSING=0
for fold in 0 1 2 3 4 5 6 7; do
  for ext in npz yaml; do
    P="$W/harmonix-fold${fold}_mlx.${ext}"
    if [[ -f "$P" ]]; then echo "  OK $(basename "$P") ($(stat -f%z "$P" 2>/dev/null) bytes)"; else echo "  MISSING $P"; MISSING=1; fi
  done
done

if [[ -x "$APP" ]]; then "$APP" --self-test; else echo "App binary: not installed/built yet"; fi
if [[ -x "$V/bin/python" ]]; then
  "$V/bin/python" --version
  "$V/bin/python" -m pip show all-in-one-mlx 2>/dev/null | grep -E '^(Name|Version|Location):'
  "$V/bin/python" -m pip show demucs-mlx 2>/dev/null | grep -E '^(Name|Version|Location):'
  echo "HTDemucs convert dependencies:"
  "$V/bin/python" -c 'import importlib.util; [print(f"  {n}: {chr(79)+chr(75) if importlib.util.find_spec(n) else chr(77)+chr(73)+chr(83)+chr(83)+chr(73)+chr(78)+chr(71)}") for n in ("torch","demucs","demucs_mlx")]'
  echo "HTDemucs source checkpoint:"
  CKPT="$HOME/.cache/torch/hub/checkpoints/955717e8-8726e21a.th"
  EXPECTED="8726e21a993978c7ba086d3872e7608d7d5bfca646ca4aca459ffda844faa8b4"
  if [[ -f "$CKPT" ]]; then
    ACTUAL="$(/usr/bin/shasum -a 256 "$CKPT" | /usr/bin/awk '{print $1}')"
    if [[ "$ACTUAL" == "$EXPECTED" ]]; then echo "  SHA-256 OK"; else echo "  BAD SHA-256: $ACTUAL"; fi
  else echo "  MISSING: $CKPT"; fi
  echo "HTDemucs MLX bootstrap:"
  "$V/bin/python" -c 'from demucs_mlx import Separator; Separator(model="htdemucs", progress=False); print("  HTDEMUCS_MLX_READY")' || echo "  FAILED"
  "$V/bin/python" "$R/backend/analyze_cli.py" --self-test
  echo "Resolve bridge:"
  "$V/bin/python" "$R/runtime/resolve_bridge.py" --ping
else
  echo "Plugin venv: not installed yet"
fi

echo
echo "Analysis log: $HOME/Library/Logs/MusicStructureAI_CPP/analyze.log"
if [[ -f "$HOME/Library/Logs/MusicStructureAI_CPP/analyze.log" ]]; then
  echo "--- analyze.log last 40 lines ---"
  tail -40 "$HOME/Library/Logs/MusicStructureAI_CPP/analyze.log"
fi

echo
if [[ "$MISSING" -ne 0 ]]; then echo "检测到模型权重缺失：重新运行 v0.3.6 install.command。"; fi
echo "若 SDK 或 Cocoa header 缺失："
echo "1) xcode-select --install"
echo "2) 若已安装 /Applications/Xcode.app：sudo xcode-select -s /Applications/Xcode.app/Contents/Developer"
echo "3) 再重新运行 install.command"
read -r -p "按回车关闭..." _||true
