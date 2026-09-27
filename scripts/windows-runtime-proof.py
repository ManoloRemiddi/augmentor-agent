#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Run real Windows runtime imports, computation, DLL and private-shell checks."""
import argparse
import ctypes
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys


def pe_machine(path):
    with Path(path).open('rb') as stream:
        if stream.read(2) != b'MZ':
            raise ValueError('Missing PE header: '+str(path))
        stream.seek(0x3c)
        offset = struct.unpack('<I', stream.read(4))[0]
        stream.seek(offset)
        if stream.read(4) != b'PE\0\0':
            raise ValueError('Invalid PE signature: '+str(path))
        return struct.unpack('<H', stream.read(2))[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--arch', choices=('x64', 'arm64'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    assert sys.platform == 'win32'
    config = json.loads((root/'runtime-lock.json').read_text())
    expected = 0xaa64 if args.arch == 'arm64' else 0x8664
    native, process = ctypes.c_ushort(), ctypes.c_ushort()
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.IsWow64Process2.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ushort), ctypes.POINTER(ctypes.c_ushort)]
    if not kernel.IsWow64Process2(kernel.GetCurrentProcess(), ctypes.byref(process), ctypes.byref(native)):
        raise ctypes.WinError(ctypes.get_last_error())
    assert native.value == expected and process.value == 0, 'Proof must run as a native process, not emulated'
    assert platform.python_version() == config['python']
    for name, version in config['pythonPackages'].items():
        assert importlib.metadata.version(name) == version, name
    # Loading the real native modules catches missing C runtimes and ABI mismatches.
    import numpy as np
    import onnxruntime as ort
    import sounddevice as sd
    import yaml
    import websocket
    import velopack
    from PySide6.QtCore import qVersion
    from PySide6.QtGui import QImage
    from PySide6.QtWidgets import QApplication, QLabel
    from PySide6.QtTest import QTest
    from PySide6.QtQuick import QQuickWindow
    assert np.dot(np.array([2, 3]), np.array([4, 5])) == 23
    assert 'CPUExecutionProvider' in ort.get_available_providers()
    assert sd.get_portaudio_version()[0] > 0
    assert yaml.safe_load('test: true')['test']
    application = QApplication.instance() or QApplication([])
    label = QLabel('Augmentor — native Windows '+args.arch)
    label.resize(360, 80); label.show(); QTest.qWait(50)
    screenshot = label.grab().toImage()
    assert not screenshot.isNull()
    label.close()
    node = json.loads(subprocess.check_output([str(root/'node/node.exe'), '-p',
        'JSON.stringify({version:process.versions.node,arch:process.arch})'], text=True))
    assert node == {'version': config['node'], 'arch': args.arch}
    shell = json.loads(subprocess.check_output([str(root/'powershell/pwsh.exe'), '-NoLogo', '-NoProfile',
        '-NonInteractive', '-Command',
        '[ordered]@{version=$PSVersionTable.PSVersion.ToString(); arch=[System.Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture.ToString()} | ConvertTo-Json -Compress'], text=True))
    assert shell['version'] == config['powershell'] and shell['arch'].lower() == args.arch
    binaries = {}
    for name in ('python/python.exe', 'python/python313.dll', 'node/node.exe', 'powershell/pwsh.exe'):
        machine = pe_machine(root/name)
        assert machine == expected, name
        binaries[name] = hex(machine)
    # All loaded GUI/array/audio/FFI wheels must be target-native. Inventory the
    # entire Python native payload as well, including plugins not yet loaded.
    for path in (root/'python/Lib/site-packages').rglob('*'):
        if path.suffix.lower() in ('.pyd', '.dll'):
            machine = pe_machine(path)
            assert machine == expected, str(path.relative_to(root))
            binaries[path.relative_to(root).as_posix()] = hex(machine)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    report = {'schema': 'augmentor-windows-runtime-proof/1', 'arch': args.arch,
        'os': platform.platform(), 'windowsVersion': list(sys.getwindowsversion()),
        'python': platform.python_version(), 'qt': qVersion(), 'node': node, 'powershell': shell,
        'nativeProcess': True, 'numpyComputation': True, 'onnxImport': True,
        'portAudioLoaded': True, 'qtWidgetRendered': True, 'binaryMachines': binaries,
        'limits': ['No physical audio, D3D flare, consumer install, provider or RTX hardware qualification.']}
    args.out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'binaryMachines'}))


if __name__ == '__main__':
    main()
