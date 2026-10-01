# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Test-only Qt layer over the disposable compositor fixture. No product payload.
ARG GNOME_BASE=augmentor-gnome-discovery
FROM ${GNOME_BASE}
RUN dnf install -y python3-pyside6 && dnf clean all
