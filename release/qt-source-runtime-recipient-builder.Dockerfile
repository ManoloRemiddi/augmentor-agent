# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Frozen candidate toolchain, from public base plus separately authenticated .debs.
# Run acquire-ubuntu-toolchain.py against complete signed metadata before building.
# docker build --network=none with this file and the reviewed kit/debs context.
# This builder is neither an application installation nor a release artifact.
FROM docker.io/library/ubuntu@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3
ENV DEBIAN_FRONTEND=noninteractive
COPY debs/ /inputs/debs/
WORKDIR /inputs/debs
RUN printf '%s\n' 'dd48878dac87bf715ded8614dd15172a94cea2f7ce947108d1fce3e0ec4eee84  SHA256SUMS' | sha256sum --strict --check - && \
    sha256sum --strict --check SHA256SUMS && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get -o Acquire::Retries=0 -o DPkg::Lock::Timeout=0 -y \
        --no-install-recommends --allow-downgrades install /inputs/debs/*.deb && \
    dpkg-query -W > /inputs/build-package-versions.txt && \
    printf '%s\n' 'bc6cd4560d3d984dc11e2b2faceb1b1b2fcf73440fad5a4d9c6a8f76a594b7b3  /inputs/build-package-versions.txt' | sha256sum --strict --check - && \
    mkdir -p /work && \
    printf '%s\n' 'Owned Augmentor Noble Qt source builder; no application installation' > /etc/augmentor-source-build-container
RUN useradd --create-home --uid 1001 augmentor-proof && chown augmentor-proof:augmentor-proof /work
USER augmentor-proof
ENV HOME=/home/augmentor-proof USER=augmentor-proof LLVM_INSTALL_DIR=/usr/lib/llvm-18
WORKDIR /work
RUN python3.12 -m venv --system-site-packages --without-pip /work/build-python
CMD ["sleep", "infinity"]
