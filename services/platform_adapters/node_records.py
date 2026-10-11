#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Isolated Windows private-record boundary for the authored Node Host."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    if sys.platform!='win32' or len(sys.argv)!=3:raise ValueError('Windows private record operation required.')
    from platform_adapters.windows_identity import private_directory, private_file_descriptor
    from platform_adapters.private_files import atomic_json, read_json
    operation,path=sys.argv[1:]
    if operation=='directory':private_directory(path)
    elif operation=='verify':os.close(private_file_descriptor(path))
    elif operation=='read':sys.stdout.write(json.dumps(read_json(path),ensure_ascii=True))
    elif operation=='write':
        raw=sys.stdin.buffer.read(16*1024*1024+1)
        if len(raw)>16*1024*1024:raise ValueError('Private record exceeds its bound.')
        private_directory(Path(path).parent);atomic_json(path,json.loads(raw.decode('utf-8')))
    else:raise ValueError('Unknown private record operation.')


if __name__=='__main__':
    try:main()
    except Exception:
        print('Private Windows record operation was refused.',file=sys.stderr)
        raise SystemExit(1)
