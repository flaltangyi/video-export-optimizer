# 跨平台与跨智能体适配 / Platform and agent portability

通用导出流程覆盖macOS、Windows、Linux；实际执行依赖本机工程和运行环境。支持一种方法、接口存在、配置检测通过、完成短片输出、确认硬编与完成画质验收是不同状态。本文不设一个能保证所有编码可用的统一系统最低版本。

The export workflow targets macOS, Windows, and Linux. Runtime capability and project integration determine the available path. Workflow coverage, API presence, supported configuration, a successful clip, verified hardware encoding, and quality acceptance are separate claims. There is no universal OS minimum that guarantees all codecs.

## 平台与版本 / Platform and version

先在真正执行导出的进程环境中收集系统、架构、运行时与驱动信息；不要从控制智能体所在设备推定远程导出端。按实际依赖的官方要求核对版本，不把“Windows最新版”或“Linux”当作足够的环境描述。

| 平台 | 必须识别的差异 | 选路时的处理 |
|---|---|---|
| macOS | 系统版本、Apple Silicon／Intel、浏览器／Electron及工程版本 | VideoToolbox是候选后端；现有M4成绩不能代表所有Mac |
| Windows | Windows版本、edition及build、x64／ARM64、原生／WSL／虚拟机／Server、GPU与驱动、浏览器／Electron版本 | N版等系统的媒体组件可能不同；缺能力先定位，不擅自加功能包。原生Windows和WSL分别检测，不能复用同一硬编结论 |
| Linux | 发行版与版本、内核、架构、桌面／headless／容器、浏览器／Electron构建、GPU驱动及设备访问 | 名称相同的浏览器可能有不同编解码构建；容器／远程进程未必能用宿主GPU。按实际可用能力回退，不默认强开GPU标志或放宽设备权限 |

FFmpeg的VideoToolbox、NVENC、QSV、AMF、VAAPI等只是可能的候选，不是按操作系统固定对应的唯一后端；需同时满足实际构建、硬件、驱动、输入格式及运行权限。`ffmpeg -encoders`／`-hwaccels`只帮助发现构建提供的接口，不证明本次会成功启用；WebCodecs与FFmpeg的可用后端也不能互相代证。

Record the exporting environment's OS version/build, architecture, runtime, GPU/driver, and native/WSL/container/remote context. On Windows, distinguish editions and media-component availability. On Linux, record distribution, kernel, browser build, graphical/headless session, and GPU device access. FFmpeg encoder lists and WebCodecs API presence are not proof of successful hardware use. Probe each execution environment independently.

## 能力检测与回退 / Capability checks and fallback

1. 检查工程实际使用的浏览器／Electron版本、Remotion／HyperFrames及封装依赖版本；依据这些版本的官方要求评估支持范围，不随意更新整套环境。
2. 在真实渲染进程检查安全上下文、`VideoEncoder`、`VideoFrame`及所需解码接口；用**本次完整配置**调用`VideoEncoder.isConfigSupported()`。支持列表不能替代实际配置检测；`prefer-hardware`不能代替运行时证据。
3. 确认取帧、字幕字体、图层、布局、转场、音轨和封装已接通。以包含关键效果的代表片段验证；技术检查与人工观看／听取分开。
4. WebCodecs或硬编不可用时，保留符合交付规格的现有路径；可优化其供帧、传输和封装。若必须改输出规格、安装驱动／组件或扩大权限，按用户授权与宿主规则处理；不静默降质。
5. 保存通过配置及其系统／运行时／驱动／工程版本。相关版本或执行环境改变后，复核受影响能力；不把旧Mac报告当作新Windows／Linux结果。

Probe the exact configuration in the real renderer, validate a representative scene, and retain a correct fallback. Bind reusable configurations to their OS/runtime/driver/project versions. A changed environment invalidates the affected assumptions, not necessarily every prior check.

## 跨智能体接入 / Agent integration

