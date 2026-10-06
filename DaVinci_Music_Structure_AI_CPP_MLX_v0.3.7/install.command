#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"; RUNTIME="$HOME/Library/Application Support/MusicStructureAI_CPP"; VENV="$RUNTIME/.venv"; APP="$HOME/Applications/Music Structure AI.app"; SCRIPTS="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/MusicStructureAI CPP"; OLD="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/MusicStructureAI"; LOGDIR="$HOME/Library/Logs/MusicStructureAI_CPP"; LOG="$LOGDIR/install.log"
mkdir -p "$RUNTIME" "$LOGDIR" "$HOME/Applications"; exec > >(tee -a "$LOG") 2>&1
pause(){ echo; read -r -p "按回车关闭窗口..." _ || true; }; fail(){ echo "错误：$*"; pause; exit 1; }
[[ "$(uname -s)" == "Darwin" ]] || fail "仅支持 macOS。"; [[ "$(uname -m)" == "arm64" ]] || fail "v0.3 仅支持 Apple Silicon。"; OSMAJOR="$(sw_vers -productVersion|cut -d. -f1)"; [[ "$OSMAJOR" -ge 14 ]] || fail "all-in-one-mlx 要求 macOS 14 或更高。"
echo "=== Music Structure AI v0.3.7 · C++ + MLX ==="; echo "macOS $(sw_vers -productVersion) / $(uname -m)"
find_python(){ for p in "$(command -v python3.12 2>/dev/null||true)" "$(command -v python3 2>/dev/null||true)" /opt/homebrew/bin/python3.12 /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12; do [[ -x "$p" ]]||continue; if "$p" -c 'import platform,sys;raise SystemExit(0 if sys.version_info[:2]==(3,12) and platform.machine()=="arm64" else 1)' >/dev/null 2>&1; then echo "$p"; return 0; fi; done; return 1; }
PYTHON="$(find_python||true)"; [[ -n "$PYTHON" ]] || fail "没有找到 arm64 Python 3.12。你已有 Python 3.12.3 时，请确认 python3.12 --version 可运行。"; PYTHON_VERSION="$("$PYTHON" --version 2>&1)"; echo "Python: $PYTHON ($PYTHON_VERSION)"
if ! command -v ffmpeg >/dev/null 2>&1 && [[ ! -x /opt/homebrew/bin/ffmpeg ]]; then if command -v brew >/dev/null 2>&1; then echo "安装 FFmpeg..."; brew install ffmpeg; else fail "未找到 FFmpeg，也未找到 Homebrew。请先安装 FFmpeg。"; fi; fi
FFMPEG="$(command -v ffmpeg 2>/dev/null||true)"; [[ -n "$FFMPEG" ]] || FFMPEG=/opt/homebrew/bin/ffmpeg
SDK_PATH="$(xcrun --sdk macosx --show-sdk-path 2>/dev/null || true)"
[[ -n "$SDK_PATH" && -d "$SDK_PATH" ]] || fail "没有找到 macOS SDK。请先运行：xcode-select --install；若已安装完整 Xcode，请运行：sudo xcode-select -s /Applications/Xcode.app/Contents/Developer"
COCOA_HEADER="$SDK_PATH/System/Library/Frameworks/Cocoa.framework/Headers/Cocoa.h"
[[ -f "$COCOA_HEADER" ]] || fail "当前开发者目录里的 macOS SDK 不完整，缺少 Cocoa.h：$COCOA_HEADER。请重新安装 Command Line Tools，或用 xcode-select 切换到完整 Xcode。"
CLANG="$(xcrun --sdk macosx --find clang++ 2>/dev/null||true)"; [[ -x "$CLANG" ]] || fail "需要 Apple Command Line Tools。请先运行：xcode-select --install"
echo "Developer: $(xcode-select -p 2>/dev/null || echo '?')"
echo "macOS SDK: $SDK_PATH"
echo "Apple clang++: $CLANG"
if [[ -d "$OLD" ]]; then BACKUP="$RUNTIME/backup-v0.2-$(date +%Y%m%d-%H%M%S)"; echo "备份旧 v0.2：$BACKUP"; mv "$OLD" "$BACKUP"; fi
rm -rf "$RUNTIME/runtime" "$RUNTIME/backend" "$SCRIPTS"; mkdir -p "$RUNTIME/runtime" "$RUNTIME/backend" "$SCRIPTS"; cp -R "$ROOT/runtime/." "$RUNTIME/runtime/"; cp -R "$ROOT/backend/." "$RUNTIME/backend/"; cp -R "$ROOT/resolve_scripts/." "$SCRIPTS/"
if [[ ! -x "$VENV/bin/python" ]]; then rm -rf "$VENV"; "$PYTHON" -m venv "$VENV"; fi
"$VENV/bin/python" -m pip install --upgrade pip wheel setuptools; echo "安装/升级 all-in-one-mlx + HTDemucs 转换依赖..."; "$VENV/bin/python" -m pip install --upgrade 'all-in-one-mlx==1.0.5' 'demucs-mlx[convert]>=1.4.4,<1.5'
WEIGHTS_DIR="$RUNTIME/mlx-weights"
mkdir -p "$WEIGHTS_DIR"
echo "检查 MLX Harmonix 模型权重..."
BASE_URL="https://raw.githubusercontent.com/ssmall256/all-in-one-mlx/v1.0.5/mlx-weights"
for fold in 0 1 2 3 4 5 6 7; do
  for ext in npz yaml; do
    FILE="harmonix-fold${fold}_mlx.${ext}"
    DEST="$WEIGHTS_DIR/$FILE"
    NEED=0
    if [[ ! -f "$DEST" ]]; then NEED=1;
    elif [[ "$ext" == "npz" && $(stat -f%z "$DEST" 2>/dev/null || echo 0) -lt 1024 ]]; then NEED=1;
    elif [[ "$ext" == "yaml" && $(stat -f%z "$DEST" 2>/dev/null || echo 0) -lt 20 ]]; then NEED=1; fi
    if [[ "$NEED" -eq 1 ]]; then
      echo "下载 $FILE ..."
      TMP="$DEST.part"
      rm -f "$TMP"
      /usr/bin/curl -L --fail --retry 3 --connect-timeout 15 --progress-bar "$BASE_URL/$FILE" -o "$TMP" || fail "下载 MLX 权重失败：$FILE"
      mv "$TMP" "$DEST"
    fi
  done
