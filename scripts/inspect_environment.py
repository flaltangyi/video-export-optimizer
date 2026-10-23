#!/usr/bin/env python3
"""Read local OS/runtime metadata; no installs, external commands or codec tests.

Run in the environment that will actually export the video. The report is not
proof of WebCodecs support, available GPU devices, or hardware acceleration.
Python 3.9+ standard library only. Existing report files are never overwritten.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import sys


def linux_release():
    if hasattr(platform, 'freedesktop_os_release'):
        try:
            info = platform.freedesktop_os_release()
            return {k: info.get(k) for k in ('ID', 'VERSION_ID', 'PRETTY_NAME')}
        except OSError:
            pass
    try:
        info = {}
        for line in Path('/etc/os-release').read_text(encoding='utf-8').splitlines():
            key, sep, value = line.partition('=')
            if sep and key in ('ID', 'VERSION_ID', 'PRETTY_NAME'):
                info[key] = value.strip().strip('"').strip("'")
        return info
    except OSError:
        return {}


def collect():
    system = platform.system()
    result = {
        'schema': 'video-export-environment-v1',
        'os': {'system': system, 'release': platform.release(),
               'version': platform.version(), 'architecture': platform.machine()},
        'python': {'version': platform.python_version(), 'executable': sys.executable},
        'pathExecutables': {name: shutil.which(name) for name in ('node', 'ffmpeg', 'ffprobe')},
        'executionContext': {
            'wslHint': system == 'Linux' and ('microsoft' in platform.release().lower()
                                             or bool(os.environ.get('WSL_DISTRO_NAME'))),
            'containerHint': Path('/.dockerenv').exists(),
            'meaning': 'Hints only; confirm native/WSL/container/remote context with the actual export process.'},
        'notProbed': ['browser/Electron and framework versions', 'GPU model and driver',
                      'host OS/build behind WSL, container, VM or remote execution',
                      'GPU device access and graphical/headless session',
                      'WebCodecs APIs and exact codec configuration',
                      'FFmpeg build, encoder runtime and target-player compatibility'],
        'hardwareAccelerationVerified': False,
        'webCodecsConfigVerified': False,
        'externalCommandsRun': False,
        'scope': 'Local metadata and PATH lookup only; a tool missing from PATH may still exist elsewhere.'}
    if system == 'Windows':
        release, version, service_pack, product_type = platform.win32_ver()
        result['os']['windows'] = {'release': release, 'version': version,
                                  'servicePack': service_pack, 'productType': product_type,
                                  'edition': platform.win32_edition() if hasattr(platform, 'win32_edition') else None}
    elif system == 'Darwin':
        result['os']['macOSVersion'] = platform.mac_ver()[0]
    elif system == 'Linux':
        result['os']['distribution'] = linux_release()
    return result


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='new UTF-8 JSON file; no overwrite')
    args = parser.parse_args()
    report = collect()
    text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        try:
            with args.output.open('x', encoding='utf-8') as handle:
                handle.write(text)
        except OSError as error:
            print(f'Cannot create a new report (nothing was overwritten): {error}', file=sys.stderr)
            return 2
        print(json.dumps({'report': str(args.output), 'hardwareAccelerationVerified': False}, ensure_ascii=False))
    else:
        print(text, end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
