# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Small desktop launcher for a household's existing NAS dashboard."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.parse import urlsplit

from PySide6.QtCore import QLockFile, QProcess, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel, QLineEdit,
    QMenu, QMessageBox, QPushButton, QStyle, QSystemTrayIcon, QVBoxLayout)


def config_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))/'augmentor/home-launcher.json'


def validate_url(value):
    value = value.strip()
    parsed = urlsplit(value)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or any(c.isspace() for c in value)
            or any(ord(c) < 32 for c in value)):
        raise ValueError('Enter an http:// or https:// dashboard address, without a key, password or query string.')
    try:
        parsed.port
    except ValueError as error:
        raise ValueError('The dashboard address has an invalid port.') from error
    return value


def load_url(path=None):
    path = path or config_path()
    if not path.exists():
        return ''
    return validate_url(json.loads(path.read_text())['url'])


def save_url(value, path=None):
    value = validate_url(value)
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix='.home-launcher-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump({'url': value}, stream)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def browser_command(url, finder=shutil.which):
    url = validate_url(url)
    for name in ('chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable', 'microsoft-edge'):
        if executable := finder(name):
            return executable, ['--app='+url, '--class=AugmentorHome']
    return None


class HomeTray:
    def __init__(self, app, opener=None):
        self.app = app
        self.opener = opener or self.launch_dashboard
        self.dialog = None
        icon = QIcon.fromTheme('go-home')
        if icon.isNull():
            icon = app.style().standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon)
        self.tray = QSystemTrayIcon(icon, app)
        self.tray.setToolTip('Augmentor Home — open your home dashboard')
        self.menu = QMenu()
        self.open_action = QAction('Open Home', self.menu)
        self.open_action.triggered.connect(self.open_home)
        self.menu.addAction(self.open_action)
        self.settings_action = QAction('Connection settings…', self.menu)
        self.settings_action.triggered.connect(self.show_settings)
        self.menu.addAction(self.settings_action)
        self.menu.addSeparator()
        quit_action = QAction('Quit launcher', self.menu)
        quit_action.triggered.connect(app.quit)
        self.menu.addAction(quit_action)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.activated)
        self.tray.show()

    def activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.open_home()

    def launch_dashboard(self, url):
        command = browser_command(url)
        if command:
            ok, _ = QProcess.startDetached(*command)
        else:
            ok = QDesktopServices.openUrl(QUrl(url))
        if not ok:
            raise RuntimeError('Could not open your browser. Check that a browser is installed.')

    def open_home(self):
        try:
            url = load_url()
            if not url:
                self.show_settings(); return
            self.opener(url)
        except Exception as error:
            QMessageBox.warning(self.dialog, 'Augmentor Home', str(error))
            self.show_settings()

    def show_settings(self):
        if self.dialog is not None:
            self.dialog.show(); self.dialog.raise_(); self.dialog.activateWindow(); return
        dialog = QDialog()
        dialog.setWindowTitle('Augmentor Home — connection')
        dialog.setMinimumWidth(460)
        layout = QVBoxLayout(dialog)
        note = QLabel('Open the dashboard hosted by your NAS. Use your usual Home Assistant login in the browser; no API key or pairing code is needed here.')
        note.setWordWrap(True); layout.addWidget(note)
        layout.addWidget(QLabel('Dashboard address'))
        field = QLineEdit(); field.setAccessibleName('Dashboard address')
        field.setPlaceholderText('http://your-nas:8123/home-lighting/lights')
        try:
            field.setText(load_url())
        except (ValueError, KeyError, OSError):
            pass
        layout.addWidget(field)
        status = QLabel(); status.setWordWrap(True); layout.addWidget(status)
        buttons = QHBoxLayout(); layout.addLayout(buttons)
        save = QPushButton('Save and open'); buttons.addWidget(save)
        close = QPushButton('Close'); close.clicked.connect(dialog.close); buttons.addWidget(close)
        def accept():
            try:
                save_url(field.text())
            except (ValueError, OSError) as error:
                status.setText(str(error)); return
            dialog.close(); self.open_home()
        save.clicked.connect(accept)
        dialog.finished.connect(lambda _: setattr(self, 'dialog', None))
        self.dialog = dialog
        dialog.show(); dialog.raise_(); dialog.activateWindow()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--background', action='store_true', help='Start tray without opening dashboard')
    parser.add_argument('--settings', action='store_true')
    args = parser.parse_args(argv)
    app = QApplication([sys.argv[0]])
    app.setApplicationName('Augmentor Home'); app.setQuitOnLastWindowClosed(False)
    identity = hashlib.sha256(str(config_path().absolute()).encode()).hexdigest()[:16]
    socket_name = 'augmentor-home-'+str(os.getuid())+'-'+identity
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', tempfile.gettempdir()))
    lock = QLockFile(str(runtime/(socket_name+'.lock')))
    # Only the lock holder may remove a stale socket.
    if not lock.tryLock(0):
        if args.background:
            return 0
        client = QLocalSocket(); client.connectToServer(socket_name)
        if not client.waitForConnected(3000):
            print('Home launcher is starting; try again shortly.', file=sys.stderr); return 1
        client.write(b'settings\n' if args.settings else b'open\n')
        client.waitForBytesWritten(1000); client.disconnectFromServer(); return 0
    QLocalServer.removeServer(socket_name)
    server = QLocalServer(); server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    if not server.listen(socket_name):
        print('Could not start Home launcher: '+server.errorString(), file=sys.stderr); return 1
    tray = HomeTray(app)
    clients = set()
    def connect_client():
        client = server.nextPendingConnection(); clients.add(client)
        def read():
            if not client.canReadLine():
                return
            command = bytes(client.readLine(64)).strip()
            if command == b'open':
                tray.open_home()
            elif command == b'settings':
                tray.show_settings()
            client.disconnectFromServer()
        def dispose():
            clients.discard(client); client.deleteLater()
        client.readyRead.connect(read); client.disconnected.connect(dispose)
        read()
    server.newConnection.connect(connect_client)
    def initial():
        if args.settings:
            tray.show_settings()
        elif not args.background:
            tray.open_home()
    QTimer.singleShot(0, initial)
    def no_tray_fallback():
        if not QSystemTrayIcon.isSystemTrayAvailable():
            tray.show_settings()
    QTimer.singleShot(10000, no_tray_fallback)
    result = app.exec()
    server.close(); lock.unlock()
    return result


if __name__ == '__main__':
    raise SystemExit(main())
