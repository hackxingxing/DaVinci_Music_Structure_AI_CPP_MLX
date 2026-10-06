#!/bin/bash
set -euo pipefail
C="$HOME/Library/Caches/MusicStructureAI_CPP"; echo "将删除：$C"; read -r -p "输入 YES：" x; [[ "$x" == "YES" ]]&&rm -rf "$C"&&echo "已清除"||echo "已取消"; read -r -p "按回车关闭..." _||true
