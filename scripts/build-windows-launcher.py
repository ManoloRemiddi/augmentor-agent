#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Compile the native private-Python launcher for a staged Windows payload."""
import argparse
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def product_resources(directory, version, arch):
    """Render the approved vector at native icon sizes and embed shell metadata."""
    if not re.fullmatch(r'\d+\.\d+\.\d+', version): raise ValueError('Use the shared numeric product version.')
    numbers = [*map(int, version.split('.')), 0]
    if any(value > 65535 for value in numbers): raise ValueError('Product version exceeds the Windows resource range.')
    from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt
    from PySide6.QtGui import QGuiApplication, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    app = QGuiApplication.instance() or QGuiApplication(['augmentor-resource-builder', '-platform', 'offscreen'])
    renderer = QSvgRenderer(str(ROOT/'apps/native/augmentor_linux/assets/augmentor.svg'))
    if not renderer.isValid(): raise ValueError('The shared Augmentor icon is invalid.')
    frames = []
    for size in (16, 24, 32, 48, 64, 128, 256):
        image = QImage(size, size, QImage.Format.Format_ARGB32); image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image); renderer.render(painter); painter.end()
        data = QByteArray(); stream = QBuffer(data); stream.open(QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(stream, 'PNG'): raise ValueError('Could not render the application icon.')
        frames.append((size, bytes(data)))
    offset = 6 + 16*len(frames)
    icon = bytearray(struct.pack('<HHH', 0, 1, len(frames)))
    for size, data in frames:
        icon.extend(struct.pack('<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    for _size, data in frames: icon.extend(data)
    directory = Path(directory)
    (directory/'augmentor.ico').write_bytes(icon)
    manifest = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity name="com.augmentor.Agent" version="{version}.0" type="win32" processorArchitecture="{'amd64' if arch == 'x64' else 'arm64'}"/>
  <description>Augmentor Agent</description>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3"><security><requestedPrivileges>
    <requestedExecutionLevel level="asInvoker" uiAccess="false"/>
  </requestedPrivileges></security></trustInfo>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1"><application>
    <supportedOS Id="{{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}}"/>
  </application></compatibility>
  <application xmlns="urn:schemas-microsoft-com:asm.v3"><windowsSettings>
    <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2,PerMonitor</dpiAwareness>
    <longPathAware xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">true</longPathAware>
  </windowsSettings></application>
</assembly>
'''
    (directory/'augmentor.manifest').write_text(manifest, encoding='utf-8')
    rc_path = lambda name: str(directory/name).replace('\\', '\\\\')
    rc = f'''// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
#pragma code_page(65001)
#include <windows.h>
101 ICON "{rc_path('augmentor.ico')}"
1 RT_MANIFEST "{rc_path('augmentor.manifest')}"
1 VERSIONINFO
 FILEVERSION {','.join(map(str,numbers))}
 PRODUCTVERSION {','.join(map(str,numbers))}
 FILEFLAGSMASK 0x3fL
 FILEFLAGS 0x0L
 FILEOS VOS_NT_WINDOWS32
 FILETYPE VFT_APP
 FILESUBTYPE 0x0L
BEGIN
  BLOCK "StringFileInfo"
  BEGIN
    BLOCK "040904b0"
    BEGIN
      VALUE "CompanyName", "Augmentor"
      VALUE "FileDescription", "Augmentor Agent"
      VALUE "FileVersion", "{version}"
      VALUE "InternalName", "Augmentor"
      VALUE "OriginalFilename", "Augmentor.exe"
      VALUE "ProductName", "Augmentor Agent"
      VALUE "ProductVersion", "{version}"
      VALUE "LegalCopyright", "Copyright © 2026 Manolo Remiddi"
    END
  END
  BLOCK "VarFileInfo"
  BEGIN
    VALUE "Translation", 0x409, 1200
  END
END
'''
    (directory/'augmentor.rc').write_text(rc, encoding='utf-8')
    return directory/'augmentor.rc'


def build_launcher(payload, arch, *, name='Augmentor.exe'):
    if sys.platform != 'win32' or arch not in ('x64','arm64') or name not in ('Augmentor.exe','AugmentorFixture.exe','AugmentorBrowserHost.exe'):
        raise ValueError('Use a supported Windows launcher identity and architecture.')
    payload = Path(payload).resolve()
    vswhere = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)'))/'Microsoft Visual Studio/Installer/vswhere.exe'
    install = subprocess.check_output([str(vswhere), '-latest', '-products', '*', '-property', 'installationPath'], text=True).strip()
    if not install:
        raise RuntimeError('Windows build tools are missing')
    vcvars = Path(install)/'VC/Auxiliary/Build/vcvarsall.bat'
    # Build paths originate in this controlled checkout. Do not accept shell
    # metacharacters: vcvarsall is the vendor's batch environment initializer.
    values = (str(vcvars), str(payload), str(ROOT))
    if any(any(c in value for c in '&|<>^%!\r\n') for value in values):
        raise ValueError('Unsupported shell character in the build path')
    include = payload/'python/include'
    if not (include/'Python.h').is_file():
        raise RuntimeError('Standalone Python must include its matching C headers')
    with tempfile.TemporaryDirectory(prefix='launcher-build-', dir=payload) as temporary:
        resources = Path(temporary)
        definitions = ''
        if name != 'AugmentorFixture.exe':
            release = json.loads((payload/'release.json').read_text(encoding='utf-8'))
            definitions = '/DAUGMENTOR_LIFETIME_LEASE '
            if release.get('customerDistribution') is False and release.get('qualificationStatus') == 'development-candidate':
                definitions += '/DAUGMENTOR_DEVELOPMENT_CANDIDATE '
        compile_resource = resource_input = manifest_option = ''
        if name == 'Augmentor.exe':
            version = json.loads((payload/'release.json').read_text(encoding='utf-8'))['version']
            rc = product_resources(resources, version, arch)
            res = resources/'augmentor.res'
            compile_resource = f'rc /nologo /fo"{res}" "{rc}" && '
            resource_input = f'"{res}" '
            manifest_option = '/MANIFEST:NO '
        command = (f'call "{vcvars}" {"amd64_arm64" if arch == "arm64" else "amd64"} && '
            +compile_resource+
            'cl /nologo /O2 /W4 /MT '+definitions+('/DAUGMENTOR_BROWSER_HOST ' if name == 'AugmentorBrowserHost.exe' else '')+
            f'/I"{include}" "{ROOT / "services/platform/windows-launcher.c"}" '
            f'/Fe:"{payload / name}" /Fo:"{payload / "launcher.obj"}" '+resource_input+
            '/link /SUBSYSTEM:WINDOWS '+manifest_option+'user32.lib shell32.lib advapi32.lib')
        # list2cmdline would backslash-escape embedded quotes, which cmd.exe does
        # not understand. This is an explicitly constructed, validated shell line.
        subprocess.run('cmd.exe /d /s /c "'+command+'"', check=True)
    (payload/'launcher.obj').unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--arch', choices=('x64','arm64'), required=True)
    args = parser.parse_args()
    build_launcher(args.root, args.arch)
    build_launcher(args.root, args.arch, name='AugmentorBrowserHost.exe')