done
for fold in 0 1 2 3 4 5 6 7; do
  NPZ="$WEIGHTS_DIR/harmonix-fold${fold}_mlx.npz"; YAML="$WEIGHTS_DIR/harmonix-fold${fold}_mlx.yaml"
  [[ -f "$NPZ" && $(stat -f%z "$NPZ") -ge 1024 ]] || fail "MLX 权重异常：$NPZ"
  [[ -f "$YAML" && $(stat -f%z "$YAML") -ge 20 ]] || fail "MLX 配置异常：$YAML"
done
"$VENV/bin/python" - <<PYWEIGHTS
from pathlib import Path
import zipfile
wd=Path(r"$WEIGHTS_DIR")
for fold in range(8):
    npz=wd/f"harmonix-fold{fold}_mlx.npz"
    yml=wd/f"harmonix-fold{fold}_mlx.yaml"
    if not zipfile.is_zipfile(npz):
        raise SystemExit(f"invalid npz: {npz}")
    if yml.stat().st_size < 20:
        raise SystemExit(f"invalid yaml: {yml}")
print("MLX_WEIGHT_VALIDATION_OK")
PYWEIGHTS
echo "MLX 权重：OK ($WEIGHTS_DIR)"

echo "验证 HTDemucs 首次转换依赖..."
"$VENV/bin/python" - <<'PYDEMUX'
import importlib.util
missing = [name for name in ("torch", "demucs", "demucs_mlx") if importlib.util.find_spec(name) is None]
if missing:
    raise SystemExit("缺少 HTDemucs 转换依赖: " + ", ".join(missing))
print("DEMUCS_CONVERT_DEPS_OK")
PYDEMUX

