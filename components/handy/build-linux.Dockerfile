# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
FROM debian:trixie-slim@sha256:a99cfc517144bc59b1978475ec53b46ecabec7e43635402ee5b77cc54cd1b20a
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config libgtk-3-dev libwebkit2gtk-4.1-dev \
    libayatana-appindicator3-dev librsvg2-dev libasound2-dev libgtk-layer-shell-dev \
    libopenblas-dev cmake clang libclang-dev libevdev-dev libvulkan-dev glslc \
    spirv-headers glslang-tools curl ca-certificates git patchelf libssl-dev \
    && rm -rf /var/lib/apt/lists/*
ENV PATH="/opt/rust/bin:${PATH}" CARGO_HOME=/cargo CARGO_BUILD_JOBS=2
WORKDIR /work/src-tauri
