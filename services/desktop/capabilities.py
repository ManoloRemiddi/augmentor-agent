#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Read-only backend discovery. Never opens sharing, observes windows or sends input."""
import json
import os
import re
import xml.etree.ElementTree as ET
from session_environment import graphical_environment

PORTAL = 'org.freedesktop.portal.Desktop'
PORTAL_PATH = '/org/freedesktop/portal/desktop'
RD = 'org.freedesktop.portal.RemoteDesktop'
SC = 'org.freedesktop.portal.ScreenCast'


def assess(env, dependencies, interfaces=None, kwin=False):
    """Presence is separate from live permission and successful desktop operation."""
    desktop = env.get('XDG_CURRENT_DESKTOP', '').split(':')
    session = env.get('XDG_SESSION_TYPE', '').lower()
    reason = None
    if session != 'wayland' or 'KDE' not in desktop:
        reason = 'unsupported-session'
    elif not env.get('DISPLAY'):
        reason = 'stop-display-unavailable'
    elif not dependencies:
        reason = 'dependencies-missing'
    elif interfaces is None:
        reason = 'session-interfaces-unavailable'
    elif not kwin:
        reason = 'window-observer-unavailable'
    else:
        remote = interfaces.get(RD, {})
        screen = interfaces.get(SC, {})
        if (remote.get('version', 0) < 1 or remote.get('AvailableDeviceTypes', 0) & 3 != 3
                or screen.get('version', 0) < 1 or screen.get('AvailableSourceTypes', 0) & 1 != 1):
            reason = 'portal-capabilities-incomplete'
    return {'schema': 1, 'available': reason is None,
            'backend': 'kde-wayland-portal' if session == 'wayland' and 'KDE' in desktop else None,
            'reason': reason, 'permission': 'not-requested', 'functionalTested': False}


def dependencies_available():
    try:
        import gi
        gi.require_version('Gst', '1.0')
        gi.require_version('Atspi', '2.0')
        from gi.repository import Gst, Atspi
        from PySide6 import QtCore, QtWidgets
        Gst.init(None)
        return Gst.ElementFactory.find('pipewiresrc') is not None
    except (ImportError, ValueError, RuntimeError):
        return False


def supported_kwin_version(information):
    version = re.search(r"KWin version:\s*(\d+)\.(\d+)\.(\d+)", information)
    return bool(version and int(version[1]) == 6 and tuple(int(v) for v in version.groups()) >= (6, 3, 6))


def interfaces_available():
    from gi.repository import Gio, GLib
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    def call(name, path, interface, method, signature, args):
        return bus.call_sync(name, path, interface, method,
                             GLib.Variant(signature, args) if signature else None, None,
                             Gio.DBusCallFlags.NO_AUTO_START, 500, None).unpack()
    def owner(name):
        return call('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus',
                    'GetNameOwner', '(s)', (name,))[0]
    # Unique owners prevent queries from activating replacement services.
    portal = owner(PORTAL)
    interfaces = {}
    for interface in (RD, SC):
        try:
            values = call(portal, PORTAL_PATH, 'org.freedesktop.DBus.Properties',
                          'GetAll', '(s)', (interface,))[0]
            interfaces[interface] = {key: value for key, value in values.items()
                                     if key in ('version', 'AvailableDeviceTypes', 'AvailableSourceTypes')
                                     and type(value) is int}
        except GLib.Error:
            interfaces[interface] = {}
    try:
        compositor = owner('org.kde.KWin')
        information = call(compositor, '/KWin', 'org.kde.KWin', 'supportInformation', None, ())[0]
        xml = call(compositor, '/Scripting', 'org.freedesktop.DBus.Introspectable',
                   'Introspect', None, ())[0]
        root = ET.fromstring(xml)
        methods = {method.get('name') for interface in root.findall('interface')
                   if interface.get('name') == 'org.kde.kwin.Scripting'
                   for method in interface.findall('method')}
        kwin = supported_kwin_version(information) and {'loadScript', 'unloadScript'}.issubset(methods)
    except (GLib.Error, ET.ParseError):
        kwin = False
    return interfaces, kwin


def report():
    env = graphical_environment()
    os.environ.update({key: value for key, value in env.items() if key in
                       ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'XDG_RUNTIME_DIR',
                        'DBUS_SESSION_BUS_ADDRESS', 'XDG_CURRENT_DESKTOP', 'XDG_SESSION_TYPE')})
    # Avoid D-Bus or dependency queries on unsupported sessions.
    preliminary = assess(env, True)
    if preliminary['reason'] in ('unsupported-session', 'stop-display-unavailable'):
        return preliminary
    dependencies = dependencies_available()
    interfaces, kwin = None, False
    if dependencies:
        try:
            interfaces, kwin = interfaces_available()
        except Exception:
            pass  # Closed/unavailable buses are unavailable, never permission grants.
    return assess(env, dependencies, interfaces, kwin)


if __name__ == '__main__':
    print(json.dumps(report()))
