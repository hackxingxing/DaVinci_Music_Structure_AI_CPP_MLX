#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
RUNTIME="$HOME/Library/Application Support/MusicStructureAI_CPP"
TARGET="$RUNTIME/runtime"
pause(){ echo; read -r -p "按回车关闭窗口..." _ || true; }
fail(){ echo "错误：$*"; pause; exit 1; }
[[ -d "$RUNTIME" ]] || fail "没有找到已安装的 Music Structure AI：$RUNTIME"
mkdir -p "$TARGET"
cp "$ROOT/runtime/core.py" "$TARGET/core.py"
rm -rf "$TARGET/__pycache__" 2>/dev/null || true
printf '\n中文段落标记已更新。\n'
printf '颜色图例：前奏=蓝色，主歌=绿色，副歌=红色，桥段=紫色，尾奏=黄色，间奏=粉色，器乐/独奏=青色。\n'
printf '\n回到 Resolve 后运行：\nWorkspace → Scripts → Utility → MusicStructureAI CPP → Apply Last Analysis\n'
printf '即可用同一份分析结果重新写入中文段落标记，不需要重新分析音乐。\n'
pause
