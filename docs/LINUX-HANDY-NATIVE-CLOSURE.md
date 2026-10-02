<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Dictation native candidate on Arch and Leap

The checksum-pinned public Handy candidate resolves its25 native ELF objects and
passes actual disabled component startup on both owned distro fixtures. The
[actual report](../release/qualification/next-targets/20261003-handy-arch-leap-native-candidate.json)
records the artifact, producer, executed probes, package registrations and raw
log hashes. This is an additional component check; complete installed products,
minimum CPUs, graphical Browser, microphone/paste and real Wayland sessions remain
unqualified. All five distro rollout points stay active.

## Original artifact and native ABI

The [public producer run](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37036303734)
at source`81a2bba34cd88b34f9f76023e04782af2df74e82` validates a restored cached
runtime on Ubuntu24.04. It does not establish a fresh compiler production. Artifact
`11239857075`, `handy-linux-x86_64`, is169,211,434 bytes; original ZIP SHA256 is
`8d1b22b99b1f4c4a9dc451a7904e4eb794a175bd9c23c2fde3f99846d7b5cb2d`.
The preserved original BUILD.json digest is
`ea1a5a3defdb8d60c8a0d442dbd9f2169f6a110d291f390438e3624c92f031c2`.
The component's embedded source, patch and recorded build-input hashes also match
the current working merge. No notices/source archives or producer receipt is
rewritten to claim another producer.

[`probe-handy-linux-elf.py`](../release/probe-handy-linux-elf.py) checks the complete
producer file inventory and hashes, then uses readelf without executing the
payload. Its result agrees with the original private inspection:25 native files,
maximum required GLIBC2.39, GLIBCXX3.4.32 and CXXABI1.3.11. It records every
DT_NEEDED, interpreter, search path and required symbol version. This is stronger
than inferring compatibility from a Dockerfile, but does not by itself prove
complete relocation, instruction-set suitability or target runtime behavior.

The actual distro loader then lists every native object as ordinary UID1000.
Before installing the explicit dependencies, two objects in each fixture fail.
After installation all25 pass, with153 Arch/147 Leap observed system library
paths registered to packages and six bundled paths. These are observed loader
providers, not a complete dependency byte inventory or a maintenance fence.
Existing system-Python/Qt candidate verification still passes after the native
packages are installed.

## Verified provider choices

| Requirement | Fedora43/44 metadata | Leap16 fixture | Arch20261001 fixture |
| --- | --- | --- | --- |
| WebKitGTK4.1 | webkit2gtk4.1 | libwebkit2gtk-4_1-0 | webkit2gtk-4.1 |
| GTK layer-shell | gtk-layer-shell | libgtk-layer-shell0 | gtk-layer-shell |
| AppIndicator candidate | libappindicator-gtk3 | libappindicator3-1 | libayatana-appindicator |
| OpenBLAS SONAME0 | openblas-serial | libopenblas_serial0 | openblas |

Fedora metadata explicitly lists the libraries in
[WebKit4.1](https://packages.fedoraproject.org/pkgs/webkitgtk/webkit2gtk4.1/fedora-44.html),
[layer-shell](https://packages.fedoraproject.org/pkgs/gtk-layer-shell/gtk-layer-shell/fedora-44.html),
[AppIndicator](https://packages.fedoraproject.org/pkgs/libappindicator/libappindicator-gtk3/fedora-44.html)
and [OpenBLAS serial](https://packages.fedoraproject.org/pkgs/openblas/openblas-serial/fedora-44.html).
The Fedora `openblas` package itself contains docs, so its name alone is insufficient.
The [Fedora packaging checkpoint](LINUX-FEDORA-DICTATION-PACKAGING.md) now implements
the matching dependency and udev-rule contract, builds both RPMs and executes the
new Fedora 44 installed lifecycle/component checks. Complete session, audio,
input, clean combined product and release qualification remain separate.

The official [Leap repository](https://download.opensuse.org/distribution/leap/16.0/repo/oss/repodata/repomd.xml)
and dated [Arch file index](https://archive.archlinux.org/repos/2026/10/01/extra/os/x86_64/extra.files)
provide the candidate mappings. Fresh research checked metadata content hashes;
it did not independently authenticate those repository signatures. The actual
fixture transactions and installed package identities are retained separately.
Leap's ordinary `dbus-1` package does not supply the test-bus executable:
`zypper` identifies `dbus-1-daemon` for `/usr/bin/dbus-run-session`. The original
missing-tool attempt and no-op `dbus-1` transaction are preserved; the later
private-bus component proof passes with the actual daemon provider.

The supplied, hash-checked `libappindicator-sys0.9.0` source explicitly tries
Ayatana SONAME1 before AppIndicator SONAME1. Arch's Ayatana package therefore
matches an actual supported loader choice. See
[the pinned loader source](https://github.com/tauri-apps/libappindicator-rs/blob/eafd1e3682a1247f595410266091e9684021cb6f/sys/src/lib.rs#L13).
Embedded mode also skips the tray; these proofs confirm `tray:false`, not a live
indicator-tray acceptance.

Arch's dated xdotool package supplies libxdo.so.4 rather than .3. None of the25
Handy objects declares either library, the active supplied crate notices contain
no libxdo crate, and the matching Enigo default uses x11rb. Tauri's libxdo feature
is optional and absent from this selected default dependency configuration. See
[the pinned Tauri manifest](https://github.com/tauri-apps/tauri/blob/7cd71369c00978a3783b6ae3e9972358abbe4ae6/crates/tauri/Cargo.toml)
and [pinned Enigo manifest](https://github.com/enigo-rs/enigo/blob/b297a14e807abdf818b7809a70b445ade4fc5897/Cargo.toml).
Do not introduce a compatibility symlink. The external xdotool command remains
an independent paste-helper requirement to test.

The [pinned Handy clipboard code](https://github.com/cjpais/Handy/blob/05e0aedd2906f0d82722735f930465950c476b90/src-tauri/src/clipboard.rs)
executes `which` to discover helpers. Minimal packages must provide that executable
alongside the chosen xdotool/wl-clipboard/XWayland paths. The bundled ydotoold uses
Augmentor's private socket and needs active-user access to `/dev/uinput` for actual
injection. No fixture attaches a physical input/audio device for this checkpoint.

## Actual bounded component check

The existing public [`proof-handy-component.py`](../scripts/proof-handy-component.py)
executes the candidate under private D-Bus/Xvfb as UID1000. It checks the actual
status protocol, disabled/no-tray state, theme validation, stale settings refusal,
conversation ownership exclusion and zero-exit termination on stdin EOF. Both
fixtures pass; the probe requests no capture or model download. The copied binary
modes are restored from the original ZIP's exact0755 metadata, preserving all
file bytes. This does not test the ordinary user's installed dictation broker,
consented shortcuts, owned target paste, microphone/ASR or graphical Browser.

Keep complete target package builders, bootstrap interpreters, installer/runtime
receipts and uinput provisioning explicit. Verify native package replacement
under maintenance, not just successful imports. Then qualify GNOME/KDE sessions,
Browser, voice and upgrade/rollback/removal from one clean product/dependency
revision. Source/legal acceptance and the22-file license decision remain open;
no owner installation, selected artifact, service, model or device changes here.
