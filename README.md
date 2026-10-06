# DaVinci Music Structure AI 使用说明
版本：v0.3.7  
适用平台：macOS / Apple Silicon  
适用软件：DaVinci Resolve  
后端：C++ 原生控制器 + Python 3.12 + MLX / Metal

---

## 1. 插件用途

DaVinci Music Structure AI 用于分析时间线中的音乐，并自动识别：

- 前奏
- 主歌
- 副歌
- 桥段
- 尾奏
- 间奏
- 器乐段
- 独奏段
- BPM
- Beat（节拍）
- Downbeat（每小节第一拍）

分析完成后，会把结果直接写入 DaVinci Resolve 时间线，方便进行：

- 卡点剪辑
- 变装视频
- 转场设计
- 音乐结构剪辑
- 副歌高潮定位
- 小节切镜
- 节奏密度控制

---

## 2. 插件入口

打开 DaVinci Resolve 后：

`Workspace → Scripts → Utility → MusicStructureAI CPP → Music Structure AI`

如果需要重新写入上一次分析结果：

`Workspace → Scripts → Utility → MusicStructureAI CPP → Apply Last Analysis`

---

## 3. 使用方法

### 第一步：把音乐放入时间线

将需要分析的音乐放到 DaVinci Resolve 时间线。

支持常见音频格式，例如：

- WAV
- MP3
- FLAC
- AAC
- 视频文件中的音频

插件会在需要时通过 FFmpeg 转换为分析用 WAV。

---

### 第二步：把播放头放到音乐 Clip 上

将时间线播放头移动到需要分析的音乐片段内部。

插件当前不是读取“鼠标选中的音频”，而是寻找：

> 播放头当前位置下面的音频 Clip

如果同一位置存在多条音轨，插件会显示候选列表，可手动选择需要分析的音乐。

---

### 第三步：打开插件

进入：

`Workspace → Scripts → Utility → MusicStructureAI CPP → Music Structure AI`

选择目标音乐。

---

### 第四步：选择分析内容

默认建议全部开启：

- [x] 音乐段落
- [x] Downbeat
- [x] Beat

如果不希望时间线上出现大量节拍点，可以关闭 Beat，只保留：

- 音乐段落
- Downbeat

这种方式通常更适合常规剪辑。

---

### 第五步：点击“分析”

插件会依次执行：

`音频读取 → FFmpeg → HTDemucs MLX → Harmonix 模型 → 音乐结构分析 → 写入 Resolve Marker`

第一次运行模型时可能会稍慢。

后续模型和分析结果会使用本地缓存。

---

## 4. 如何区分时间线上的标记

插件目前主要分成三层：

### 4.1 音乐段落

位于时间线顶部。

段落会使用中文名称，例如：

- 01 前奏
- 02 主歌 1
- 03 副歌 1
- 04 主歌 2
- 05 副歌 2
- 06 桥段
- 07 副歌 3
- 08 尾奏

建议把时间线稍微放大后查看段落名称。

---

### 4.2 Downbeat

Downbeat 表示：

> 每个小节的第一拍

它比普通 Beat 更适合做：

- 变装点
- 大动作点
- 场景切换
- 镜头切换
- 转场
- 节奏结构设计

如果歌曲是常见 4/4 拍，可理解为：

`1 2 3 4 | 1 2 3 4 | 1 2 3 4`

其中每个“1”就是 Downbeat。

---

### 4.3 Beat

Beat 是普通节拍。

数量会比较密集。

适合：

- 高频卡点
- 快节奏蒙太奇
- 动作同步
- 音效同步
- 微小节奏调整

如果时间线太乱，可以在分析前关闭 Beat。

---

## 5. 中文段落颜色

当前推荐的视觉理解方式：

| 段落 | 中文 | 主要用途 |
|---|---|---|
| Intro | 前奏 | 建立氛围、人物出场 |
| Verse | 主歌 | 叙事、铺垫 |
| Chorus | 副歌 | 高潮、变装、强转场 |
| Bridge | 桥段 | 情绪转换、视觉变化 |
| Outro | 尾奏 | 收尾 |
| Break | 间奏 | 节奏转换 |
| Instrumental | 器乐段 | 无歌词段落 |
| Solo | 独奏段 | 乐器突出段落 |

实际颜色以当前插件写入 Resolve 的 Marker 颜色为准。

---

## 6. 推荐剪辑方法

### 普通变装视频

重点关注：

`主歌 → 副歌`

通常可以：

