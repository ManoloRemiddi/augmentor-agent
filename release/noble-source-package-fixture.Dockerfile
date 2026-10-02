# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Owned installed-package fixture; no desktop/session/live harness qualification.
FROM augmentor-noble-source-runtime:20261002-25
USER 0:0
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-bin wmctrl && rm -rf /var/lib/apt/lists/*
COPY augmentor-runtime_0.2.13_amd64.deb augmentor-desktop_0.2.13_amd64.deb /inputs/
RUN rm /etc/augmentor-source-runtime-fixture && printf "Owned Augmentor Noble source-runtime package fixture; no owner installation\n" > /etc/augmentor-source-package-fixture && dpkg --install /inputs/augmentor-runtime_0.2.13_amd64.deb && dpkg --install /inputs/augmentor-desktop_0.2.13_amd64.deb
USER 1001:1001
ENV HOME=/home/augmentor-proof USER=augmentor-proof
WORKDIR /home/augmentor-proof
CMD ["sleep", "infinity"]
