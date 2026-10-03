<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Fedora dictation packaging candidate

The corrected Fedora 43/44 RPMs pass fresh installation, ordinary-user Desktop
rendering, active runtime and Desktop refusal for reinstall/removal, idle
reinstall, removal preserving private files, and reinstall after removal in a
fresh owned containers. The installed Handy component also passes its actual
disabled protocol/theme/ownership/EOF check through the cold runtime lease.
See [the qualification report](../release/qualification/next-targets/20261003-fedora-dictation-packaging.json).

The original working-recipe checkpoint combines clean public `4f99696` payload
with separately hashed packaging/maintainer recipes. A newer
[clean-source package record](../release/qualification/next-targets/20261003-clean-fedora-package-replacement.json)
builds both RPMs from the clean `536fc75` Debian-format payload and matching
committed recipes. In both fixtures, actual installed cold runtime and Desktop
leases refuse replacement, idle reinstall adopts the clean source, private files
remain and ordinary-user rendering passes. This is different-source replacement
at the same product/package version, not a version-to-version upgrade or rollback.
Fresh clean-536 installation is still running in hosted CI. Complete installers,
native GNOME/KDE sessions, graphical Browser, physical audio/input, enforcing
SELinux, upgrades/rollback and source/legal/release acceptance remain open.

## Observed failure and corrected package contract

The original local RPM build and both hosted Fedora jobs fail with
“Installed (but unpackaged)” for `70-augmentor-dictation.rules` and
`augmentor-dictation.conf`. The recipe now includes those files and runs the
same bounded uinput/udev setup as Debian after the transaction. A container
cannot establish active-user device access: no input, audio or GPU devices
are attached here.

The [measured Handy ELF requirements](LINUX-HANDY-NATIVE-CLOSURE.md#original-artifact-and-native-abi)
require GLIBC 2.39 and GLIBCXX 3.4.32. Fedora now explicitly declares those
floors and its GTK3, WebKit4.1, JavaScriptCore4.1, layer-shell, indicator,
OpenBLAS, Vulkan, ALSA, clipboard/XWayland and device setup providers.
[OpenBLAS serial](https://packages.fedoraproject.org/pkgs/openblas/openblas-serial/)
supplies the required library; the documentation-only `openblas` package
does not. [Layer-shell](https://packages.fedoraproject.org/pkgs/gtk-layer-shell/gtk-layer-shell/)
is also explicit. The external `which` command is required by the pinned
Handy helper discovery; Debian-format recipes now provide `debianutils`
and raise their generic libc floor to the measured 2.39.

RPM installation admits only its exact Fedora release and x86-64 before writing
maintenance state. An ID_LIKE derivative, other Fedora version or architecture
refuses. Final removal uses the existing activity guards without requiring the
old installation's OS release, so a Fedora 43 package remains removable after
a distro upgrade to 44. These are hook checks; a real distro upgrade is not
qualified by the synthetic removal-admission case.

The copied application release marker now names the actual Fedora target.
The package receipt separately identifies the immutable Debian-format payload
inputs and the packaging/maintainer recipe hashes. Native binaries retain their
producer bytes and executable modes. The RPM disables automatic rewriting of
the verified payload. This is a preview build, without a published binary,
customer package-signing setup or automatic native dependency closure claim.

## Actual Fedora fixtures

A component-only Fedora 44 fixture first resolves all 25 native ELF loader lists
and executes the public disabled component probe as UID1000 under private
D-Bus/Xvfb. It installs native packages from normal signed Fedora repositories,
then disconnects networking before execution.

Separate complete-package fixtures start from the exact pinned official
Fedora 43/44 images with no application or proof user. They install explicit distro
dependencies from normal repositories, disconnects networking, then executes
the unchanged public [package probe](../release/prove-linux-package.py).
The local candidate RPM is unsigned; that private command-line artifact has
its exact checksum verified, while ordinary repository checks remain enabled.
Observed versions are Python 3.14.7 and Node 24.19.0 on both; Fedora 43 uses
PySide/Qt 6.10.3 and GTK4 4.20.4, while Fedora 44 uses 6.11.2 and GTK4 4.22.5.
The package's final `rpm -V` also passes after the component probe.

The first installed-component attempt lacked `dbus-run-session`. Adding its
actual `dbus-daemon` provider as a qualification dependency permits the repeat;
normal desktop sessions are a separate requirement. The passing private probe
still logs missing FUSE/display portal backend warnings. They are retained and
do not constitute a successful real portal session. No capture, model download,
tray acceptance, paste or installed dictation-broker action is requested.

Earlier guarded driver attempts refused an inherited proof user and Docker's
`none` network representation before product installation. The subsequent
fresh fixture succeeds; the original attempts remain distinct. Twenty-one
focused Linux cases pass: 12 complete setup, three Fedora hooks and six Debian
target cases. Four installed Linux adapter tests now explicitly skip on other
platforms; shared portable setup cases continue to run.

## Hosted source checks and remaining diagnosis

For head `4f99696`, [Linux run 37070593276](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37070593276)
passes source boundary, Home, all three Handy platforms, Debian, installed
packages and packaged Browser. The two Fedora builds fail on the omitted files
above. Ubuntu 26.04 passes package lifecycle, then exits 139 in the native suite
at the shared browser dialog test. It is not an APT installation failure.
A separate [isolated diagnostic and correction](LINUX-QT-FIXTURE-COMPATIBILITY.md)
identify the class-level MagicMock trigger; a real fixture override passes the
unchanged UI cases and the 31-case Window sequence. The workflow now enables
Python faulthandler for the next native distro suite without suppressing cases.

[Mac run 37070593430](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37070593430)
passes both 14 and 26. [Windows Desktop](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37070593066)
fails four Linux-only setup fixture entrypoints, addressed by the explicit
platform decorators here. The [full Windows run](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37070593079)
has a separate x64 actual desktop teardown access violation; ARM64 passes.
Its recorded payload checkout `a3ec589` differs
from `4f99696` only in four documentation files. No Qt teardown repair is
claimed from this record. Both new `536fc75` Windows Desktop jobs now pass
after explicit Linux adapter scoping. Its complete Linux/Mac/Windows
qualification is still running at the clean-package checkpoint.

GitGuardian checks `111048837418` and new `111063275897` remain failed and unwaived with the same
twelve historical script/log digest findings. Fresh hosted checks for the
corrected source are required. All five rollout points remain active. The
22-file license proposal remains exact and pending; owner installations,
selection, services, models, device and audio settings have not changed.
