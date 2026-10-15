#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Negative checks against the actual built native adapter's sandbox command."""
from pathlib import Path
import importlib.util
import json
import os
import socket
import sys

source = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('native_office', source / 'dist/runtime/src/office-native-linux.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
root = Path(sys.argv[1]).absolute()
sentinel = root / 'outside-authored-sentinel'
sentinel.write_text('AUTHORED_OUTSIDE_FILE')
input_path = root / 'authored-readonly.docx'
input_path.write_text('AUTHORED_READONLY_INPUT')
box = root / 'owned-box'
box.mkdir(mode=0o700)
fonts = '/usr/share/fonts/truetype/liberation2'
if not Path(fonts).is_dir():
    fonts = '/usr/share/fonts/truetype/liberation'
options = {'fontDirectories': [fonts], 'fontFallbacks': [], 'maxFontFiles': 100, 'maxFontFileBytes': 256 * 1024**2, 'maxLoadedFontBytes': 512 * 1024**2, 'maxOutputBytes': 20 * 1024**2, 'timeoutMs': 10_000}
adapter.snapshot_fonts(box, options)
adapter.profile(box, options)
output = root / 'descriptor-output.pdf'
output_fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
parent_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
assert (output_fd, parent_fd) == (3, 4)
os.write(output_fd, b'AUTHORED_OUTPUT_DESCRIPTOR')
listener = socket.socket()
listener.bind(('127.0.0.1', 0))
listener.listen(1)
try:
    cmd = adapter.command(box, input_path)
    # Test-only Python reads the same namespace boundaries as the renderer.
    # No home, extra writable path, environment or network is added.
    for path in ('/usr/bin/python3.13', '/usr/lib/python3.13'):
        cmd += ['--ro-bind', path, path]
    script = f'''import json,os,socket
from pathlib import Path
values={{'outsideFileAbsent':not Path({str(sentinel)!r}).exists(),'hostProcessEnvironmentAbsent':not Path('/proc/{os.getpid()}/environ').exists(),'hostEnvironmentAbsent':'AUTHORED_NATIVE_ENV_SENTINEL' not in os.environ,'ownerHomeAbsent':not Path({str(Path.home())!r}).exists()}}
extra=[]
for value in os.listdir('/proc/self/fd'):
 try:
  if int(value)>2:extra.append(os.readlink('/proc/self/fd/'+value))
 except FileNotFoundError:pass
values['admissionAndStatusDescriptorsClosedBeforeParser']=not extra
values['outputAndParentDescriptorsClosedBeforeParser']=not extra
try:socket.create_connection(('127.0.0.1',{listener.getsockname()[1]}),timeout=1).close();values['hostLoopbackDenied']=False
except OSError:values['hostLoopbackDenied']=True
for key,path in [('inputReadOnly','/input/source.docx'),('systemReadOnly','/usr/lib/libreoffice/program/bootstraprc')]:
 try:Path(path).write_text('AUTHORED_MUTATION');values[key]=False
 except OSError:values[key]=True
print(json.dumps(values));assert all(values.values())
'''
    os.environ['AUTHORED_NATIVE_ENV_SENTINEL'] = 'AUTHORED_NOT_REAL'
    result = json.loads(adapter.run(cmd + ['/usr/bin/python3.13', '-I', '-c', script], box, options, catalog=True))
    assert sentinel.read_text() == 'AUTHORED_OUTSIDE_FILE' and input_path.read_text() == 'AUTHORED_READONLY_INPUT'
    assert output.read_text() == 'AUTHORED_OUTPUT_DESCRIPTOR'
    profile = (box / 'work/profile/user/registrymodifications.xcu').read_text()
    assert 'DisableMacrosExecution' in profile and 'DisableActiveContent' in profile
    print(json.dumps(result))
finally:
    listener.close()
    os.close(output_fd)
    os.close(parent_fd)
