# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Isolated source builder; no application/runtime installation or qualification.
FROM docker.io/library/ubuntu@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build pkg-config ca-certificates patchelf \
    python3.12-dev python3.12-venv python3-setuptools python3-wheel python3-packaging \
    libclang-18-dev llvm-18-dev clang-18 \
    libgl1-mesa-dev libegl1-mesa-dev libopengl-dev libvulkan-dev \
    libdbus-1-dev libglib2.0-dev libatspi2.0-dev libssl-dev libfontconfig1-dev \
    libicu-dev zlib1g-dev libpcre2-dev \
    libdouble-conversion-dev libfreetype-dev libharfbuzz-dev libpng-dev libjpeg-dev \
    libtiff-dev libwebp-dev libwayland-dev libxkbcommon-dev libxkbcommon-x11-dev \
    libx11-dev libx11-xcb-dev libxcb1-dev libxcb-cursor-dev libxcb-icccm4-dev \
    libxcb-image0-dev libxcb-keysyms1-dev libxcb-render-util0-dev libxcb-glx0-dev \
    libxcb-shape0-dev libxcb-xinerama0-dev libxcb-xkb-dev \
    libxcb-randr0-dev libxcb-sync-dev libxcb-xfixes0-dev libxcb-render0-dev \
    libxcb-shm0-dev libxcb-util-dev wayland-protocols && \
    mkdir -p /work /inputs && \
    dpkg-query -W > /inputs/build-package-versions.txt && \
    printf '%s\n' 'Owned Augmentor Noble Qt source builder; no application installation' > /etc/augmentor-source-build-container
RUN useradd --create-home --uid 1001 augmentor-proof && chown augmentor-proof:augmentor-proof /work
USER augmentor-proof
ENV HOME=/home/augmentor-proof USER=augmentor-proof LLVM_INSTALL_DIR=/usr/lib/llvm-18
WORKDIR /work
RUN python3.12 -m venv --system-site-packages --without-pip /work/build-python
CMD ["sleep", "infinity"]
