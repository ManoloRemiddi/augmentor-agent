# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Test-only imports for the actual native UI in the disposable GNOME fixture.
ARG GNOME_BASE=augmentor-rollout-gnome-qt-fixture
ARG NODE_BASE=augmentor-rollout-fedora-node-cache
FROM ${NODE_BASE} AS node_fixture
FROM ${GNOME_BASE}
COPY --from=node_fixture /usr/lib/augmentor/node /usr/lib/augmentor/node
RUN dnf install -y python3-pyyaml python3-websocket-client python3-pygments python3-numpy python3-keyring python3-secretstorage && dnf clean all
