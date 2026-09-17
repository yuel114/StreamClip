# 第三方代码与授权

项目源码按 GPL-3.0 分发，全文见根目录 [LICENSE](LICENSE)。此声明不代表已取得第三方角色、立绘或参考图的授权。

## 皮肤与生成素材

本仓库保留两套皮肤及其图片。发布者尚未取得相关角色和参考图衍生素材的公开再分发授权；这些图片不包含在项目对自有源码作出的 GPL 授权声明中。详细范围、生成来源及未解决事项见 [assets/ui/ASSET_RIGHTS.md](assets/ui/ASSET_RIGHTS.md)。来源记录和 AI 生成记录不是权利人许可，不应据此推断已获商用或再分发授权。

## Lucide 图标

- 导航与操作图标使用 Lucide 的原始 SVG，存放于 `assets/ui/icons`，不包含新的运行时依赖。
- 固定来源：`https://github.com/lucide-icons/lucide/tree/076b52527f0c5fe4cc1cd2472ef716fc332ccf0e/icons`。
- ISC 许可证及部分源自 Feather 的图标所需的 MIT 声明均完整保留于 `licenses/lucide-LICENSE`，随 EXE 打包。图标只在 Qt 中按控件状态着色，源文件未修改。

## Qt / PySide6 与 Qt Multimedia

- 界面使用 PySide6 / Qt 6.11.2，来源：[Qt for Python](https://www.qt.io/qt-for-python)、[PySide 源码](https://code.qt.io/cgit/pyside/pyside-setup.git/)、[Qt 源码](https://code.qt.io/cgit/qt/)。本项目未修改 Qt/PySide6 库。
- 随包保留 LGPLv3 许可证全文 `licenses/qt-LGPL-3.0.txt`；Qt 组件的具体许可证以各组件上游声明为准。项目自身的 GPLv3 声明见下文。
- 内嵌播放器使用 Qt Multimedia 随带的 FFmpeg 7.1.5。运行库声明 LGPL 2.1 或更高版本；全文为 `licenses/ffmpeg-LGPL-2.1.txt`，对应源码见 [FFmpeg n7.1.5](https://github.com/FFmpeg/FFmpeg/tree/n7.1.5)。外部媒体处理仍使用用户已配置或 tools 目录中的 FFmpeg 程序。

## Hikami-Go

- 项目：[lililixxx1/hikami-go](https://github.com/lililixxx1/hikami-go)
- 固定来源提交：[`17e30777bc34fc12652df107c84502a9f85d0679`](https://github.com/lililixxx1/hikami-go/tree/17e30777bc34fc12652df107c84502a9f85d0679)
- 作者及版权归属：Hikami-Go 贡献者，以来源仓库的版权声明和提交记录为准。
- 许可证：GNU General Public License，Version 3。未经修改的全文位于 [licenses/hikami-go-LICENSE](licenses/hikami-go-LICENSE)。
- 改编日期：2026-09-08。

`hikami_glossary.py`、`app.py` 中对应的术语和工具调用集成，以及 `self_test.py` 中对应检查，基于以下上游实现改编：

- `internal/glossary/glossary.go`、`discovery.go`、`candidate_store.go`、`review.go`：词表覆盖、自由备注、导入导出、热词、发现提示词、候选合并与评分、AI 复核和人工批准。
- `internal/recap/glossary_correction.go`、`transcript_correction.go`、`provider_util.go`、`prompt.go`、`handler.go`：词表修正版转写、回顾规范写法、引用保护、建议写法提取与清理。
- `internal/asr/dashscope.go`、`internal/mcp/builtin.go`、`loop.go`：Fun-ASR 热词请求、Brave/Tavily 查询、工具调用循环及预算。
- `web/src/components/channel/GlossaryEditor.vue`、`web/src/features/channel/useGlossaryEntries.ts`、`web/src/features/settings/components-v10/GlossaryCardV10.vue`：全局/主播词表和候选审核的操作流程。

本地改编使用 Python 标准库、现有 SQLite 连接、AI 客户端和 Tk/ttkbootstrap 窗口替代 Go/Vue 服务，不依赖上游程序运行。分块上限、候选评分权重、热词权重、审核状态和引用保留规则沿用上游；补充本地旧资料迁移、输入验证、后台结果状态保护、原子文件写入及密钥重定向保护。导入时保留词条启用状态，避免将停用项重新启用。每条录播的侧车文件使用本软件现有的同名文件约定。

本次移植范围是术语识别、回顾参考和候选审核流程，包括内置 Brave/Tavily 联网查词。上游的独立 Go 服务、外部 MCP 服务器管理、专栏/Opus 发布和针对少数游戏的可选百科摘要没有作为本软件功能引入。

派生代码遵循 GPLv3。本源码目录包含这些改编的可读源代码与构建脚本；EXE 同时携带此声明和许可证。分发包含这些派生代码的版本时，应按 GPLv3 提供相应源代码、保留声明并遵守许可证条件。软件按许可证约定提供，不附带担保。
