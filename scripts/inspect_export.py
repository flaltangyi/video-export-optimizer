#!/usr/bin/env python3
"""Inspect an exported video without changing it; optionally decode to a null sink.

Only the Python standard library is required. Install/provide ffprobe separately,
and ffmpeg when --strict-decode is requested. This is a file/contract check, not
a visual-quality, hardware-acceleration, browser-playback, or human-review test.
"""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys


def positive_number(text):
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError('must be a positive finite number')
    return value


def positive_integer(text):
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError('must be a positive integer')
    return value


def positive_rate(text):
    try:
        value = Fraction(text)
    except (ValueError, ZeroDivisionError):
        raise argparse.ArgumentTypeError('use a positive rate such as 30 or 30000/1001')
    if value <= 0:
        raise argparse.ArgumentTypeError('frame rate must be positive')
    return value


def as_fraction(value):
    try:
        return Fraction(str(value))
    except (ValueError, TypeError, ZeroDivisionError):
        return None


def executable(value, name):
    candidate = shutil.which(str(value)) if value else shutil.which(name)
    if not candidate:
        raise FileNotFoundError(f'{name} not found; provide --{name} or add it to PATH. Nothing was installed.')
    return candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--ffprobe', help='ffprobe executable; defaults to PATH')
    parser.add_argument('--ffmpeg', help='ffmpeg executable for strict decoding; defaults to PATH')
    parser.add_argument('--expected-width', type=positive_integer)
    parser.add_argument('--expected-height', type=positive_integer)
    parser.add_argument('--expected-fps', type=positive_rate)
    parser.add_argument('--expected-duration', type=positive_number, help='video seconds; tolerance is one reported frame or 1ms')
    parser.add_argument('--min-video-bitrate-mbps', type=positive_number)
    parser.add_argument('--max-video-bitrate-mbps', type=positive_number)
    parser.add_argument('--strict-decode', action='store_true')
    parser.add_argument('--timeout-seconds', type=positive_number, default=300)
    parser.add_argument('--output', type=Path, help='new JSON report file; existing files are never overwritten')
    args = parser.parse_args()
    if (args.min_video_bitrate_mbps and args.max_video_bitrate_mbps
            and args.min_video_bitrate_mbps > args.max_video_bitrate_mbps):
        parser.error('minimum video bitrate must not exceed maximum')
    if args.output and args.output.exists():
        print(f'Refusing to overwrite existing report: {args.output}', file=sys.stderr)
        return 2

    report = dict(schema='video-export-inspection-v1', status='INCOMPLETE', checks=[], commands=[],
                  qualityVerified=False, hardwareAccelerationVerified=False,
                  browserPlaybackVerified=False, humanWatchCompleted=False,
                  humanListeningCompleted=False, inputModified=False,
                  scope='First video stream, all audio metadata; packet bitrate and optional full first-video/audio decode. No reference-picture quality comparison.')
    exit_code = 2
    media = args.input.expanduser().resolve()

    def command(argv):
        report['commands'].append([str(x) for x in argv])
        p = subprocess.run([str(x) for x in argv], capture_output=True, text=True,
                           timeout=args.timeout_seconds, errors='replace')
        if p.returncode:
            raise RuntimeError(json.dumps(dict(executable=str(argv[0]), exitCode=p.returncode,
                                              stderr=p.stderr[-4000:]), ensure_ascii=False))
        return p.stdout

    def check(name, passed, observed, expected):
        report['checks'].append(dict(name=name, passed=bool(passed), observed=observed, expected=expected))

    try:
        if not media.is_file():
            raise FileNotFoundError(f'Input is not a local regular file: {media}')
        before = media.stat()
        report.update(input=str(media), fileBytes=before.st_size)
        probe = executable(args.ffprobe, 'ffprobe')
        metadata = json.loads(command([probe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', media]))
        videos = [s for s in metadata.get('streams', []) if s.get('codec_type') == 'video']
        audios = [s for s in metadata.get('streams', []) if s.get('codec_type') == 'audio']
        if not videos:
            raise ValueError('No video stream found; this helper inspects video exports')
        video = videos[0]
        rate = as_fraction(video.get('avg_frame_rate'))
        if not rate or rate <= 0:
            rate = as_fraction(video.get('r_frame_rate'))
        if not rate or rate <= 0:
            rate = None
        duration = None
        duration_source = None
        ticks, time_base = as_fraction(video.get('duration_ts')), as_fraction(video.get('time_base'))
        if ticks is not None and time_base and ticks * time_base > 0:
            duration, duration_source = ticks * time_base, 'video.duration_ts * video.time_base'
        else:
            duration = as_fraction(video.get('duration'))
            if duration and duration > 0:
                duration_source = 'video.duration'
            else:
                duration = None
        declared_count = video.get('nb_frames')
        declared_count = int(declared_count) if str(declared_count).isdigit() else None
        report['video'] = {k: video.get(k) for k in ['codec_name', 'codec_tag_string', 'profile', 'level',
                          'width', 'height', 'pix_fmt', 'color_range', 'color_space', 'color_transfer', 'color_primaries']}
        report['video'].update(fps=float(rate) if rate else None, fpsFraction=str(rate) if rate else None,
                              declaredFrameCount=declared_count,
                              durationSeconds=float(duration) if duration else None,
                              durationSource=duration_source,
                              frameRateMeaning='Reported stream average/rate; CFR at every timestamp is not verified by this metadata check')
        report['audio'] = [{k: s.get(k) for k in ['codec_name', 'sample_rate', 'channels', 'channel_layout', 'duration']}
                           for s in audios]
        report['streamCounts'] = dict(video=len(videos), audio=len(audios), total=len(metadata.get('streams', [])))
        packets = json.loads(command([probe, '-v', 'error', '-select_streams', 'v:0', '-show_packets',
                             '-show_entries', 'packet=size', '-of', 'json', media])).get('packets', [])
        packet_bytes = sum(int(p['size']) for p in packets)
        bitrate = float(packet_bytes * 8 / duration) if duration and packets else None
        report['video'].update(packetCount=len(packets), packetBytes=packet_bytes,
                              actualBitrateBps=bitrate, actualBitrateMbps=bitrate / 1e6 if bitrate else None,
                              bitrateMeaning='Sum of first-video packet bytes * 8 / reported video stream duration; excludes audio/container bytes. No container-bitrate substitution.')
        for field in ['width', 'height']:
            expected = getattr(args, 'expected_' + field)
            if expected is not None:
                check(field, video.get(field) == expected, video.get(field), expected)
        if args.expected_fps is not None:
            check('fps', rate is not None and abs(float(rate - args.expected_fps)) <= 1e-6,
                  str(rate) if rate else None, str(args.expected_fps))
        if args.expected_duration is not None:
            tolerance = max(float(1 / rate) if rate else 0, .001)
            check('duration', duration is not None and abs(float(duration) - args.expected_duration) <= tolerance,
                  float(duration) if duration else None, dict(seconds=args.expected_duration, toleranceSeconds=tolerance))
        if args.min_video_bitrate_mbps is not None:
            check('minimumActualVideoBitrate', bitrate is not None and bitrate >= args.min_video_bitrate_mbps * 1e6,
                  bitrate, args.min_video_bitrate_mbps * 1e6)
        if args.max_video_bitrate_mbps is not None:
            check('maximumActualVideoBitrate', bitrate is not None and bitrate <= args.max_video_bitrate_mbps * 1e6,
                  bitrate, args.max_video_bitrate_mbps * 1e6)
        if args.strict_decode:
            ffmpeg = executable(args.ffmpeg, 'ffmpeg')
            encoders = command([ffmpeg, '-hide_banner', '-v', 'error', '-encoders'])
            muxers = command([ffmpeg, '-hide_banner', '-v', 'error', '-muxers'])
            encoder_names = {line.split()[1] for line in encoders.splitlines() if len(line.split()) >= 2}
            muxer_names = {line.split()[1] for line in muxers.splitlines() if len(line.split()) >= 2}
            missing = [n for n in ['rawvideo'] + (['pcm_s16le'] if audios else []) if n not in encoder_names]
            if 'null' not in muxer_names:
                missing.append('null muxer')
            if missing:
                report['strictDecode'] = dict(status='TOOL_CAPABILITY_MISSING', missing=missing,
                    meaning='The selected ffmpeg lacks required output capabilities; no media-corruption conclusion was made')
                raise RuntimeError('Strict-decode tool capabilities unavailable: ' + ', '.join(missing))
            report['strictDecode'] = dict(status='RUNNING')
            progress = command([ffmpeg, '-v', 'error', '-nostdin', '-xerror', '-err_detect', 'explode', '-i', media,
                       '-map', '0:v:0', '-map', '0:a?', '-c:v', 'rawvideo', '-c:a', 'pcm_s16le',
                       '-progress', 'pipe:1', '-nostats', '-f', 'null', '-'])
            counts = [int(s.split('=', 1)[1].strip()) for s in progress.splitlines() if s.startswith('frame=')]
            decode_complete = 'progress=end' in progress
            report['strictDecode'] = dict(status='PASS' if decode_complete else 'FAILED_OR_UNSUPPORTED',
                                          decodedVideoFrames=counts[-1] if counts else None,
                                          meaning='Full first-video and audio decoding to null sink; not real-time playback, visual quality, audio listening, or sync acceptance')
            check('strictDecodeCompleted', decode_complete, decode_complete, True)
        after = media.stat()
        check('sourceFileMetadataUnchanged', (before.st_size, before.st_mtime_ns, before.st_ino) ==
              (after.st_size, after.st_mtime_ns, after.st_ino),
              dict(bytes=after.st_size, mtimeNs=str(after.st_mtime_ns)),
              dict(bytes=before.st_size, mtimeNs=str(before.st_mtime_ns)))
        failed = any(not item['passed'] for item in report['checks'])
        report['status'] = 'FAIL_REQUIREMENTS' if failed else 'INSPECTION_COMPLETE'
        exit_code = 1 if failed else 0
    except FileNotFoundError as error:
        report.update(status='INPUT_OR_TOOL_UNAVAILABLE', error=str(error))
    except Exception as error:
        report.update(status='INSPECTION_FAILED_OR_UNSUPPORTED', error=str(error))
        if report.get('strictDecode', {}).get('status') == 'RUNNING':
            report['strictDecode'] = dict(status='FAILED_OR_UNSUPPORTED',
                                         meaning='Decode command failed; inspect tool error before attributing this to damaged media')
    if args.output:
        try:
            with args.output.open('x') as handle:
                json.dump(report, handle, ensure_ascii=False, indent=2)
                handle.write('\n')
        except OSError as error:
            print(f'Cannot create a new report (nothing was overwritten): {error}', file=sys.stderr)
            return 2
        print(json.dumps(dict(status=report['status'], report=str(args.output)), ensure_ascii=False))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
