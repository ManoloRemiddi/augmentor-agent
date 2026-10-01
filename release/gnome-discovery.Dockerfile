# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Disposable software-rendered compositor fixture, not a product image.
FROM docker.io/library/fedora@sha256:43b29f65a41eb9c35e1cd5323e3bdf3b655c2357a9f4f1ff2f9c2798e5045d80
RUN dnf install -y python3 gnome-shell mutter xdg-desktop-portal-gnome xdg-desktop-portal-gtk pipewire wireplumber dbus-daemon mesa-dri-drivers xorg-x11-server-Xwayland shadow-utils util-linux dejavu-sans-fonts && dnf clean all
ENV LANG=C.UTF-8
