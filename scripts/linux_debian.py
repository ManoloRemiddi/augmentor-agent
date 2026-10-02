# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Explicit system dependency recipes for Debian-format Linux artifacts."""
from linux_distribution import NOBLE

TARGETS=('debian13-amd64','ubuntu26.04-amd64',NOBLE)
HANDY_DEPENDENCIES = [
    'python3-gi', 'debianutils', 'udev', 'kmod', 'libgtk-3-0t64', 'libwebkit2gtk-4.1-0',
    'libayatana-appindicator3-1', 'libgtk-layer-shell0', 'libopenblas0',
    'libvulkan1', 'libasound2t64', 'libasound2-plugins', 'libxdo3',
    'wl-clipboard', 'xdotool', 'xwayland',
]
NOBLE_DEPENDENCIES=[
    'python3 (>= 3.12)', 'python3.12-venv', 'python3-gi', 'python3-gi-cairo',
    'python3-packaging', 'python3-secretstorage', 'python3-jeepney', 'python3-cryptography',
    'python3-jaraco.classes', 'python3-jaraco.context', 'python3-jaraco.functools',
    'python3-more-itertools', 'python3-cffi', 'python3-cffi-backend',
    'python3-numpy (>= 1.24)', 'python3-flatbuffers', 'python3-yaml', 'python3-websocket',
    'gnome-keyring', 'gir1.2-gtk-4.0', 'gir1.2-atspi-2.0', 'gir1.2-gstreamer-1.0',
    'at-spi2-core', 'gstreamer1.0-plugins-base', 'gstreamer1.0-pipewire',
    'libportaudio2', 'libgl1', 'libegl1', 'libopengl0', 'libglib2.0-0t64',
    'libxcb-cursor0', 'libxcb-icccm4', 'libxcb-image0', 'libxcb-keysyms1',
    'libxcb-render-util0', 'libxcb-shape0', 'libxcb-xinerama0', 'libxcb-xkb1',
    'libxkbcommon-x11-0', 'libx11-xcb1', 'fonts-dejavu-core', 'libc6 (>= 2.39)', 'libstdc++6',
]
NOBLE_SOURCE_QT_DEPENDENCIES = [
    'libicu74', 'libdouble-conversion3', 'libfontconfig1', 'libfreetype6',
    'libharfbuzz0b', 'libpcre2-16-0', 'libjpeg-turbo8', 'libpng16-16t64',
    'libtiff6', 'libwebp7', 'libwebpdemux2', 'libwebpmux3', 'libssl3t64',
    'libdbus-1-3', 'libbrotli1', 'libwayland-client0', 'libwayland-cursor0',
    'libwayland-egl1', 'libxcb-glx0', 'libxcb-randr0', 'libxcb-render0',
    'libxcb-shm0', 'libxcb-sync1', 'libxcb-xfixes0', 'libxkbcommon0',
    'libzstd1', 'zlib1g', 'libgcc-s1', 'libx11-6', 'libxcb1', 'libglx0',
]


def dependencies(target,version, *, source_qt=False):
    if target not in TARGETS:raise ValueError('Unsupported Debian artifact target.')
    if source_qt and target!=NOBLE:
        raise ValueError('The source Qt dependency recipe is limited to Noble.')
    if target==NOBLE:
        names = NOBLE_DEPENDENCIES+(NOBLE_SOURCE_QT_DEPENDENCIES if source_qt else [])+HANDY_DEPENDENCIES
        return ', '.join(dict.fromkeys(names)),f'augmentor-runtime (= {version}), libglib2.0-bin, wmctrl'
    runtime='python3 (>= 3.11), python3-yaml, python3-websocket, python3-keyring (>= 25.6), python3-secretstorage, gnome-keyring, libc6 (>= 2.39), libstdc++6'
    desktop=f'augmentor-runtime (= {version}), python3-pyside6.qtcore (>= 6.8.2.1), python3-pyside6.qtgui, python3-pyside6.qtwidgets, python3-pyside6.qtnetwork, python3-pyside6.qtdbus, python3-pyside6.qtquick, python3-pyside6.qtquickwidgets, qml6-module-qtquick, qml6-module-qtqml, qml6-module-qtqml-models, qml6-module-qtqml-workerscript, libqt6svg6, qt6-svg-plugins, python3-gi, gir1.2-gtk-4.0, gir1.2-atspi-2.0, at-spi2-core, gir1.2-gstreamer-1.0, gstreamer1.0-pipewire, gstreamer1.0-plugins-base, python3-yaml, python3-websocket, python3-pygments (>= 2.18), python3-numpy (>= 1.24), fonts-dejavu-core, libglib2.0-bin, wmctrl'
    return runtime+', '+', '.join(HANDY_DEPENDENCIES),desktop
