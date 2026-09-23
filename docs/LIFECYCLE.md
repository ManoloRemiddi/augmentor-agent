<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Updating, migrating and removing the Debian preview

For the selected user-local desktop, use [desktop deployments](DESKTOP-DEPLOYMENTS.md).
Package replacement alone does not promote a different user-local desktop build.

The packaged application uses `augmentor-runtime` and optional
`augmentor-desktop`. Both versions come from `release/product.json`. Install the
matching pair when using the desktop. The current preview version is 0.2.10, with Linux
and DSH as the first-release target. Packages retain user data outside
`/usr/lib/augmentor`. Historical upgrade/rollback evidence below is scoped to
its exact version pair; it does not certify every downgrade.

## Upgrade

Finish or Stop running chats, disconnect Augmentor in the extension, and close
open native dialogs. In each account using Augmentor, run:

```sh
augmentor-maintenance prepare
sudo apt install --reinstall ./augmentor-runtime_0.2.10_amd64.deb ./augmentor-desktop_0.2.10_amd64.deb
```

Run the installation command from the directory containing the reviewed package
pair. The public 0.2.10 pair has a distinct version from 0.2.9; `--reinstall` also
supports reinstalling that exact pair if necessary. Public
releases must use distinct versions. It requires an administrator password when the account has no unattended
package-install permission. Do not share that password with an assistant.

Preparation refuses an active task. It closes the idle native window, runtime worker
and shared prompt and automatic-memory companions, then creates a private snapshot under
`$XDG_STATE_HOME/augmentor-release-backups/`. This includes credentials: treat it
as private user data. The command prints the exact backup directory. It does not
stop the external DSH harness or replay a prompt.

Package hooks hold an exclusive release boundary and refuse components still in
use. Launchers, workers and services hold shared lifetime leases. Incomplete
package configuration also prevents launch after reboot. Starting a new chat
after preparing may require preparing again; the package manager refuses the
operation instead of terminating that chat.

For the 0.2.0 baseline, close its UI and browser connection first. It predates the
maintenance command. The 0.2.1 installer detects remaining old workers and refuses
replacement. Keep that release's host shutdown and prompt-service stop available
until its user migration is complete; do not kill a task to force installation.

## Interrupted installation and rollback

Keep the two known-good previous `.deb` files. Finish an interrupted installation
with `sudo dpkg --configure -a`; if dependencies are incomplete, use the
distribution's package repair flow. Do not remove release locks by hand.

The following is the historical 0.2.1 → 0.2.0 rollback example, not the
current candidate rollback command:

```sh
augmentor-maintenance prepare
sudo apt install --allow-downgrades ./augmentor-runtime_0.2.0_amd64.deb ./augmentor-desktop_0.2.0_amd64.deb
```

The checked 0.2.1 → 0.2.0 rollback retains history and prompts in place. It does not
restore an older data snapshot over newer work. This proves that specific schema-1
pair; a future storage migration needs its own compatibility and restoration
checks before publishing a downgrade path.

## Move existing user entrypoints to the packages

After the packages are installed and old components have closed:

```sh
augmentor-maintenance migrate
```

This backs up recognized Augmentor launchers and native-host registrations,
moves the legacy launcher shortcut to the packaged identity, and points the
user-level browser registration at `/usr/bin/augmentor-browser-host`. It retains
the legacy application directory. An existing canonical shortcut takes priority.
Without a running KDE session, the trusted launcher retains its shortcut for the
next login. Differing or symlinked integrations stop migration before replacement.
The printed backup contains a per-file manifest for review or restoration.

## Remove

To remove both components, first run this as each affected ordinary user:

```sh
augmentor-maintenance prepare --remove
sudo apt remove augmentor-desktop augmentor-runtime
```

Preparation clears owned launcher entries and KDE shortcut bindings, removes
recognized user-level browser registrations, and backs up those integrations.
The package manager removes system launchers and native-host registrations.
Configuration, prompts, conversations, backups and user workspace files remain.
Reinstallation uses the retained data without resubmitting old prompts.

For desktop-only removal, use `prepare --component desktop --remove` and
`sudo apt remove augmentor-desktop`. The companion and its active task remain
available. This mode snapshots the removed integrations rather than copying live
runtime data. Per-user cleanup is explicit because root package scripts do not
execute user-controlled code or rewrite arbitrary home directories.

## Current memory and lifecycle evidence

[CI at 29231fd](https://github.com/ManoloRemiddi/augmentor-agent-history/actions/runs/35441917540)
passes installed 0.2.9 maintenance, upgrade/rollback, interrupted configuration and
removal. The installed checks assert the automatic-memory socket closes and its
SQLite journal is included in the backup. This does not back up Hindsight's
external Docker volume; see [memory operations](MEMORY-OPERATIONS.md).

## Historical evidence

Candidate 13 is a clean build from `da2c4b3de69901cf51c4b2256ee1df406f418bc4`.
Its application code matches candidate 12; its package hashes, native binary
notices and exclusion of private state pass the artifact review. Candidate 12
passes installed DSH/Qt checks and Debian 13/KDE Wayland capture/input/Stop.
Candidate 8 supplies clean package lifecycle evidence, and candidate 4 supplies
0.2.7 → 0.2.8 upgrade/rollback and VM reboot evidence. See the
[release status](CROSS-PLATFORM-RELEASE-STATUS.md) for exact scope and remaining
requirements. None of these checks alone makes the candidate public-ready.

The following records the earlier baseline evidence:

`release/lifecycle-proof.py` exercises installed 0.2.0 → 0.2.1 → 0.2.0 packages in
an expendable Debian environment as a separate user. It checks active-update
refusal, desktop-only removal during a task, interruption between unpack and
configure, rollback, migration, unrelated-file preservation, removal and
reinstallation. It compares actual persisted prompts and history and counts
provider requests to reject replay. `scripts/shortcut-launch-proof.py` additionally
checks real key activation and removal across a KDE shortcut-service restart.

Historical private CI rebuilt the baseline from frozen commit
`295dbc0f270344c4eab38ce5ade908622a0cd8af`; local upgrade evidence also uses that
commit's checksum-verified CI packages. These deterministic checks use a local
model fixture. They do not establish live-provider, native Wayland computer-use,
or independent-tester acceptance.


### Public CI baseline after repository consolidation

The current public workflow uses the original, checksum-verified **0.2.9** Debian
packages from the archived `v0.2.9-complete-preview.1` public download. It tests
upgrade to the current candidate, rollback, refusal while active, interrupted
configuration, removal and data preservation. It no longer fetches a private
commit or rebuilds private history. The older 0.2.0 evidence above remains historical.

[`scripts/stage-lifecycle-baseline.py`](../scripts/stage-lifecycle-baseline.py)
pins the complete archive SHA-256 and each Debian package hash, reads only the
expected regular-file members, and writes the manifest consumed by the existing
lifecycle proof. It preserves the original package bytes and source identity.
Run it before `bash scripts/lifecycle-proof.sh`; `--archive` accepts a local copy
only if it matches the same pinned checksum. Do not replace this baseline with
the candidate itself or give public CI credentials for private history.

## User-local supervised desktop

The [September 20 startup deployment](RESTART-RELIABILITY-2026-09-20.md) registers
one user-local build and a managed DSH service. Stop desktop/mobile surfaces
before intentionally stopping DSH for maintenance, because automatic reconnect
starts its registered runtime. `install-desktop-startup.py` backs up launchers and
records the selected deployment; do not independently edit login and menu paths.
