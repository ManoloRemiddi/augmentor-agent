<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->
# Fedora 44 installation preview

This is an experimental **Fedora 44 x86_64 RPM** for Augmentor Agent 0.2.9.
It reuses the checksum-verified Linux release payload with an RPM-aware lifecycle
adapter. It is not a Fedora repository submission or certification for all Fedora
editions. DNF-based Fedora installations are the first target; Atomic desktops
(Silverblue/Kinoite), ARM and older Fedora releases are not covered.

## Install

Obtain the RPM and SHA256SUMS together from the release output, then run:

```sh
sha256sum -c SHA256SUMS
sudo dnf install ./augmentor-agent-0.2.9-1.fc44.x86_64.rpm
```

This single RPM contains the runtime, native Desktop app and browser companion.
It resolves Qt/Python and desktop-library dependencies from Fedora repositories.
It is currently unsigned. Do not disable system-wide package signature checks.

Open **Augmentor Agent** from your application menu. Configure your separately
installed DSH profile and a local or cloud model in Settings. The original
0.2.9 DSH compatibility target is 0.1.5-rc.1; do not blindly downgrade a newer
existing installation. Preserve existing conversations and customized presets.

For Browser, use the matching `augmentor-browser-0.2.9.zip` from the same reviewed
bundle, extracted permanently and loaded unpacked in Chromium. The RPM includes
native-host manifests for system Chromium and Google Chrome. Browser attachment
on Fedora still needs an end-to-end desktop test; Flatpak browsers are not covered.

## Update or remove

Finish active work, disconnect the Browser extension and run
`augmentor-maintenance prepare` before replacing/removing the package. The RPM
uses the app's lifetime locks and refuses maintenance while it is open. An
interrupted transaction can leave a pending marker: retry/complete the DNF
operation rather than deleting locks. User home data is not owned by the RPM.

```sh
sudo dnf install ./augmentor-agent-0.2.9-1.fc44.x86_64.rpm
sudo dnf remove augmentor-agent
```

## Validation boundary

See `outputs/fedora-0.2.9/fedora-proof.json` for the exact artifact hash and results.
Container checks cover dependency installation, a non-root runtime lease and
headless Qt rendering, package verification, maintenance protection and data
retention. They do **not** establish working GNOME/KDE session integration,
Wayland/X11 capture and input, custom global shortcuts, SELinux policy behavior,
real Fedora browser attachment or DSH model turns. Those require a real Fedora
desktop before public compatibility claims are expanded.

## Reproduce the package

On the build machine, install `dpkg-deb` and `rpmbuild`, then run:

```sh
python3 scripts/package-fedora.py --bundle outputs/augmentor-agent-0.2.9-linux
```

The bundle's Debian payload checksums are verified before extraction. Original
license notices and release provenance are retained; `fedora-package.json`
records the Fedora target, original inputs and the lifecycle override hash.
No Debian installation scripts are run; the RPM has transaction-specific hooks.

The isolated proof uses the official Fedora 44 container plus the RPM dependencies,
with `release/prove-fedora.py` mounted as `/proof.py`, `tests/` as `/tests`, and the
output directory as `/artifacts`. Run `python3 /proof.py /artifacts/augmentor-agent-0.2.9-1.fc44.x86_64.rpm`.

Sources: [Fedora 44](https://www.fedoraproject.org/workstation/download/),
[Fedora package catalog](https://packages.fedoraproject.org/).
