# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Disposable source-runtime product-entrypoint fixture; no graphical-session qualification.
FROM docker.io/library/ubuntu@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    at-spi2-core dbus-x11 fonts-dejavu-core gir1.2-atspi-2.0 gir1.2-gstreamer-1.0 \
    gir1.2-gtk-4.0 gnome-keyring gstreamer1.0-pipewire gstreamer1.0-plugins-base libbrotli1 \
    libc6 libdbus-1-3 libdouble-conversion3 libegl1 libfontconfig1 \
    libfreetype6 libgcc-s1 libgl1 libglib2.0-0t64 libglx0 \
    libharfbuzz0b libicu74 libjpeg-turbo8 libopengl0 libpcre2-16-0 \
    libpng16-16t64 libportaudio2 libssl3t64 libstdc++6 libtiff6 \
    libwayland-client0 libwayland-cursor0 libwayland-egl1 libwebp7 libwebpdemux2 \
    libwebpmux3 libx11-6 libx11-xcb1 libxcb-cursor0 libxcb-glx0 \
    libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
    libxcb-render0 libxcb-shape0 libxcb-shm0 libxcb-sync1 libxcb-xfixes0 \
    libxcb-xinerama0 libxcb-xkb1 libxcb1 libxkbcommon-x11-0 libxkbcommon0 \
    libzstd1 python3 python3-cffi python3-cffi-backend python3-cryptography \
    python3-flatbuffers python3-gi python3-gi-cairo python3-jaraco.classes python3-jaraco.context \
    python3-jaraco.functools python3-jeepney python3-more-itertools python3-numpy python3-packaging \
    python3-secretstorage python3-websocket python3-yaml python3.12-venv xauth \
    xvfb zlib1g && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 1001 augmentor-proof && install -d -o 1001 -g 1001 /work && printf "Owned Augmentor Noble source-runtime entrypoint fixture; no application installation\n" > /etc/augmentor-source-runtime-fixture
USER 1001:1001
ENV HOME=/home/augmentor-proof USER=augmentor-proof
WORKDIR /work
CMD ["sleep", "infinity"]
