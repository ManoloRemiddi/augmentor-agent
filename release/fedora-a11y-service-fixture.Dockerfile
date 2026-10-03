# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
FROM fedora@sha256:43b29f65a41eb9c35e1cd5323e3bdf3b655c2357a9f4f1ff2f9c2798e5045d80
RUN dnf5 install --assumeyes --setopt=install_weak_deps=False --setopt=gpgcheck=1 --setopt=localpkg_gpgcheck=1 at-spi2-core python3-gobject-base dbus-daemon gsettings-desktop-schemas gobject-introspection \
 && echo '9c14ce427c18c5dcfa303db57d22b6277deb48bb154e385b8cceb572fd309c24  /usr/libexec/at-spi-bus-launcher' | sha256sum --check - \
 && echo 'fba13406b5e8ebe67c6eea1aa99f61d2b67a2620ba01bac74ce2772261dd9324  /usr/libexec/at-spi2-registryd' | sha256sum --check - \
 && useradd --create-home --uid 1000 augmentor-proof \
 && mkdir /work \
 && chown 1000:1000 /work \
 && printf 'Owned Augmentor Fedora native accessibility service fixture; no application installation\n' > /etc/augmentor-a11y-service-fixture
ENV HOME=/home/augmentor-proof USER=augmentor-proof LOGNAME=augmentor-proof LC_ALL=C.UTF-8
USER 1000:1000
WORKDIR /work
CMD ["sleep", "infinity"]
