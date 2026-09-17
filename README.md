# StreamClip

Windows 桌面端 Bilibili 直播切片工作台，使用 Python、PySide6 / Qt Quick 和 FFmpeg。

> 源码使用 GPLv3；角色皮肤的公开再分发授权尚未取得，不包含在代码授权声明中。详细来源及权利状态见 [素材权利说明](assets/ui/ASSET_RIGHTS.md)。

## 功能

- 监控直播间、自动录播、采集实时弹幕，下载历史回放或导入本地媒体。
- 通过阿里云 DashScope 转写语音，通过 OpenAI 兼容接口生成回顾、选题、标题和封面文案。
- 管理全局和主播术语表、主播知识库及待审核词条。
- 使用 FFmpeg 制作字幕、封面和视频切片，在软件内预览成片。
- 通过 Bilibili 扫码登录，按队列投稿并查询平台处理状态。
- 两套皮肤、八个工作页面、任务重试、未保存表单保护和运行日志。

## 皮肤角色

- 「羽啾 · 薄荷」：[羽啾chu2u](https://space.bilibili.com/2138961136)
- 「冰蓝 · 蝶影」：[雨纪_Ameki](https://space.bilibili.com/1932862336)

**拜托给个关注吧~** 工作台皮肤区域提供对应的个人主页按钮，切换皮肤后链接同步切换。

## 运行要求

- Windows 10/11，64 位 Python 3.11。
- 完整版 FFmpeg 和 FFprobe，需要支持 H.264/AAC、字幕、绘字以及 MP4 输出。
- 下载 Bilibili 回放需要 yt-dlp。
- 语音识别和 AI 分析需要用户自己的服务账号、API Key、模型权限及额度。
- 默认封面字体依赖 Windows 的等线粗体和微软雅黑粗体；也可在设置中导入有使用授权的字体。本仓库不分发字体文件。

FFmpeg、FFprobe、yt-dlp 的可执行文件不放入 Git 仓库。可以从各自上游获取，放到 `tools/ffmpeg.exe`、`tools/ffprobe.exe`、`tools/yt-dlp.exe`，或在「设置 → 高级设置 → 媒体工具」填写路径。

## 源码启动

在项目目录打开 PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

默认启动完整 Qt Quick 界面。`启动Qt试运行.cmd` 与 `--qml` 是兼容入口；无需运行任何独立服务器。

首次使用：

1. 在「设置」的「语音与 AI」分组填写阿里云 ASR Key、AI API 地址和 Key，获取并选择模型。OpenAI 兼容地址填写到 `/v1`。
2. 在「账号」添加账号，用 Bilibili App 扫码并确认登录。
3. 在「直播间」添加房间号并启用监控，或从工作台导入本地媒体。
4. 在「基础与自动化」确认保存目录、自动处理和投稿可见性后再开始。

术语管理入口位于「高级设置」顶部。联网查词可选，默认关闭；需要时自行配置 Brave 或 Tavily。

**自动处理默认开启，投稿默认私密。** AI 画面复核不通过的切片会强制私密投稿并保留复核提醒。请自行核对账号、素材使用许可、标题和可见性，不要将自动检查当作人工审片或平台审核通过的保证。

## 数据与隐私

运行数据默认在程序旁的 `data/`，包括配置、数据库、登录凭据和日志；录播与切片可设置独立目录。不要同时启动多个实例处理同一数据目录。

账号凭据、API Key、数据库、录播、字幕和日志不应提交到 Git，也不要放进 Issue。账号凭据的本地加密不等于公开备份是安全的。更换机器或程序目录后可能需要重新登录。

转写会将音频上传到配置的 ASR 服务；AI 分析可能向配置的模型服务发送转写、弹幕、主播知识库、标题及画面抽帧。只处理有权使用并可发送至相应服务的内容，费用由所用服务收取。

## 测试

测试使用隔离数据，不执行真实录制、收费 ASR / AI 调用或平台投稿。界面检查需要 Windows 桌面会话和可用的图形驱动。

```powershell
$env:TEMP = 'E:\CodexBuildCache\StreamClip\tests'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force $env:TEMP | Out-Null
$env:LIVECLIP_UI_TEST_OUTPUT = 'E:\CodexBuildCache\StreamClip\ui-check'
$env:LIVECLIP_TEST_FFMPEG = (Resolve-Path .\tools\ffmpeg.exe).Path
.\.venv\Scripts\python.exe -X utf8 -B release_check.py
.\.venv\Scripts\python.exe -X utf8 -B self_test.py
.\.venv\Scripts\python.exe -X utf8 -B quick_ui_test.py
```

路径可以替换为自己的隔离测试目录。发布检查扫描 Git 将跟踪的文件并验证许可证及素材清单，不是完整的安全审计或素材授权审查；它不会把未解决的素材权利状态判为已获授权。

## 构建

将虚拟环境的 Python 放到当前 PowerShell 的 PATH 后执行：

```powershell
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"
$env:LIVECLIP_TEST_FFMPEG = (Resolve-Path .\tools\ffmpeg.exe).Path
.\build.ps1 -BuildRoot 'E:\CodexBuildCache\StreamClip\release'
```

`-BuildRoot` 可指定其他有写入权限的构建目录；不要指向源码或数据目录。脚本先构建、验证包内 QML，再运行打包后的业务和界面自检；全部成功且当前程序未运行时，才备份并替换项目根目录的 `StreamClip.exe`。它不会停止正在录制的进程。请勿直接分发未通过检查的 EXE。

源码仓库不包含预编译 EXE。二进制分发还需要核对 Qt、FFmpeg 等随包组件的许可和相应源码要求，并解决上述皮肤素材的授权问题。

## 许可证

项目自有源码与 Hikami-Go 派生代码按 GNU GPL v3 分发，全文见 [LICENSE](LICENSE)。Hikami-Go 的来源提交、移植范围，以及 Qt、FFmpeg、Lucide 的声明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。第三方声明与原许可证均保留。

皮肤图片的权利状态单独见 [ASSET_RIGHTS.md](assets/ui/ASSET_RIGHTS.md)，不能将代码许可证解读为第三方角色授权。本项目不代表 Bilibili、阿里云或任何主播；请遵守平台规则和相关内容权利要求。
