<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Linux Mint 22.3 source-runtime candidate

The explicit package target is `linuxmint22.3-amd64`, restricted to
`ID=linuxmint`, `VERSION_ID=22.3`, x86-64 and `/usr/bin/python3.12`. Its
[`mint223-cp312-x86_64-source-qt-voice` policy](../release/linuxmint22.3-python-source-qt-voice.json)
requires the reviewed source Qt runtime. Other Mint versions, LMDE, a Noble
package relabelled as Mint and a system-PySide fallback remain refused.

The candidate reuses the exact seven reviewed Noble-built wheels, Qt 6.8.2 native
stage and original PySide6 `augmentor2` derivation receipt. It does not claim
those inputs were compiled on Mint. The 18 Qt libraries, 67 regular native/plugin/
QML files and 18 SONAME links keep their original hashes and provenance. The
source contract is enforced by [the finite native verifier](../scripts/linux-source-qt.py).
The new target/profile gives Mint a distinct policy hash and immutable runtime
identity; its environment is prepared at its final ordinary-user XDG path.
Never copy or relabel an existing Noble virtual environment or its receipt.

The [Debian-format builder](../scripts/package-debian.py) requires `--source-qt`
and the exact reviewed wheel/native input cache for Mint. It supplies a separate
runtime and matching desktop `.deb`, preserves upstream notices and keeps their
root-owned inputs readable to the preparing user. The system recipe supplies
Python 3.12 venv, GI/GTK4/AT-SPI, GStreamer with its Python overrides and GstApp/
GstAudio typelibs, Secret Service, CFFI/NumPy, ICU 74 and the measured native Qt/
Handy dependencies. Bundled Node 24.19 remains the application runtime.

Both dpkg preinst hooks check the exact host before creating maintenance state.
Desktop preinst also checks the installed runtime's target and version. Existing
active-component leases, pending interruption recovery and user-data retention
apply. The [complete assembler](../scripts/package-complete.py) rejects
cross-target Debian-format inputs even when package names and versions match;
setup checks the installed clean source, target and complete runtime contract.
Its managed profile cannot fall back to online pip or system Python. Desktop,
component, startup and Node/voice selection share the immutable runtime and
verified source-Qt library/plugin/QML environment.

The existing [installed Mint session report](../release/qualification/next-targets/20261002-mint223-installed-session.json)
proves normal signed-ISO installation on an ext4 disk, detached-ISO boot,
password login, lock/unlock and reboot. It records Cinnamon 6.6.4 and an X11
session with no Augmentor installed. These facts do not qualify the new package.
Real installed runtime imports, GUI rendering, full Desktop/Browser/Handy setup,
shortcut/Stop and lock/reboot integration, native transactions and physical audio
remain separate tests. Record exact post-install system packages: admitting the
dependencies can update Python, libc and PipeWire from the original ISO baseline.

The focused source tests cover exact target/ABI refusal, Python/Node identity,
native manifest binding, managed-runtime fallback refusal, both preinst host
checks, same-version cross-target desktop refusal, source input verification and
loader paths. They are synthetic checks, not installed-product acceptance.
The policy retains `qualified`, `licenseReviewComplete` and
`embeddedSourceCoverageComplete` as false. Public release and recipient source/
licensing obligations remain open; no source-builder, recipient-control or license
files are changed by this adapter. See the [rollout ledger](LINUX-DISTRO-ROLLOUT.md),
[source runtime entrypoints](LINUX-SOURCE-RUNTIME-ENTRYPOINTS.md) and
[Cinnamon adapter contract](LINUX-CINNAMON-ADAPTER.md).
