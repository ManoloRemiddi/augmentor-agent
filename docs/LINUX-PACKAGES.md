<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Debian packages: development preview

These packages are an implementation milestone, not a public supported release.
The [agent handoff](AGENT-HANDOFF.md) records the current qualified implementation
and the independent beta/public distribution gates. The first release targets Linux with [DSH setup](DSH-SETUP.md) and shared
[automatic Hindsight memory](DUAL-MEMORY.md). Fresh desktop profiles default to DSH and offer
connection setup. Pi supports the subset in the feature matrix and retains its own regression and
package checks. macOS qualification is tracked separately in the release ledger. Linux includes a bounded
[desktop control preview](DESKTOP-CONTROL.md).

## Components

- `augmentor-runtime`: shared services, DSH adapters, the Chromium native companion
  and application code. Existing Pi runtime code is retained but is not the
  first-release qualification target. Includes a hash-pinned Node executable and locked npm
  dependencies. Requires Python and the declared system C/C++ libraries, not
  system Node/npm or Qt. Registers the host for conventional Chrome/Chromium.
- `augmentor-desktop`: launcher, application-menu entry and desktop dependencies.
  Depends on the identical runtime package version. Uses Debian's separately
installed, replaceable PySide6/Qt libraries.

Application code resides in `/usr/lib/augmentor`. It is read-only to an ordinary
user; configuration, prompts, conversations and logs remain in user directories.
The existing `augmentor-pi` user-state names remain compatible. The current
`0.2.9` package version is a preview build from this branch, not a public release.

The packaged desktop uses `com.augmentor.Agent.desktop`. In KDE, save a show/hide
key in **Settings** to create its user launcher entries and activate the binding.
The [lifecycle guide](LIFECYCLE.md) covers migration of recognized legacy user
entrypoints, owned shortcut removal, updates and rollback.

## Build and check

```sh
npm ci --ignore-scripts
npm run check
npm run build
python3 scripts/package-debian.py
bash scripts/debian-package-proof.sh
```

The builder needs Python 3.11+, npm, a compatible Node and `dpkg-deb`; it targets
Linux amd64. `release/runtime.json` pins the embedded Node archive/checksum and
the Debian acceptance image. Build-time downloads are separate from installation.
Staging removes only the unused optional terminal clipboard and foreign esbuild
binaries/keyboard helpers, plus SDK sample applications; the Linux esbuild
executable stays available for SDK extensions. It installs the reviewed Photon
rebuild, retaining image support and its transitive notices.

To reproduce that image module, install Rust 1.97.1 and its
`wasm32-unknown-unknown` target, then run `python3 scripts/build-photon.py`.
Source/CLI archive hashes, the Rust lock and paired output hashes are recorded
under `release/photon` and `vendor/photon-node/BUILD.json`. Rebuilds intentionally
require review before accepting changed dependencies, notices or binary hashes.

Artifacts and SHA-256 records are written under `outputs/debian/`. These checksums
detect corruption; an authenticated public update channel remains separate work.
Root CI retains its private package artifacts for 14 days.

The package proof uses Podman, or Docker with `AUGMENTOR_CONTAINER_ENGINE=docker`.
It starts a clean Debian userland, installs the runtime using its declared
dependencies, creates a separate ordinary user and confirms no system Node or Qt
is available. It verifies real Pi file execution against a local deterministic
model, shared prompts through native messaging, restart without replay and Stop.
It then installs the desktop, exercises the actual first-run form and a file task,
and verifies real KDE shortcut launch/hide/show before and after restarting the
shortcut service. It removes package-owned files while preserving user data. This
is separate from the [installed lifecycle proof](LIFECYCLE.md), which also covers
running-service refusal, migration, rollback, interruption and user integration
cleanup. Neither container proof is a full desktop VM certification.

## Preview installation

Install both local files through the distribution's package installer, or:

```sh
sudo apt install --reinstall ./augmentor-runtime_0.2.9_amd64.deb ./augmentor-desktop_0.2.9_amd64.deb
```

For browser-only use, install the runtime package alone. The extension still needs
its [preview loading step](BROWSER-DISTRIBUTION.md); store publication remains
pending. Existing
user-level native-host registrations can override the new system registration;
use `augmentor-maintenance migrate` to migrate recognized registrations after
closing old components. Differing registrations are reported for review.
The package build/proof does not install or replace the developer's live app.

## Licenses and library replacement

Read **About & licenses** in the native app or `/usr/lib/augmentor/docs/LICENSING.md`.
The npm inventory/texts, upstream fallback notices, Node's full bundled notices
and a binary inventory are under `/usr/lib/augmentor/licenses/`. Each reviewed
binary records a hash; unknown native executables fail the build. Qt binaries
are supplied by Debian dependencies, not embedded inside our package.

Use `dpkg-query -W` to identify installed `python3-pyside6.*`, `libpyside6*`,
`libshiboken6*` and `libqt6*` versions. Their copyright/source information is under
`/usr/share/doc/`. With matching Debian source repositories enabled, `apt source`
can retrieve the corresponding `pyside6`, `qt6-base` and `qt6-svg` source packages;
select the source versions matching the installed binaries. Preserve the Debian
patches and build instructions when rebuilding those libraries.

Users may install rebuilt compatible system libraries, or set `AUGMENTOR_PYTHON`
to a Python environment with compatible replacement PySide/Qt libraries. The
application does not enforce original library hashes at runtime. Debugging
modifications, including the necessary reverse engineering, is permitted.

## Installed DSH acceptance

`scripts/debian-dsh-proof.sh` runs a separate ephemeral Debian container against
the selected package artifacts. Set `AUGMENTOR_DEBIAN_ARTIFACTS` to the artifact
directory, `AUGMENTOR_CONTAINER_ENGINE` to `docker` or `podman`, and
`AUGMENTOR_DSH_TEST_ROOT` to an installed DSH 0.1.5-rc.1 package directory containing
its `package.json`, `lib` and `node_modules`. The script verifies artifact hashes
and the host version before mounting that test host read-only.

The container installs the runtime and desktop packages, then runs setup,
questions, approvals and exact-edit acceptance as an ordinary user against the
installed adapter. It uses a deterministic local model and isolated DSH state.
This complements `scripts/debian-package-proof.sh`; it does not establish live
external-model behavior, KDE Wayland desktop control, reboot activation or
compatibility with other distributions.

`release/lifecycle-proof.py` additionally verifies an installed 0.2.7 → 0.2.8
transition in a disposable container or marked test VM. Against Debian candidate
4, it passes active-task refusal, upgrade/rollback, interrupted configuration,
legacy integration migration, removal and reinstall with retained conversations,
shared prompts and custom improvement instructions. It verifies no automatic
model replay. Evidence is recorded in
`outputs/cross-platform/linux-lifecycle-027-to-028.log`; actual reboot and KDE
Wayland acceptance remain separate requirements.

Candidate 4 now also passes `scripts/vm-acceptance.py` in the preserved test VM's
isolated copy-on-write overlay: Plasma Wayland with the app rendered through
XWayland, hardware-key shortcut launch/hide/show, actual guest reboot, automatic
shortcut restoration and owned-shortcut removal. The run includes first-run file
work and six clipboard/scroll cases. Evidence:
`outputs/cross-platform/linux-wayland-reboot-4.log`. Current-artifact desktop
capture/input/Stop acceptance remains separate.