- **原生支持Agent Skills的宿主**：按宿主当前支持的安装位置放置完整目录，入口为`SKILL.md`；保留相对引用。自动发现、隐式匹配及权限属于宿主行为，需分别验证。
- **仅支持项目规则或提示词的宿主**：让其在导出任务中读取`SKILL.md`与相关参考文件，使用该宿主实际提供的文件、执行和浏览器工具。没有必要为换智能体重写渲染算法。
- **Codex元数据**：`agents/openai.yaml`只用于相应宿主的界面／调用策略，不是通用流程的依赖；其他宿主可忽略，不把相同策略字段复制成未经证实的兼容配置。
- **固定导出命令**：要让检查必经，需接到项目真实导出入口。技能自动匹配不能约束绕过智能体直接运行的命令。

Hosts with native Agent Skills support should load the complete directory using their documented skill location. Other hosts can read the workflow through their project rules. `agents/openai.yaml` is optional Codex-specific metadata; the shared workflow does not depend on it. Discovery, automatic triggering, permissions, and tool access must be verified for each host.

## 路径、命令和报告 / Paths, commands, and reports

随宿主使用真实可访问路径与临时目录；不内置`/Users/mac`、`/Volumes`、Windows盘符或某家智能体缓存位置。跨设备优先记录项目相对路径和素材身份，不假定文件已经同步。Windows路径有空格时作为单个参数传入；不把POSIX shell、`/dev/null`、符号链接或AppleScript作为通用依赖。程序调用优先使用参数数组，JSON统一UTF-8，空／未知能力明确保留，不猜测成功。

只读基础环境报告需要已有Python3.9+，不安装依赖、不启动外部进程、不探测浏览器或GPU：

```bash
# macOS / Linux — use the actual installed Python
python3 scripts/inspect_environment.py --output environment-report.json
```

```powershell
# Windows — when the Python launcher is installed; otherwise use the actual Python executable
py -3 scripts/inspect_environment.py --output environment-report.json
py -3 scripts/inspect_export.py --input "D:\Videos\成片.mp4" --ffprobe "C:\Tools\ffmpeg\bin\ffprobe.exe" --output export-report.json
```

工具未在PATH里不等于未安装；可为成片检查显式传入`--ffprobe`／`--ffmpeg`。环境报告里的`notProbed`需由智能体在实际工程补齐。没有Python时可手动收集同样信息，无需仅为遵循文档先安装。报告不覆盖旧文件，不含凭据；公开分享前仍需移除本机私有路径。

Use platform-appropriate paths and argument arrays, UTF-8 reports, and existing tools. The environment helper collects metadata only; `notProbed` explicitly lists missing runtime evidence. Commands above are examples, not proof of Windows/Linux execution.

## 已验证范围 / Verification scope

公开性能数据仍来自M4 Mac。2026-10-22这次修订增加跨平台／跨智能体规则与只读环境助手，并在Mac检查脚本行为；没有新增Windows／Linux视频导出或其他智能体自动匹配实测。后续实际接入按平台、版本、宿主分别记录“已通过／不可用／未验证”，不把设计覆盖写成兼容认证。

Published performance measurements remain Mac-specific. This revision adds portable guidance and a read-only helper, tested locally on macOS. Windows/Linux video exports and automatic selection in other agent hosts have not been runtime-validated.

## 官方依据 / Primary sources

- [WebCodecs配置与硬件偏好](https://www.w3.org/TR/webcodecs/#hardware-acceleration)
- [Chromium音视频构建差异](https://www.chromium.org/audio-video/)
- [Windows N媒体功能包](https://support.microsoft.com/en-us/windows/experience/platform-variants/media-feature-pack-for-windows-n)
- [WSL GPU环境参考，非视频编码证明](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gpu-compute)
- [Chromium Linux VAAPI构建、驱动与验证](https://chromium.googlesource.com/chromium/src/+/HEAD/docs/gpu/vaapi.md)
- [FFmpeg硬件加速运行条件](https://ffmpeg.org/ffmpeg.html#Advanced-Video-options)
- [Agent Skills开放规范](https://agentskills.io/specification)
