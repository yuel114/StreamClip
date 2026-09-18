# 素材权利说明

## 当前版本

旧版第三方角色素材已移除。当前版本采用「极昼」与「黑夜」主题，工作台分别使用独立设计的太阳娘和月亮娘；不保留旧角色的主页按钮，也不以旧角色或参考图生成新素材。Git 历史未重写，历史提交中的旧素材不属于本次发行内容。

当前随包的图片资源如下：

| 文件 | 用途及来源 |
| --- | --- |
| `app-icon-source.png` | 无角色参考的通用视频工具图标原图。 |
| `app-icon.png`、`app-icon.ico` | 图标原图的缩放、圆角和多尺寸派生版本。 |
| `wallpaper-sun.png` | 极昼工作台的日系太阳娘原图。 |
| `wallpaper-moon.png` | 黑夜工作台的日系月亮娘原图。 |
| `wallpaper-day.png`、`wallpaper-night.png` | 独立生成的雪地和黑色地貌原图。 |
| `wallpaper-day-header.png`、`wallpaper-night-header.png` | 对应地貌原图的等比裁切页头。 |

五张原图通过已配置的 65535 通道生成，模型标识为 `gpt-image-2.5-flare`；这是通道标识，不标为 OpenAI 官方型号。每张原图的 `references` 均为空，未发送旧角色、用户截图或其他外部参考图片。

生成通道、提示词、任务标识及原图哈希见 `generation-provenance.json`；最终图片的使用位置、派生配方及哈希见 `art-provenance.json`。`tools/build_ui_art.py` 可离线重建派生资源，不调用生图服务。

来源可追溯和无外部参考生成不代表第三方权利保证。图片与代码的权利范围不同，不能将源码的 GPL 声明解读为对第三方角色、商标、肖像或他人作品的授权；也不承诺生成内容不存在相似性或其他权利争议。

## Lucide 图标

`icons/` 使用 Lucide 上游图标，许可证和版权声明见 `../../licenses/lucide-LICENSE` 及根目录 `THIRD_PARTY_NOTICES.md`。

## 权利问题反馈

权利人可以通过仓库 Issue 提供涉及的文件名和公开可核实的来源，要求移除或替换。请勿在公开 Issue 中上传身份证件、私人合同、未公开原稿或其他敏感材料。
