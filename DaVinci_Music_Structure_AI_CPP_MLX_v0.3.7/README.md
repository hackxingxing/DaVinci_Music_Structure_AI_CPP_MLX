# Music Structure AI v0.3.7 — 中文段落可视化版

## v0.3.7 变化

- 段落 Marker 改为**纯中文**，不再显示 `INTRO / VERSE / CHORUS` 英文。
- 段落按时间顺序编号：`01 前奏`、`02 主歌 1`、`03 副歌 1`、`04 主歌 2`……
- 重复的主歌/副歌自动编号，方便剪辑时快速区分。
- 固定颜色图例：**前奏蓝 / 主歌绿 / 副歌红 / 桥段紫 / 尾奏黄 / 间奏粉 / 器乐与独奏青**。
- 已安装 v0.3.6 的用户可直接双击 `update-chinese-labels.command`，无需重装模型。更新后在 Resolve 运行 `Apply Last Analysis` 即可重新写入中文标记。


架构：**Resolve 内部 Python 启动器 → C++17/Objective-C++ 原生控制器 → Python 3.12 + all-in-one-mlx/Metal → Resolve Python Bridge → Marker**。

## 功能
- Intro / Verse / Chorus / Bridge / Outro / Break / Instrumental / Solo。
- BPM、Beat、Downbeat。
- 段落写 Timeline 范围 Marker；节拍写音乐 Clip Marker。
- 播放头下多条音频时由 C++ 原生窗口选择。
- 同一裁切范围使用缓存。
- 外部自动写回失败时保留结果，可在 Resolve 运行 `Apply Last Analysis`。

## 系统要求
- Apple Silicon；macOS 14+。
- Python 3.12（现有 3.12.3 可直接使用）。
- FFmpeg。
- Apple Command Line Tools：`xcode-select --install`。

## v0.3.1 → v0.3.3 修复
- 修复 `Cocoa/Cocoa.h file not found`：编译时不再直接调用 clang++ 绝对路径，而是使用 `xcrun --sdk macosx clang++`。
- 显式传入 `-isysroot "$(xcrun --sdk macosx --show-sdk-path)"`。
- 安装前验证 macOS SDK 与 `Cocoa.h` 是否真实存在。
- `diagnose.command` 增加 Developer Directory、SDK、Cocoa Header、Apple Clang 检查。

## 安装
1. 解压。
2. 双击 `install.command`。
3. 安装器创建独立 Python 3.12 venv、安装 `all-in-one-mlx`，并在本机用 Apple clang++ 编译 `~/Applications/Music Structure AI.app`。
4. 完全退出并重新打开 Resolve。

旧 v0.2 Resolve 脚本会被备份到 `~/Library/Application Support/MusicStructureAI_CPP/backup-v0.2-...`。

## 使用
1. 把播放头放到音乐 Clip 内。
2. `Workspace → Scripts → Utility → MusicStructureAI CPP → Music Structure AI`。
3. 选择音乐，勾选段落 / Downbeat / Beat。
4. 点 **分析并写入 Resolve**。

建议一次性把 Resolve `Preferences → System → General → External Scripting Using` 设为 `Local`，这样 C++ 外部控制器分析结束后可自动写回。

如果自动写回失败，回 Resolve 执行：`Workspace → Scripts → Utility → MusicStructureAI CPP → Apply Last Analysis`。

## 路径
- App：`~/Applications/Music Structure AI.app`
- Runtime：`~/Library/Application Support/MusicStructureAI_CPP/`
- Resolve Scripts：`~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/MusicStructureAI CPP/`
- Cache：`~/Library/Caches/MusicStructureAI_CPP/analysis/`
- Log：`~/Library/Logs/MusicStructureAI_CPP/`

## 说明
C++ 负责 UI、调度和缓存；Python 仅承担 MLX 模型调用与 Resolve 官方 Python API 桥接。真正耗时的模型计算由 MLX/Metal 执行。后续可以继续把推理层迁移到 MLX C++ API。

当前仍采用“播放头位于音乐 Clip 内”来定位音乐，因为 Resolve 公开脚本 API 没有稳定的当前选中 Audio Clip 获取接口。


### Objective-C++ 编译修复

- 修复 Objective-C++ 控制器中 `status` 属性与 `setStatus:` 方法冲突导致的编译错误。
- 修复 `[@"状态：" stringByAppendingString:...]` 消息发送语法。
- 将 `main.mm` 重写为可读的多行代码，减少单行代码导致的编译定位困难。
- 控制器编译失败时保存完整日志到 `~/Library/Logs/MusicStructureAI_CPP/controller-build.log`。


## v0.3.3 修复

- 修复 `install.command` 在 `~/Library/Application Support/...` 路径下执行 Python 时缺少引号导致的 `Permission denied`。
- 所有 Python 可执行文件路径均以完整引用方式调用，兼容包含空格的 macOS 用户目录。


## v0.3.6：HTDemucs 下载哈希修复

若 Meta 的 `dl.fbaipublicfiles.com` 返回内容与 `955717e8-8726e21a.th` 的官方 SHA-256 不一致，插件不会关闭安全校验。`repair-demucs.command` 会：

1. 检查 `~/.cache/torch/hub/checkpoints/955717e8-8726e21a.th`；
2. 只接受 SHA-256 `8726e21a993978c7ba086d3872e7608d7d5bfca646ca4aca459ffda844faa8b4`；
3. 不匹配的文件会改名保存为 `.bad-时间戳`；
4. 从备用镜像重新下载并再次做完整 SHA-256 校验；
5. 执行 `python -m demucs_mlx.mlx_convert htdemucs --output-dir ~/.cache/demucs-mlx`；
6. 最后用 `Separator(model="htdemucs")` 验证安全 MLX cache 可以直接加载。

对于已经装好 v0.3.5 的机器，无需重装全部插件，直接运行 v0.3.6 中的 `repair-demucs.command` 即可。
