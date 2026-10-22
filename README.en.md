# Video Export Optimizer

[简体中文](README.md) | English

An Agent Skill for video editing and final exports: **meet the required visual quality and preserve the content first, then reduce waiting, frame handoffs, and repeated reads and writes during export.**

Author: 毅直有办法. The approach grew out of disk space constraints and measurements of real video production workflows.

## What it does

Once installed, an Agent that supports implicit skill matching can select this skill for ordinary requests such as “export the video,” “render the final video,” or “generate an MP4.” You do not need to name the skill each time. It considers what the current project actually supports, checks the source media, subtitles, layout, layers, and audio tracks, selects a faster path that is already supported or can be validated, and checks the delivery specifications.

The package combines export guidance with a read-only inspection tool. Rendering is still performed by the project's Remotion, HyperFrames, or other engine; the project must provide the necessary capabilities or integration. For HyperFrames, this skill provides guidance on choosing and adapting an export path; it does not include a general-purpose HyperFrames renderer. Installing this package will not automatically convert arbitrary projects to WebCodecs or take over every export button in an editing application.

## Remotion and HyperFrames support

| Project | Guidance provided by this skill | Integration requirements |
|---|---|---|
| Remotion | Direct source-frame delivery, preserving component compositing, encoder and muxing selection, quality and resource checks | Use a validated project export entry point; Web Renderer must support the project's version and effects |
| HyperFrames | Reduce PNG captures and per-frame round trips; evaluate direct video-frame delivery with DOM overlays; validate audio and the final video | Requires a project-specific adapter; arbitrary HTML/CSS, multiple video layers, and complex blending cannot automatically become an equivalent Canvas composition |

**HyperFrames is covered.** The guidance draws on the author's local adaptation experiments, with full-length results listed separately below. The package does not bundle a universal HyperFrames renderer or one-click hardware-encoding adapter. Unsupported effects need a path that preserves them; removing subtitles, layouts, or layers is not an optimization.

## Do I need to install WebCodecs first?

