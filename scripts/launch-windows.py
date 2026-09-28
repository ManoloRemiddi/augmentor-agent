#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Embedded Windows entrypoint for the shared desktop and its private runtimes.

Installer hooks, login registration and update coordination are separate gates.
This entrypoint is also used by the assembled development candidate.
"""
import importlib.util
import argparse
import json
import os
from pathlib import Path
import runpy
import sys
import sysconfig
import traceback

ROOT = Path(__file__).resolve().parents[1]
APP_ID = 'com.augmentor.Agent'
_dll_directories = []  # Retain AddDllDirectory cookies for the process lifetime.


def configure_qt(root=ROOT):
    """Supply explicit private DLL paths under the native launcher's safe search policy.

    PySide adds its Qt DLL directory to PATH, but SetDefaultDllDirectories in
    the embedding launcher deliberately excludes PATH/current-directory lookup.
    Plugins such as SVG need their separately loaded Qt DLLs here as well.
    """
    root = Path(root).resolve()
    site = root/'python/Lib/site-packages'
    paths = [root/'python', site/'PySide6', site/'shiboken6']
    plugins = site/'PySide6/plugins'
    for path in [*paths, plugins]:
        if not path.is_dir() or not path.resolve().is_relative_to(root):
            raise ValueError('The private Qt runtime is incomplete. Repair this installation.')
    handles = []
    try:
        for path in paths: handles.append(os.add_dll_directory(str(path)))
    except BaseException:
        for handle in handles: handle.close()
        raise
    _dll_directories.extend(handles)
    os.environ['QT_PLUGIN_PATH'] = str(plugins)
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(plugins/'platforms')
    from PySide6.QtCore import QCoreApplication
    QCoreApplication.setLibraryPaths([str(plugins)])


def load_launcher():
    spec = importlib.util.spec_from_file_location('windows_component_launcher', ROOT/'scripts/launch-component.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def preflight(root=ROOT):
    release = json.loads((root/'release.json').read_text(encoding='utf-8'))
    target = {'win-amd64': 'windows-x64', 'win-arm64': 'windows-arm64'}.get(sysconfig.get_platform())
    if not target or release.get('target') != target:
        raise ValueError('This Augmentor package does not match its Windows runtime architecture.')
    from augmentor_linux.managed_setup import missing_runtime
    missing = missing_runtime(root, platform='win32')
    if missing: raise ValueError('This copy is incomplete: '+', '.join(missing)+'. Repair the installation.')
    return release


def configure_qualification(root, release):
    """Explicit disposable-data launch; cannot be used by customer artifacts."""
    if release.get('customerDistribution') is not False or release.get('qualificationStatus') != 'development-candidate':
        raise ValueError('Qualification data paths require a development candidate.')
    from platform_adapters.paths import private_directory
    root = private_directory(Path(root).resolve())
    environment = {}
    for variable, name in [('XDG_CONFIG_HOME','config'), ('XDG_DATA_HOME','data'),
                           ('XDG_STATE_HOME','state'), ('XDG_CACHE_HOME','cache'), ('XDG_RUNTIME_DIR','run')]:
        environment[variable] = str(private_directory(root/name))
    environment['AUGMENTOR_SHARED_STATE'] = str(private_directory(root/'run/shared'))
    environment['AUGMENTOR_SHARED_CONFIG'] = str(private_directory(root/'config/shared'))
    environment['AUGMENTOR_SHARED_DATA'] = str(private_directory(root/'data/shared'))
    return environment


def main():
    if sys.platform != 'win32': raise RuntimeError('Use the Augmentor package for this operating system.')
    sys.path[:0] = [str(ROOT/'services'), str(ROOT/'apps/native')]
    configure_qt()
    release = preflight()
    args = list(sys.argv[1:])
    environment = None
    if args[:1] == ['--qualification-root']:
        if len(args) < 2: raise ValueError('A disposable qualification directory is required.')
        environment = configure_qualification(args[1], release)
        args = args[2:]
    launcher = load_launcher(); launcher.configure(windows_paths=environment)
    # Embedded GUI Python has no console streams. Give diagnostics private
    # files and keep credentials/errors out of a public command-line window.
    from platform_adapters.paths import private_directory
    from platform_adapters.private_files import descriptor
    from augmentor_linux.instances import validate_name
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--instance', default='main', type=validate_name)
    instance, _rest = parser.parse_known_args(args)
    log = private_directory(Path(os.environ['XDG_STATE_HOME'])/'logs')/('desktop.'+instance.instance+'.log')
    stream = os.fdopen(descriptor(log, writable=True, create=True), 'a', encoding='utf-8', buffering=1)
    sys.stdout = sys.stderr = stream
    if sys.stdin is None: sys.stdin = open(os.devnull, encoding='utf-8')
    import ctypes
    identity = ctypes.WinDLL('shell32', use_last_error=True).SetCurrentProcessExplicitAppUserModelID
    identity.argtypes = [ctypes.c_wchar_p]; identity.restype = ctypes.c_long
    if identity(APP_ID) < 0: raise RuntimeError('Windows could not set the Augmentor application identity.')
    if '--preview' not in args and '--screenshot' not in args:
        from windows_supervisor import ensure
        ensure(ROOT)
    sys.argv = ['augmentor-desktop', *args]
    runpy.run_module('augmentor_linux', run_name='__main__')


if __name__ == '__main__':
    try: main()
    except Exception:
        if sys.stderr is not None: traceback.print_exc()
        if sys.platform == 'win32':
            import ctypes
            message = ctypes.WinDLL('user32', use_last_error=True).MessageBoxW
            message.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
            message.restype = ctypes.c_int
            message(None, 'Augmentor could not start. Repair this installation and try again. Your conversations and settings have been preserved.',
                    'Augmentor could not start', 0x10)
        raise SystemExit(1)
