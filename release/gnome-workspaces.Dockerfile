# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Test-only EWMH dependency over the existing actual-native private fixture.
ARG GNOME_BASE=augmentor-rollout-gnome-native-ui
FROM ${GNOME_BASE}
RUN dnf install -y wmctrl && dnf clean all
