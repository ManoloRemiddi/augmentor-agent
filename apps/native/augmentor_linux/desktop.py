# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bounded desktop observations. Runs outside the UI thread and model runtime."""
import json
import sys
import time

from doctor import report
from browser import open_url, desktop_environment, refresh_accessibility_bus


def observe(app_pid=None):
    if sys.platform=='darwin':
        from pathlib import Path
        sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'services/desktop'))
        from macos import MacDesktop
        return {'ok':True,**MacDesktop(lambda *_:None).native('observe',**({'appPid':app_pid} if app_pid is not None else {}))}
    refresh_accessibility_bus()
    import gi
    gi.require_version('Atspi', '2.0')
    from gi.repository import Atspi
    Atspi.set_timeout(800, 1500)
    desktop = Atspi.get_desktop(0)
    if desktop is None:
        return {'ok': False, 'error': 'No accessibility desktop is available.'}
    apps = []
    target = None
    deadline = time.monotonic() + 6
    for index in range(min(desktop.get_child_count(), 200)):
        if time.monotonic() > deadline:
            break
        try:
            app = desktop.get_child_at_index(index)
            pid, name = app.get_process_id(), app.get_name()
            apps.append({'pid': pid, 'name': name})
            if app_pid is not None and pid == app_pid:
                target = app
        except Exception:
            continue
    if app_pid is None:
        return {'ok': True, 'applications': apps, 'coverage': 'AT-SPI registered applications only'}
    if target is None:
        return {'ok': False, 'error': 'Application is not accessible; list applications again.'}
    nodes, stack = [], [(target, [], 0)]
    while stack and len(nodes) < 120 and time.monotonic() < deadline:
        node, path, depth = stack.pop()
        try:
            role = node.get_role_name()
            password = node.get_role() == Atspi.Role.PASSWORD_TEXT
            states = node.get_state_set()
            item = {'path': path, 'role': role, 'name': '[password field]' if password else node.get_name()[:300], 'showing': states.contains(Atspi.StateType.SHOWING)}
            nodes.append(item)
            if depth < 8 and not password:
                for i in reversed(range(min(node.get_child_count(), 100))):
                    stack.append((node.get_child_at_index(i), path + [i], depth + 1))
        except Exception:
            continue
    return {'ok': True, 'appPid': app_pid, 'nodes': nodes, 'truncated': bool(stack)}


def dispatch(request):
    if request.get('action') == 'profile':
        try:
            env = desktop_environment()
        except RuntimeError:
            env = None
        return report(environment=env)
    if request.get('action') == 'browser_open':
        return open_url(request.get('url'), request.get('browser', 'chromium'))
    if request.get('action') == 'observe':
        pid = request.get('appPid')
        if pid is not None and (type(pid) not in (int, float) or pid <= 0 or int(pid) != pid):
            raise ValueError('appPid must be a positive integer')
        return observe(pid)
    raise ValueError('Unsupported desktop operation')


if __name__ == '__main__':
    try:
        text = sys.stdin.read(65537)
        if len(text) > 65536:
            raise ValueError('Request too large')
        output = dispatch(json.loads(text))
    except Exception as exc:
        output = {'ok': False, 'error': str(exc)[:500]}
    print(json.dumps(output))
