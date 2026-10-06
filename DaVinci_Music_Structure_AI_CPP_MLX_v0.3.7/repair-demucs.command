#!/bin/bash
set -euo pipefail
R="$HOME/Library/Application Support/MusicStructureAI_CPP"
V="$R/.venv"
LOGDIR="$HOME/Library/Logs/MusicStructureAI_CPP"
LOG="$LOGDIR/repair-demucs.log"
CKPT_DIR="$HOME/.cache/torch/hub/checkpoints"
CKPT="$CKPT_DIR/955717e8-8726e21a.th"
EXPECTED_SHA="8726e21a993978c7ba086d3872e7608d7d5bfca646ca4aca459ffda844faa8b4"
mkdir -p "$LOGDIR" "$CKPT_DIR"
exec > >(tee -a "$LOG") 2>&1
pause(){ echo; read -r -p "按回车关闭窗口..." _ || true; }
fail(){ echo "错误：$*"; pause; exit 1; }
sha256_file(){ /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'; }
[[ -x "$V/bin/python" ]] || fail "没有找到插件虚拟环境：$V。请先运行 install.command。"

echo "=== Music Structure AI · Repair HTDemucs v0.3.6 ==="
echo "安装/确认 demucs-mlx 转换依赖..."
"$V/bin/python" -m pip install --upgrade 'demucs-mlx[convert]>=1.4.4,<1.5'
"$V/bin/python" -c 'import importlib.util; missing=[n for n in ("torch","demucs","demucs_mlx") if importlib.util.find_spec(n) is None]; assert not missing, "Missing: "+", ".join(missing); print("DEMUCS_CONVERT_DEPS_OK")'

echo "检查原始 HTDemucs checkpoint..."
if [[ -f "$CKPT" ]]; then
  ACTUAL="$(sha256_file "$CKPT")"
  if [[ "$ACTUAL" == "$EXPECTED_SHA" ]]; then
    echo "HTDemucs checkpoint：SHA-256 OK"
  else
    BAD="$CKPT.bad-$(date +%Y%m%d-%H%M%S)"
    echo "发现错误 checkpoint：$ACTUAL"
    echo "移动到：$BAD"
    mv "$CKPT" "$BAD"
  fi
fi

if [[ ! -f "$CKPT" ]]; then
  echo "Meta 原下载源当前返回内容与模型签名不一致；改用镜像并做完整 SHA-256 校验。"
  TMP="$CKPT.part"
  rm -f "$TMP"
  URLS=(
    "https://huggingface.co/iBoostAI/Demucs-v4/resolve/main/955717e8-8726e21a.th?download=true"
    "https://huggingface.co/lainlives/audio-separator-models/resolve/main/955717e8-8726e21a.th?download=true"
  )
  OK=0
  for URL in "${URLS[@]}"; do
    echo "下载：$URL"
    rm -f "$TMP"
    if /usr/bin/curl -L --fail --retry 3 --retry-delay 2 --connect-timeout 20 --progress-bar "$URL" -o "$TMP"; then
      ACTUAL="$(sha256_file "$TMP")"
      echo "下载 SHA-256：$ACTUAL"
      if [[ "$ACTUAL" == "$EXPECTED_SHA" ]]; then
        mv "$TMP" "$CKPT"
        OK=1
        break
      fi
      echo "镜像文件哈希不匹配，拒绝使用。"
    fi
  done
  rm -f "$TMP"
  [[ "$OK" -eq 1 ]] || fail "无法取得通过 SHA-256 校验的 HTDemucs checkpoint。"
fi

echo "将 HTDemucs 转换为 demucs-mlx 安全缓存..."
mkdir -p "$HOME/.cache/demucs-mlx"
"$V/bin/python" -m demucs_mlx.mlx_convert htdemucs --output-dir "$HOME/.cache/demucs-mlx"

echo "验证 MLX 模型可直接加载..."
"$V/bin/python" -c 'from demucs_mlx import Separator; Separator(model="htdemucs", progress=False); print("HTDEMUCS_MLX_READY")'

echo "修复完成。之后推理直接读取本地 MLX 缓存，不需要再次转换。"
echo "checkpoint：$CKPT"
echo "MLX cache：$HOME/.cache/demucs-mlx"
echo "日志：$LOG"
pause
