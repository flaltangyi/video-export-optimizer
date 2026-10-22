# Video Export Optimizer

面向视频编辑与成片导出的Agent Skill：**先满足画质和内容要求，再减少导出过程中的等待、画面交接和重复读写。**

作者：毅直有办法。方法来自实际视频制作中的磁盘空间问题与导出流程实测。

## 它能做什么

安装后，支持隐式技能匹配的Agent可在你说“导出视频”“渲染成片”“生成MP4”等正常任务时选择此技能，不要求每次输入技能名。它会结合当前工程的实际能力，检查原素材、字幕、布局、图层和音轨，选择已经支持或能够验证的较快路径，并检查交付规格。

这是导出方法与只读验收工具的组合。实际渲染仍由项目中的Remotion、HyperFrames或其他引擎执行；项目需要相应能力或适配。安装此包不会自动把任意工程转换成WebCodecs，也不会接管剪辑软件的所有导出按钮。

## 是否需要先安装WebCodecs

**使用WebCodecs导出路径，需要支持它的运行环境和已经接通的工程；安装Skill本身不要求先安装WebCodecs。** WebCodecs是浏览器内置接口，不是一个独立安装包。只装Node.js或一个名为WebCodecs的依赖，也不会让现有导出命令自动变成硬件编码。[接口说明](https://developer.mozilla.org/en-US/docs/Web/API/WebCodecs_API)

首次导出时，Agent应检查：

1. 实际导出所在的浏览器／Electron渲染进程提供所需接口，并在安全上下文中运行；本地开发可使用符合条件的localhost。不能只看浏览器名称或是否安装。[安全上下文](https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts)
2. 本次编码格式、尺寸、帧率和码率等配置可用，使用`VideoEncoder.isConfigSupported()`检测；是否真正使用硬件另看运行时证据。[配置检测](https://developer.mozilla.org/en-US/docs/Web/API/VideoEncoder/isConfigSupported_static)
3. 工程能把原素材、字幕和图层合成为最终画面，并接到编码器、音轨处理和MP4封装。若采用Remotion Web Renderer，需要与工程版本配套的依赖，并检查其效果支持范围。[Remotion说明](https://www.remotion.dev/docs/web-renderer)

首次接入按“检查环境 → 补齐必要依赖与适配 → 验证代表片段 → 保留通过的项目配置”处理；以后普通导出复用。此包提供选路规则和成片检查脚本，当前没有通用的WebCodecs安装器或自动迁移所有工程的适配器。缺少WebCodecs时仍可沿现有渲染／FFmpeg路径优化等待、传输和封装，收益以本项目实测为准。

## 安装与正常使用

把本仓库的技能目录安装到当前Agent支持的技能位置。Codex可通过内置`$skill-installer`安装GitHub技能；也可以把本目录复制到用户技能目录，保持`SKILL.md`位于`video-export-optimizer/`根部。

当前[官方技能文档](https://developers.openai.com/codex/skills/)列出的用户位置是`~/.agents/skills/`；部分现有Codex环境使用`~/.codex/skills/`。选择当前实例实际加载的位置，不在两处重复安装同名副本。

正常请求示例：

> 把这个项目导出为1080×1920、30fps的MP4，保留当前字幕、转场和音轨，按项目已经确认的画质设置输出。

本包的`agents/openai.yaml`启用了`allow_implicit_invocation: true`。隐式匹配由宿主Agent决定，不是“每次一定调用”的硬性拦截器。文件安装完成与真实会话中已经自动选中，是两个需要分别验证的状态。

### 接到固定项目的导出流程

若希望团队在同一个项目里无需记住技能名，可将下面的项目指令放入项目已使用的Agent指令文件，结合现有规则调整：

```markdown
当本项目的任务包含导出视频、渲染成片或生成MP4时，使用可用的
video-export-optimizer技能处理导出阶段，沿用本项目已确认的内容和画质设置。
先确认原素材、字幕图层、音轨、分辨率、帧率、编码及质量要求，
再选可用且经过验证的较快路径；不以降规格、删效果或复用失效音轨换速度。
实际执行既有项目导出入口，随后检查实际规格、码率、解码和必要的内容保留。
若技能不可用，按既有保真流程导出并说明，不能因此假装已经应用优化。
```

如果要求`npm run export`等命令自身每次都执行前后检查，需要将检查步骤真正接入该项目脚本。项目指令和技能不会改变一个普通命令本身的行为。本仓库不自动改动其他项目的导出脚本。

## 画质要求如何参与选路

- 沿用用户或项目已批准的分辨率、帧率、时间线、字幕图层和音频编辑。
- 按内容与交付目标确定码率；不把6.4Mbps套用到所有视频。
- 相同名义码率可能得到不同实际码率；同码率也不等于同画质。
- 浏览器端合成不支持的字体、CSS、转场、HDR或其他效果需要保真回退，不能静默丢弃。
- H.264与H.265都可能硬编；H.265不保证更快。是否使用硬编要看运行时证据。
- 硬件、项目和画面不同，收益不同；保留内存和磁盘余量。

更多实现决策见[路径说明](references/pipeline-routing.md)。

## 只读成片检查

需要Python3与独立可用的`ffprobe`。完整解码另需`ffmpeg`；工具路径可显式提供，脚本不下载安装依赖、不修改视频。

```bash
python3 scripts/inspect_export.py --help
python3 scripts/inspect_export.py --input output.mp4 --output export-report.json
```

把已确认的尺寸、帧率、时长或实际码率范围作为相应参数传入。报告能检查技术规格与解码，不能单独证明视觉清晰度、字幕图层保留、音画同步、硬件启用或所有设备兼容。

## 实测来源和边界

一条6分04秒原素材视频的两条完整Remotion导出路线，各3次中位数为15分25.34秒与2分05.25秒，速度约为原来的7.39倍。对照包含音轨准备和相同最终封装；改动涉及供帧、合成/捕获和编码流程，不能归功于单一API。

另一次同一30秒片段的H.264/H.265试跑，各3次中位数约10.085秒与10.057秒，速度基本持平。实际视频码率分别约5.40与4.78Mbps，不是同画质对照。

这些个案**不是安装后的性能保证**。细节、质量与资源取舍见[实测边界](references/benchmark-boundary.md)。仓库只含通用方法、原创辅助脚本和脱敏汇总，不包含原始视频、录音、私有工程、日志或第三方bundle。

## 公开技术参考

- [Remotion Web Renderer](https://www.remotion.dev/docs/web-renderer)：现有浏览器端渲染能力及限制。
- [WebCodecs规范](https://www.w3.org/TR/webcodecs/)：编解码接口与硬件偏好的语义。
- [Codex技能说明](https://developers.openai.com/codex/skills/)：显式/隐式匹配与技能位置。

本包不再发布上述项目的代码；第三方工具按各自许可使用。本包原创文件采用MIT许可，见[LICENSE](LICENSE)。
