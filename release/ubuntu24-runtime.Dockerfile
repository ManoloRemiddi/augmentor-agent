# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Runtime/import fixture only; not a GNOME, Cinnamon or installed-product proof.
FROM docker.io/library/ubuntu@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12-venv python3-gi python3-gi-cairo python3-packaging \
    python3-secretstorage python3-jeepney python3-cryptography \
    python3-jaraco.classes python3-jaraco.context python3-jaraco.functools \
    python3-more-itertools python3-cffi python3-cffi-backend \
    python3-numpy python3-yaml python3-websocket \
    gir1.2-gtk-4.0 gir1.2-atspi-2.0 gir1.2-gstreamer-1.0 \
    at-spi2-core gstreamer1.0-plugins-base gstreamer1.0-pipewire \
    libportaudio2 libgl1 libegl1 libopengl0 libglib2.0-0t64 \
    libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 \
    libxkbcommon-x11-0 libx11-xcb1 fonts-dejavu-core \
    xvfb xauth dbus-x11 wmctrl && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 1001 augmentor-proof
USER augmentor-proof
ENV HOME=/home/augmentor-proof USER=augmentor-proof
WORKDIR /work