echo "准备 HTDemucs 原始 checkpoint（完整 SHA-256 校验）..."
CKPT_DIR="$HOME/.cache/torch/hub/checkpoints"
CKPT="$CKPT_DIR/955717e8-8726e21a.th"
EXPECTED_DEMUCS_SHA="8726e21a993978c7ba086d3872e7608d7d5bfca646ca4aca459ffda844faa8b4"
mkdir -p "$CKPT_DIR"
sha256_file(){ /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'; }
if [[ -f "$CKPT" ]]; then
  ACTUAL_SHA="$(sha256_file "$CKPT")"
  if [[ "$ACTUAL_SHA" != "$EXPECTED_DEMUCS_SHA" ]]; then
    BAD="$CKPT.bad-$(date +%Y%m%d-%H%M%S)"
    echo "发现损坏/错误 checkpoint ($ACTUAL_SHA)，移动到：$BAD"
    mv "$CKPT" "$BAD"
  else
    echo "HTDemucs checkpoint：SHA-256 OK"
  fi
fi
if [[ ! -f "$CKPT" ]]; then
  TMP="$CKPT.part"; rm -f "$TMP"; OK=0
  DEMUCS_URLS=(
    "https://huggingface.co/iBoostAI/Demucs-v4/resolve/main/955717e8-8726e21a.th?download=true"
    "https://huggingface.co/lainlives/audio-separator-models/resolve/main/955717e8-8726e21a.th?download=true"
  )
  for URL in "${DEMUCS_URLS[@]}"; do
    echo "下载 HTDemucs：$URL"
    rm -f "$TMP"
    if /usr/bin/curl -L --fail --retry 3 --retry-delay 2 --connect-timeout 20 --progress-bar "$URL" -o "$TMP"; then
      ACTUAL_SHA="$(sha256_file "$TMP")"
      echo "下载 SHA-256：$ACTUAL_SHA"
      if [[ "$ACTUAL_SHA" == "$EXPECTED_DEMUCS_SHA" ]]; then mv "$TMP" "$CKPT"; OK=1; break; fi
      echo "哈希不匹配，拒绝该下载。"
    fi
  done
  rm -f "$TMP"
  [[ "$OK" -eq 1 ]] || fail "无法下载通过 SHA-256 校验的 HTDemucs checkpoint。可运行 repair-demucs.command 重试。"
fi

echo "转换/预热 HTDemucs MLX 安全缓存..."
mkdir -p "$HOME/.cache/demucs-mlx"
if ! "$VENV/bin/python" -m demucs_mlx.mlx_convert htdemucs --output-dir "$HOME/.cache/demucs-mlx"; then
  fail "HTDemucs → MLX 转换失败。请运行 repair-demucs.command 查看详细日志。"
fi
if ! "$VENV/bin/python" - <<'PYDEMUXBOOT'
from demucs_mlx import Separator
Separator(model="htdemucs", progress=False)
print("HTDEMUCS_MLX_READY")
PYDEMUXBOOT
then
  fail "HTDemucs MLX 模型初始化失败。请运行 repair-demucs.command 或 diagnose.command 查看详细信息。"
fi
rm -rf "$APP"; mkdir -p "$APP/Contents/MacOS"; cp "$ROOT/controller/Info.plist" "$APP/Contents/Info.plist"; echo "验证 Cocoa / macOS SDK..."
printf '#import <Cocoa/Cocoa.h>\nint main(){return 0;}\n' | xcrun --sdk macosx clang++ -x objective-c++ -fblocks -fsyntax-only -isysroot "$SDK_PATH" - >/dev/null || fail "macOS SDK/Cocoa 预检失败。请运行 diagnose.command 查看开发工具路径。"
echo "编译 C++ 原生控制器..."
COMPILE_LOG="$LOGDIR/controller-build.log"
if ! xcrun --sdk macosx clang++ -std=c++17 -O2 -fobjc-arc -fblocks -isysroot "$SDK_PATH" -mmacosx-version-min=14.0 -framework Cocoa -framework Foundation "$ROOT/controller/main.mm" -o "$APP/Contents/MacOS/MusicStructureAI" 2> >(tee "$COMPILE_LOG" >&2); then
  fail "C++ 原生控制器编译失败。完整日志：$COMPILE_LOG"
fi
chmod +x "$APP/Contents/MacOS/MusicStructureAI"
PYVER="$("$VENV/bin/python" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
cat > "$RUNTIME/config.json" <<JSON
{"version":"0.3.7","architecture":"C++17/Objective-C++ controller + Python MLX backend + Resolve Python bridge","python_executable":"$VENV/bin/python","python_version":"$PYVER","backend_analyzer":"$RUNTIME/backend/analyze_cli.py","mlx_weights_dir":"$WEIGHTS_DIR","bridge":"$RUNTIME/runtime/resolve_bridge.py","ffmpeg":"$FFMPEG","app":"$APP"}
JSON
chmod +x "$RUNTIME/backend/analyze_cli.py" "$RUNTIME/runtime/resolve_bridge.py"; "$APP/Contents/MacOS/MusicStructureAI" --self-test; "$VENV/bin/python" "$RUNTIME/backend/analyze_cli.py" --self-test
set +e; "$VENV/bin/python" "$RUNTIME/runtime/resolve_bridge.py" --ping; BRIDGE_RC=$?; set -e
if [[ "$BRIDGE_RC" -ne 0 ]]; then echo "提示：自动写回通道当前不可用。Resolve 中将 External Scripting Using 设为 Local；或者分析后运行 Apply Last Analysis。"; fi
echo "安装完成。完全退出并重开 Resolve。入口：Workspace → Scripts → Utility → MusicStructureAI CPP → Music Structure AI"; pause
