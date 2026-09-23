#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Per-user desktop executor with an independent, always-visible Stop control."""
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import socket
import socketserver
import struct
import sys
import threading
import time
from PySide6.QtCore import Qt,Signal,QTimer
from PySide6.QtWidgets import QApplication,QWidget,QHBoxLayout,QLabel,QPushButton
if sys.platform=='darwin':
    from macos import MacDesktop as Backend
else:
    from gi.repository import GLib
    from portal import Portal as Backend
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'services'))
from platform_support import require_same_user
sys.path.insert(0,str(ROOT/'services/lifecycle'))
from lease import hold


def endpoint():return Path(os.environ.get('XDG_RUNTIME_DIR',f'/tmp/augmentor-{os.getuid()}' if sys.platform=='darwin' else f'/run/user/{os.getuid()}'))/'augmentor-desktop.sock'


def schedule(work):
    # macOS native work uses bounded child processes. Keep the Qt main thread
    # responsive to independent Stop while a permission/capture request waits.
    if sys.platform=='darwin':threading.Thread(target=work,daemon=True).start()
    else:GLib.idle_add(work)


class Banner(QWidget):
    update=Signal(bool,str)
    def __init__(self):
        super().__init__(None,Qt.WindowType.Tool|Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating);self.setWindowTitle('Augmentor desktop control')
        self.setStyleSheet('QWidget {background:#283638;color:#f0f4f4;} QPushButton {background:#703b3b;color:white;padding:8px;border-radius:6px;}')
        row=QHBoxLayout(self);self.label=QLabel();row.addWidget(self.label);self.stop=QPushButton('Stop desktop control');row.addWidget(self.stop)
        self.update.connect(self.changed)
    def changed(self,active,message):
        self.label.setText(message)
        if active:
            self.adjustSize();area=QApplication.primaryScreen().availableGeometry();self.move(area.right()-self.width()-12,area.top()+12);self.show()
        else:self.hide()
    def closeEvent(self,event):self.stop.click();event.ignore()


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(120)
        try:
            require_same_user(self.connection)
            raw=self.rfile.readline(32769)
            if len(raw)>32768 or not raw.endswith(b'\n'):raise RuntimeError('Invalid desktop request.')
            request=json.loads(raw)
            if request.get('protocol')!='augmentor-desktop/1':raise RuntimeError('Incompatible desktop executor.')
            method=request.get('method');owner=request.get('owner')
            if method not in ('status','shutdown') and (not isinstance(owner,str) or not re.fullmatch(r'(pi|dsh):[A-Za-z0-9_.:-]{1,180}',owner)):raise RuntimeError('A harness conversation must own desktop control.')
            backend=self.server.backend
            if method=='status':result=backend.status()
            else:
                if method=='stop':
                    if backend.owner not in (None,owner):raise RuntimeError('This chat does not own desktop control.')
                    backend.generation+=1;backend.cancel.set()
                elif method=='shutdown':
                    if backend.owner or backend.busy.locked():raise RuntimeError('Desktop control is active; stop it before maintenance.')
                elif not backend.busy.acquire(False):raise RuntimeError('A desktop operation is already running.')
                if method=='connect' and not backend.owner:backend.cancel.clear()
                generation=backend.generation;completed=threading.Event();response={}
                def work():
                    try:
                        if method not in ('stop','shutdown') and generation!=backend.generation:raise RuntimeError('Desktop action cancelled before execution.')
                        if method=='connect':result=backend.connect(owner)
                        elif method=='capture':result=backend.capture(owner)
                        elif method=='action':result=backend.action(owner,request.get('params',{}))
                        elif method=='stop':result=backend.stop()
                        elif method=='shutdown':result={'accepted':True};self.server.banner.update.emit(False,'');self.server.quit.quit.emit()
                        else:raise RuntimeError('Unsupported desktop operation.')
                        response['result']=result
                    except Exception as exc:response['error']=str(exc)[:600]
                    finally:
                        if method not in ('stop','shutdown'):backend.busy.release()
                        completed.set()
                    return False
                schedule(work)
                if not completed.wait(110):backend.cancel.set();raise RuntimeError('Desktop request timed out. Inspect the application before continuing.')
                if 'error' in response:raise RuntimeError(response['error'])
                result=response['result']
            response={'ok':True,'result':result}
        except Exception as exc:response={'ok':False,'error':str(exc)[:600]}
        try:self.wfile.write((json.dumps(response)+'\n').encode())
        except (BrokenPipeError,ConnectionResetError):pass


class Server(socketserver.ThreadingUnixStreamServer):daemon_threads=True
class ExitSignal(QWidget):quit=Signal()


def main():
    hold('desktop');os.umask(0o077);path=endpoint();path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    lock=path.with_suffix('.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    path.unlink(missing_ok=True);app=QApplication([]);app.setQuitOnLastWindowClosed(False);banner=Banner();backend=Backend(banner.update.emit)
    server=Server(str(path),Handler);server.backend=backend;server.banner=banner;server.quit=ExitSignal();server.quit.quit.connect(app.quit)
    def stop_requested():
        backend.generation+=1;backend.cancel.set();schedule(lambda:(backend.stop(),False)[1])
    banner.stop.clicked.connect(stop_requested)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    # Inactivity closes sharing, leaving no indefinitely authorized input session.
    def idle():
        if sys.platform!='darwin':
            while GLib.MainContext.default().pending():GLib.MainContext.default().iteration(False)
        if backend.owner and not backend.busy.locked() and time.monotonic()-backend.last_used>300:
            backend.cancel.set();schedule(lambda:(backend.stop(),False)[1])
    timer=QTimer();timer.timeout.connect(idle);timer.start(100)
    signal.signal(signal.SIGTERM,lambda *_:app.quit());signal.signal(signal.SIGINT,lambda *_:app.quit())
    try:app.exec()
    finally:
        backend.stop();server.shutdown();server.server_close();path.unlink(missing_ok=True)


if __name__=='__main__':main()
