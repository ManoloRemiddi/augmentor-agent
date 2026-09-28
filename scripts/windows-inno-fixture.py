#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Disposable installed program and native WinSparkle probe, not product code."""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]


def publish_result(destination, result):
    """Publish closed fixture observations, never half-written JSON."""
    destination = Path(destination)
    pending = destination.with_name(destination.name+'.pending')
    with pending.open('w', encoding='utf-8') as stream:
        json.dump(result, stream)
        stream.flush(); os.fsync(stream.fileno())
    os.replace(pending, destination)


def dismiss_fixture_windows():
    """Dismiss this test process's updater UI, including its busy-work warning.

    WinSparkle correctly shows a modal warning when can_shutdown refuses. Its
    cleanup waits for that dialog; hosted tests must exercise the dismissal.
    Never enumerate/close windows belonging to another process.
    """
    import os
    user = ctypes.WinDLL('user32', use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    user.EnumWindows.argtypes = [callback_type,wintypes.LPARAM]; user.EnumWindows.restype = wintypes.BOOL
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowThreadProcessId.restype = wintypes.DWORD
    user.PostMessageW.argtypes = [wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    user.PostMessageW.restype = wintypes.BOOL
    def close(window,_context):
        pid = wintypes.DWORD(); user.GetWindowThreadProcessId(window,ctypes.byref(pid))
        if pid.value == os.getpid(): user.PostMessageW(window,0x0010,0,0)  # WM_CLOSE
        return True
    callback = callback_type(close)
    for _ in range(10):
        user.EnumWindows(callback,0); time.sleep(.1)


def shared_gate(config):
    create = ctypes.WinDLL('kernel32', use_last_error=True).CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                       wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    handle = create(config['gate'], 0xc0000000, 3, None, 4, 0x80, None)
    if handle == ctypes.c_void_p(-1).value: raise ctypes.WinError(ctypes.get_last_error())
    return handle


def sparkle(settings):
    dll = ctypes.CDLL(settings.get('dllPath', str(ROOT/'WinSparkle.dll')))
    callbacks = []
    done = threading.Event()
    result = {'events': [], 'downloadHandled': False, 'canShutdown': None}
    def function(name, args=(), returns=None):
        value = getattr(dll, 'win_sparkle_'+name)
        value.argtypes = list(args); value.restype = returns
        return value
    def event(name):
        result['events'].append(name)
        if name in ('error', 'no-update'): done.set()
    void_callback = ctypes.CFUNCTYPE(None)
    for api, name in [('error', 'error'), ('did_find_update', 'found'), ('did_not_find_update', 'no-update')]:
        callback = void_callback(lambda name=name: event(name)); callbacks.append(callback)
        function('set_'+api+'_callback', [void_callback])(callback)
    def can_shutdown():
        result['canShutdown'] = not settings['busy']
        if settings['busy']: done.set()
        return int(not settings['busy'])
    can_callback = ctypes.CFUNCTYPE(ctypes.c_int)(can_shutdown); callbacks.append(can_callback)
    function('set_can_shutdown_callback', [type(can_callback)])(can_callback)
    def handled(path):
        try:
            result['downloadSha256'] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            if 'bundlePolicy' in settings:
                sys.path.insert(0, str(ROOT/'services'))
                from lifecycle.release_bundle import stage_bundle
                with stage_bundle(path, settings['cache'], **settings['bundlePolicy']) as release:
                    result['verifiedRelease'] = release.identity
                    result['retainedInstallerSha256'] = hashlib.sha256(release.installer.read_bytes()).hexdigest()
            result['downloadHandled'] = True
            return 1  # Qualification inspects the verified download; never executes a second installer here.
        except Exception:
            result['callbackFailed'] = True
            return -1
        finally: done.set()
    run_callback = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_wchar_p)(handled); callbacks.append(run_callback)
    function('set_user_run_installer_callback', [type(run_callback)])(run_callback)
    function('set_app_details', [ctypes.c_wchar_p]*3)('Augmentor qualification', settings['id'], '0.0.1')
    function('set_registry_path', [ctypes.c_char_p])(settings['registry'].encode('ascii'))
    function('set_appcast_url', [ctypes.c_char_p])(settings['url'].encode('ascii'))
    assert function('set_eddsa_public_key', [ctypes.c_char_p], ctypes.c_int)(settings['key'].encode('ascii'))
    function('set_automatic_check_for_updates', [ctypes.c_int])(0)
    function('init')()
    try:
        function('check_update_with_ui_and_install')()
        if not done.wait(45): raise TimeoutError('No native updater result.')
        time.sleep(.3)  # Let the native callback return before cleanup joins its UI thread.
    finally:
        publish_result(settings['progress'], result)
        dismiss_fixture_windows()
        function('cleanup')()
    return result


def main():
    action, destination, *arguments = sys.argv[1:]
    if action == '--signed-bundle':
        # Run under the original native runtime, including real private-file
        # adapters. The minimal installed fixture intentionally omits pywin32.
        result = sparkle(json.loads(Path(arguments[0]).read_text(encoding='utf-8')))
        publish_result(destination, result)
        return
    config = json.loads((ROOT/'fixture.json').read_text(encoding='utf-8'))
    result = {'version': config['version'], 'pid': __import__('os').getpid(),
              'runtime': sys.executable, 'scope': 'Disposable fixture only'}
    if action == '--hold':
        handle = shared_gate(config)
        publish_result(destination, result)
        try:
            end = time.monotonic()+180
            while not Path(arguments[0]).exists() and time.monotonic() < end: time.sleep(.05)
        finally:
            close = ctypes.WinDLL('kernel32', use_last_error=True).CloseHandle
            close.argtypes = [wintypes.HANDLE]; close.restype = wintypes.BOOL
            close(handle)
        return
    if action == '--sparkle': result.update(sparkle(json.loads(Path(arguments[0]).read_text())))
    elif action != '--inspect': raise ValueError('Unknown fixture action')
    publish_result(destination, result)


if __name__ == '__main__':
    main()
