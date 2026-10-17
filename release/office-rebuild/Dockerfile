# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
FROM debian@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends build-essential autoconf automake libtool pkg-config python3 python3-setuptools perl curl ca-certificates git wget zip unzip xz-utils bison flex gperf gawk gettext nasm libfontconfig1-dev libfreetype6-dev libxml2-utils xsltproc libssl-dev file rsync ccache cmake ninja-build && rm -rf /var/lib/apt/lists/*
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