**A WebCodecs export path requires a compatible runtime and a project that has been integrated with it. Installing the skill itself does not require installing WebCodecs first.** WebCodecs is a built-in browser API, not a standalone package. Installing Node.js or a dependency named WebCodecs does not automatically make an existing export command use hardware encoding. [API overview](https://developer.mozilla.org/en-US/docs/Web/API/WebCodecs_API)

Before the first export, the Agent should check that:

1. The browser or Electron renderer process that actually performs the export provides the required APIs and runs in a secure context. A qualifying localhost environment can be used for local development. The browser's name or the fact that it is installed is not sufficient evidence. [Secure contexts](https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts)
2. The required codec, dimensions, frame rate, bitrate, and other settings are supported, using `VideoEncoder.isConfigSupported()`. Whether hardware encoding is actually used requires separate runtime evidence. [Configuration support check](https://developer.mozilla.org/en-US/docs/Web/API/VideoEncoder/isConfigSupported_static)
3. The project can composite the source media, subtitles, and layers into final frames and connect them to the encoder, audio processing, and MP4 muxing. If it uses Remotion Web Renderer, its dependencies must match the project version, and the supported effects must be checked. [Remotion documentation](https://www.remotion.dev/docs/web-renderer)

For the initial integration, follow this sequence: check the environment → add the necessary dependencies and integration → validate a representative clip → retain the validated project configuration. Reuse that configuration for subsequent routine exports. This package provides routing rules and a finished-video inspection script. It currently includes neither a general-purpose WebCodecs installer nor an adapter that automatically migrates every project. When WebCodecs is unavailable, the existing rendering/FFmpeg path can still be used to reduce unnecessary waiting, transfers, and muxing work. Any benefit must be measured in the actual project.

## Installation and everyday use

Install the skill directory from this repository in a location supported by your Agent. Codex can install a GitHub skill through the built-in `$skill-installer`. Alternatively, copy this directory to the user skill directory, keeping `SKILL.md` at the root of `video-export-optimizer/`.

The current [official skills documentation](https://developers.openai.com/codex/skills/) lists `~/.agents/skills/` as the user location. Some existing Codex environments use `~/.codex/skills/`. Use the location that your current instance actually loads; do not install duplicate copies of the same skill in both locations.

Example of a normal request:

> Export this project as a 1080×1920, 30 fps MP4. Preserve the current subtitles, transitions, and audio tracks, and use the project's approved quality settings.

The package's `agents/openai.yaml` enables `allow_implicit_invocation: true`. Implicit matching is decided by the host Agent; it is not an interceptor that guarantees the skill runs every time. Installing the files and confirming that the skill was automatically selected in a real session are two separate checks.

### Connect it to a project's regular export workflow

If you want a team working in the same project to use the skill without remembering its name, add instructions like the following to the Agent instruction file the project already uses, adapting them to its existing rules:

```markdown
When a task in this project includes exporting video, rendering a final video,
or generating an MP4, use the available video-export-optimizer skill for the
export stage. Preserve the project's approved content and quality settings.
First confirm the source media, subtitle layers, audio tracks, resolution,
frame rate, codec, and quality requirements. Then select a faster path that
is available and has been validated. Do not gain speed by lowering the
specifications, removing effects, or reusing invalid audio tracks.
Run the project's existing export entry point, then check the actual
specifications, bitrate, decoding, and preservation of the required content.
If the skill is unavailable, use the existing path that preserves the content
and quality, and report that fallback. Do not claim that optimization was applied.
```

If a command such as `npm run export` must perform checks before and after every run, those checks need to be integrated into the project's scripts. Project instructions and a skill do not change the behavior of an ordinary command by themselves. This repository does not automatically modify other projects' export scripts.

## How quality requirements affect routing

- Preserve the resolution, frame rate, timeline, subtitle layers, and audio edits approved by the user or project.
- Choose bitrate based on the content and delivery target; do not apply 6.4 Mbps to every video.
- The same nominal bitrate can produce different actual bitrates. The same bitrate does not imply the same visual quality.
- Fonts, CSS, transitions, HDR, or other effects that browser-side compositing cannot support require a fallback that preserves them; they must not be silently discarded.
- Both H.264 and H.265 can use hardware encoding. H.265 is not guaranteed to be faster. Actual hardware use requires runtime evidence.
- Benefits vary with the hardware, project, and visual content. Leave sufficient memory and disk headroom.

See [pipeline routing (Chinese)](references/pipeline-routing.md) for more implementation decisions.

## Read-only export inspection

Requires Python 3 and a separately available `ffprobe`. Full decoding additionally requires `ffmpeg`. Tool paths can be supplied explicitly; the script does not download or install dependencies and does not modify the video.

```bash
python3 scripts/inspect_export.py --help
python3 scripts/inspect_export.py --input output.mp4 --output export-report.json
```

Pass the approved dimensions, frame rate, duration, or actual bitrate range through the corresponding arguments. The report can check technical specifications and decoding. By itself, it cannot establish visual clarity, preservation of subtitles and layers, audiovisual synchronization, hardware encoding use, or compatibility with every device.

## Measured results and limitations

These are summaries of the author's project measurements on an M4 Mac. The full video used source assets, subtitles, layers, and the original timeline: 364.133 seconds, 10,924 frames, 1080×1920, 30 fps. Existing 3D clips were used as inputs; upstream 3D rendering was not repeated. The three experiments use different timing boundaries and repetition counts, so they must be read separately rather than combined into a framework ranking.

### Remotion: two full-length export paths, 3 runs each

| Median of 3 runs | In-memory PNG pipeline + FFmpeg software encoding | Direct frame delivery + WebCodecs hardware encoding |
|---|---:|---:|
| Complete export time | 15:25.34 (925.34 s) | 2:05.25 (125.25 s) |
| Actual video bitrate | 6.333 Mbps | 6.221 Mbps |
| Final MP4 size, decimal MB | 296.44 | 291.31 |
| Sampled additional disk peak, MiB | 763.0 | 701.0 |
| Sampled process-tree peak RSS, GiB | 2.056 | 2.582 |

The faster path was approximately **7.39 times as fast**. Each run included fresh AAC preparation from the original WAV, the browser lifecycle, picture output, the same final stream-copy mux, fsync, and basic checks. Build, preflight, and post-export QA were excluded. Each path ran 3 times in a fixed interleaved, non-random order. Actual bitrates were close but not identical; OS caches were not cleared and unrelated applications were not stopped.

This compares complete paths involving frame delivery, compositing/capture, and encoding, not a single API. All six files passed full decoding, frame-count/timestamp, source-frame, and audio checks. Selected images still showed differences in color, font edges, and shadows; neither lossless output nor improved visual quality was established. The median sampled disk peak fell by about 8.1%, while median peak RSS rose by about 25.6%; not every individual disk peak was lower.

### HyperFrames: a project-specific adapter before and after optimization, 1 run each

The source media, subtitles, layouts, and layers were retained. The baseline adapter already used **in-memory PNG capture + WebCodecs hardware encoding**. The optimized path retained the original runtime, GSAP, and DOM overlays, reducing PNG conversion and per-frame cross-process round trips through project-specific video-frame delivery and capture integration. Both paths were observed using Apple VideoToolbox hardware encoding; this was not a software-to-hardware encoder switch.

| Single measurement, n=1 per version | Baseline adapter | Optimized adapter |
|---|---:|---:|
| End-to-end AV-ready time | 34:55.67 (2095.67 s) | 3:41.54 (221.54 s) |
| Actual video bitrate | About 6.142 Mbps | About 6.142 Mbps |
| Final MP4 size, MiB | 274.40 | 274.39 |
| Sampled additional disk peak, MiB | 635.38 | 639.25 |
| Sampled process-tree peak RSS, GiB | 2.205 | 2.098 |

The observed time ratio was approximately **9.46×**, not an established repeatable speedup or the default performance of upstream HyperFrames. Timing began at wrapper startup and ended after audiovisual muxing closed, fsync, and basic probing. A shared AAC track was freshly prepared from the original WAV for this experiment, but its **7.537-second preparation cost was outside both export clocks** and must be added for a standalone export from WAV. This differs from the Remotion experiment above, which includes audio preparation on every run.

Both versions passed all 10,924 frame/PTS and audio checks, but their decoded images were not pixel-identical. Against the baseline adapter's output, full-frame YUV PSNR was **54.21 dB** and SSIM was **0.998959**; 747 of 10,924 decoded frames were identical. These metrics measure change relative to the baseline, not independent lossless ground truth or absolute quality across frameworks. The sampled disk peak increased slightly, so this example does not show all resource use falling. Unsupported complex video stacking requires a fallback; this adapter's results do not establish equivalent behavior for arbitrary HTML scenes.

### H.264/H.265: the same 30-second clip, 3 runs each

| Median of 3 runs | H.264 | H.265/HEVC |
|---|---:|---:|
| Complete export time | 10.085 s | 10.057 s |
| Actual video bitrate | 5.399 Mbps | 4.782 Mbps |
| Final MP4 size, decimal MB | 20.955 | 18.641 |

The clip contained 900 frames at 1080×1920 and 30 fps, with the same component compositing and quality-priority configuration. Both codecs were observed using platform hardware encoding. Every run included fresh audio preparation and the same final muxing step. Speed was essentially unchanged: the median difference was only about 0.028 seconds, much smaller than run-to-run variation. The H.265 file was about 11.04% smaller, but its actual bitrate was also lower; equal-quality size savings were not established. Do not extrapolate these 30-second timings to a full video.

Disk figures sample allocated file space, and RSS figures sample the process tree. Sampling can miss brief peaks or double-count shared pages; it does not represent all system or GPU memory. Continuous full-length human viewing, listening, and user acceptance have not been completed for these results. File and automated checks do not replace those steps.

These individual results **are not performance guarantees after installation**. See [benchmark limitations (Chinese)](references/benchmark-boundary.md) for details, quality differences, and resource tradeoffs. The repository contains only general guidance, original helper scripts, and de-identified summaries. It does not include the original videos, recordings, private projects, logs, or third-party bundles.

## Public technical references

- [Remotion Web Renderer](https://www.remotion.dev/docs/web-renderer): existing browser-side rendering capabilities and limitations.
- [WebCodecs specification](https://www.w3.org/TR/webcodecs/): codec APIs and the semantics of hardware preferences.
- [Codex skills documentation](https://developers.openai.com/codex/skills/): explicit and implicit matching, and skill locations.

This package does not redistribute code from the projects listed above. Third-party tools remain subject to their respective licenses. Original files in this package are licensed under MIT; see [LICENSE](LICENSE).
