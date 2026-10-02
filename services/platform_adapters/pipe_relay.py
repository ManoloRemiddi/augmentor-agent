#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Windows Node client adapter: private inherited stdio to authenticated OS pipe.

The parent passes only an endpoint path in argv. Protocol bytes remain on binary
stdio, and the single bounded stderr handshake reports whether connecting failed
before any request could be sent. Failures after connection never invite replay.
"""
import json
import os
from pathlib import Path
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from platform_adapters.windows_pipe import PipeSocket


def main():
    if len(sys.argv) != 2:
        raise SystemExit('A private endpoint is required.')
    import msvcrt
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    connection = PipeSocket()
    connection.settimeout(5)
    try:
        connection.connect(sys.argv[1])
    except Exception as error:
        code = 'ENOENT' if isinstance(error, FileNotFoundError) else 'EACCES' if isinstance(error, PermissionError) else 'EIO'
        print(json.dumps({'code': code, 'message': 'The private companion could not be connected.'}), file=sys.stderr, flush=True)
        connection.close()
        return 2
    connection.settimeout(None)
    print('{"connected":true}', file=sys.stderr, flush=True)

    def send():
        try:
            while True:
                chunk = os.read(sys.stdin.fileno(), 65536)
                if not chunk:
                    break
                connection.sendall(chunk)
        except (OSError, ValueError):
            pass
        finally:
            connection.close()

    threading.Thread(target=send, daemon=True).start()
    try:
        while True:
            chunk = connection.recv(65536)
            if not chunk:
                break
            offset = 0
            while offset < len(chunk):
                offset += os.write(sys.stdout.fileno(), chunk[offset:])
    except (OSError, ValueError):
        return 3
    finally:
        connection.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
