#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real KWin/UInput mouse drags against an isolated native preview, without model calls."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def ui(directory):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from augmentor_linux.window import Window
    app = QApplication([])
    window = Window(preview=True)
    window.setWindowTitle('Augmentor resize verification')
    window.preferences.values['pinned'] = False
    window.messages = [('You', 'Keep this conversation while resizing.'), ('Augmentor', 'The answer and draft remain intact.\n' * 25)]
    window.render_messages()
    window.composer.setPlainText('Unsent resize verification draft')
    window.show()
    window.setGeometry(500, 1260, 420, 460)
    processed = None

    def tick():
        nonlocal processed
        command_path = directory / 'command.json'
        if command_path.exists():
            command = json.loads(command_path.read_text())
            if command['id'] != processed:
                processed = command['id']
                action = command['action']
                if action == 'reset': window.setGeometry(500, 1260, 420, 460)
                elif action == 'toggle': window.toggle_compact()
                elif action == 'hide-show': window.hide(); window.bring_forward()
                elif action == 'capture': window.grab().save(str(directory / 'resized.png'))
                elif action == 'close': window.close(); return
        data = {'id': processed, 'geometry': list(window.geometry().getRect()), 'compact': window.compact,
                'draft': window.composer.toPlainText(), 'answerPresent': 'The answer and draft remain intact.' in window.transcript.toPlainText(),
                'handlesVisible': sum(h.isVisible() for h in window.resize_borders.handles)}
        temporary = directory / 'state.tmp'
        temporary.write_text(json.dumps(data)); temporary.replace(directory / 'state.json')
    timer = QTimer(); timer.timeout.connect(tick); timer.start(50)
    app.exec()


def proof(directory):
    import inspect
    from evdev import UInput, ecodes as e
    from gi.repository import Gio
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/desktop'))
    import kwin
    # Include the compositor pointer position for scaled, closed-loop movement.
    source = '\n'.join(line[4:] if line.startswith('    ') else line for line in inspect.getsource(kwin.KWin.read).splitlines())
    source = source.replace('screens:workspace.screens', 'cursor:workspace.cursorPos,screens:workspace.screens')
    exec(source, kwin.__dict__); kwin.KWin.read = kwin.read
    compositor = kwin.KWin(Gio.bus_get_sync(Gio.BusType.SESSION, None))
    child = subprocess.Popen([sys.executable, __file__, '--ui', str(directory)])
    def state(): return json.loads((directory / 'state.json').read_text())
    def command(action):
        ident = time.monotonic_ns()
        temporary = directory / 'command.tmp'; temporary.write_text(json.dumps({'id': ident, 'action': action}))
        temporary.replace(directory / 'command.json')
        if action == 'close': return
        for _ in range(100):
            time.sleep(.05)
            if state()['id'] == ident: break
        else: raise RuntimeError('Preview did not acknowledge command')
        time.sleep(.25)
        return state()
    try:
        for _ in range(100):
            if (directory / 'state.json').exists(): break
            if child.poll() is not None: raise RuntimeError('Preview failed to start')
            time.sleep(.1)
        time.sleep(.4)
        with UInput({e.EV_KEY: [e.BTN_LEFT], e.EV_REL: [e.REL_X, e.REL_Y]}, name='Augmentor resize verification') as pointer:
            time.sleep(.4)
            def move(x, y):
                for _ in range(150):
                    observation = compositor.read()
                    assert observation['window']['title'] == 'Augmentor resize verification', 'Focus changed; mouse test stopped'
                    current = observation['cursor']; dx, dy = x-current['x'], y-current['y']
                    if abs(dx) <= 1 and abs(dy) <= 1: return
                    def step(delta): return 0 if abs(delta) <= 1 else (1 if delta > 0 else -1)*max(1, min(40, int(abs(delta)/3)))
                    pointer.write(e.EV_REL, e.REL_X, step(dx)); pointer.write(e.EV_REL, e.REL_Y, step(dy)); pointer.syn(); time.sleep(.025)
                raise RuntimeError(f'Pointer could not reach {x}, {y}; current {current}')
            records = []
            for name, horizontal, vertical in [('right',1,0),('left',-1,0),('bottom',0,1),('top',0,-1),('top-left',-1,-1),('top-right',1,-1),('bottom-left',-1,1),('bottom-right',1,1)]:
                before = command('reset')
                g = compositor.read()['window']['geometry']; x,y,w,h = (g[k] for k in ('x','y','width','height'))
                inset = 5 if horizontal and vertical else 3
                start_x = x + (inset if horizontal < 0 else w-inset if horizontal > 0 else w/2)
                start_y = y + (inset if vertical < 0 else h-inset if vertical > 0 else h/2)
                move(start_x, start_y)
                pointer.write(e.EV_KEY,e.BTN_LEFT,1);pointer.syn();time.sleep(.12)
                try: move(start_x + horizontal*65, start_y + vertical*55)
                finally: pointer.write(e.EV_KEY,e.BTN_LEFT,0);pointer.syn()
                time.sleep(.3); after = state()
                dw = after['geometry'][2]-before['geometry'][2]; dh = after['geometry'][3]-before['geometry'][3]
                assert (dw > 20 if horizontal else abs(dw) <= 2), (name,before,after)
                assert (dh > 20 if vertical else abs(dh) <= 2), (name,before,after)
                assert after['draft'] == before['draft'] and after['answerPresent']
                records.append({'handle':name,'before':before['geometry'],'after':after['geometry']})
                print(name, 'passed', flush=True)
            expanded = state()['geometry']
            assert command('hide-show')['geometry'] == expanded
            compact = command('toggle'); assert compact['handlesVisible'] == 0 and compact['geometry'][2:] == [208,208]
            restored = command('toggle'); assert restored['geometry'][2:] == expanded[2:] and restored['handlesVisible'] == 8
            command('capture')
            (directory/'proof.json').write_text(json.dumps({'realMouseDrags':records,'hideShowPreservesGeometry':True,'compactRestoresSize':True,'draftAndAnswerPreserved':True},indent=2)+'\n')
    finally:
        command('close')
        try: child.wait(timeout=5)
        except subprocess.TimeoutExpired: child.terminate(); child.wait(timeout=5)


if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--ui': ui(Path(sys.argv[2]))
    else:
        directory = Path(sys.argv[1]) if len(sys.argv)>1 else Path(tempfile.mkdtemp(prefix='augmentor-resize-'))
        directory.mkdir(parents=True, exist_ok=True)
        for name in ('command.json', 'state.json'): (directory/name).unlink(missing_ok=True)
        proof(directory)
        print(directory / 'proof.json')
