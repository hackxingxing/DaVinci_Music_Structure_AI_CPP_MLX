#!/bin/bash
set -euo pipefail
rm -rf "$HOME/Applications/Music Structure AI.app" "$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/MusicStructureAI CPP" "$HOME/Library/Application Support/MusicStructureAI_CPP"
echo "已卸载。"; read -r -p "同时删除缓存？输入 YES：" x||true; [[ "$x" == "YES" ]]&&rm -rf "$HOME/Library/Caches/MusicStructureAI_CPP"||true; read -r -p "按回车关闭..." _||true