- 主歌：人物铺垫
- 副歌第一拍：完成变装
- 副歌内部 Downbeat：切换造型、景别或机位

---

### 高级转场视频

推荐观察：

`前奏 → 主歌 → 副歌 → 桥段 → 最终副歌`

可以把不同音乐段落对应不同视觉阶段。

例如：

- 前奏：人物静态
- 主歌：动作建立
- 副歌：第一次变装
- 桥段：情绪或场景变化
- 最终副歌：最终造型高潮

---

### 快节奏卡点视频

建议同时开启：

- Downbeat
- Beat

其中：

- Downbeat 决定大剪辑点
- Beat 决定小动作点

---

## 7. 自动写回 Marker

为了让插件分析结束后自动写入 Resolve：

进入：

`DaVinci Resolve → Preferences → System → General`

找到：

`External Scripting Using`

设置为：

`Local`

然后完全退出并重新打开 Resolve。

---

## 8. 如果分析完成但没有写入时间线

运行：

`Workspace → Scripts → Utility → MusicStructureAI CPP → Apply Last Analysis`

插件会读取最后一次分析结果并重新写入 Marker。

不需要重新分析音乐。

---

## 9. 清除插件 Marker

可通过插件中的“清除标记”功能，或者对应的 Utility 脚本清除 Music Structure AI 创建的 Marker。

建议只使用插件自身的清理功能，以免误删自己手工添加的 Marker。

---

## 10. 缓存

插件会缓存：

- MLX 模型
- HTDemucs 模型
- 音乐分析结果
- 最近一次分析结果

因此同一音乐再次分析通常会更快。

---

## 11. 插件主要文件位置

### 主运行目录

不要删除：

`~/Library/Application Support/MusicStructureAI_CPP/`

这里包含：

- Python 虚拟环境
- MLX 后端
- Runtime
- 配置文件
- 模型相关文件

删除后插件会无法正常运行。

---

### 日志目录

`~/Library/Logs/MusicStructureAI_CPP/`

常用日志：

`analyze.log`

如果插件分析失败，优先查看这个文件。

---

### Demucs MLX 缓存

通常位于：

`~/.cache/demucs-mlx/`

---

## 12. 下载目录可以删除吗

可以。

例如安装完成后的：

`DaVinci_Music_Structure_AI_CPP_MLX_v0.3.7/`

以及：

`DaVinci_Music_Structure_AI_CPP_MLX_v0.3.7.zip`

都只是安装源文件。

确认插件已经可以正常：

- 打开
- 分析音乐
- 识别中文段落
- 写入 Marker

之后就可以删除。

但不要删除：

`~/Library/Application Support/MusicStructureAI_CPP/`

---

## 13. 常见问题

### 插件菜单里找不到

完全退出 DaVinci Resolve 后重新打开。

检查：

`Workspace → Scripts → Utility`

---

### 插件找不到音乐

确认播放头位于目标音频 Clip 内部。

---

### 同一位置有多条音频

在插件窗口中选择正确的音乐轨道。

---

### 分析失败

查看：

`~/Library/Logs/MusicStructureAI_CPP/analyze.log`

优先查看最后几行 Traceback。

---

### 自动写回失败

检查：

`Preferences → System → General → External Scripting Using → Local`

然后重启 Resolve。

或者直接运行：

`Apply Last Analysis`

---

### 时间线上 Beat 太多

重新分析前关闭：

`Beat`

只保留：

- 音乐段落
- Downbeat

通常会更加清晰。

---

## 14. 推荐默认设置

普通剪辑：

- [x] 音乐段落
- [x] Downbeat
- [ ] Beat

卡点 / 变装 / 快剪：

- [x] 音乐段落
- [x] Downbeat
- [x] Beat

---

## 15. 当前版本架构

`DaVinci Resolve`
↓
`C++ 原生控制器`
↓
`Python 3.12`
↓
`all-in-one-mlx`
↓
`MLX / Metal GPU`
↓
`HTDemucs + Harmonix`
↓
`音乐结构 / BPM / Beat / Downbeat`
↓
`Resolve Marker`

---

## 16. 当前版本

版本：

`DaVinci Music Structure AI v0.3.7`

当前重点功能：

- Apple Silicon 原生
- C++ 控制器
- MLX / Metal 加速
- 中文音乐段落
- 主歌 / 副歌 / 前奏 / 桥段 / 尾奏识别
- Beat
- Downbeat
- Resolve Marker 自动写入
- 分析缓存
- 日志诊断

---

建议以后每次插件升级，都在此文档底部记录版本号和主要变化，方便长期维护。
