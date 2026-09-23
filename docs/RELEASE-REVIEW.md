<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Private preview release review

This record covers the engineering review for the Debian 13 amd64/Chromium
preview. The exact candidate, CI run and artifact identity are recorded in
PRODUCTIZATION-STATUS.md. It is not an independent penetration test, legal
opinion or approval for a public store listing.

## Data and execution boundaries

| Boundary | Implementation and evidence |
| --- | --- |
| Extension to companion | Stable allowlisted extension identity; exact product handshake before data mutation or harness startup. Installed ZIP/companion CI checks a fresh browser profile. |
| Browser role to Linux | Pi excludes shell/filesystem/desktop tools. DSH has an execution guard plus a native API allowlist and browser-session ownership checks. Actual DSH fixtures try forbidden shell and foreign Linux-chat access and verify no file is created. |
| DSH pairing | Numeric loopback endpoint, no redirect/proxy forwarding, bounded responses, checked host/preset versions and a private local pairing token. Setup preserves existing profile text and refuses customized owned files. |
| Shared memory | Off by default, HTTPS/authentication for remote services, fixed configured scopes, explicit retention, pending-operation journal before submission, no retry of unknown writes. Real Hindsight checks cover recall, isolation, source deletion and export. |
| Desktop input | OS consent, same-user private socket, one conversation owner, fresh single-use window tokens, independent Stop, focus/password checks and no automatic replay. Full VM tests inspect saved files and interrupted text. See DESKTOP-CONTROL.md. |
| Credentials and diagnostics | Private configuration files; keys remain unencrypted at rest. Opted-in traces contain allowlisted metadata, bounded size/retention. Support exports omit conversation, clipboard, screenshot, memory, key, endpoint and personal-path payloads. Actual Qt/Chromium exports are read independently. |
| Updates and recovery | Lifetime leases refuse active replacement; data backups include shared harness configuration. Installed-package CI exercises interrupted configuration, migration, rollback, removal and reinstall without replay. |

Tool approval policies are not an OS sandbox. A harness or model running with
the user's shell access can access that user's files. Same-user local service
checks do not defend against another already-compromised process running as that
user. The browser restrictions are enforced for browser model/tool and extension
requests; they do not convert the entire Linux account into a sandbox.

## Artifact and license checks

`scripts/review-artifacts.py` checks the downloaded Debian packages and extension
ZIP together when `--browser` is supplied. For the Linux desktop-only release,
omit `--browser`; extension review is then reported as not performed. Both modes
require clean source identity, and combined mode requires matching versions. It verifies
artifact hashes/sizes, every ZIP member/hash, the stable manifest version and
included product/Marked notices. It inspects package paths for private-state
files, recomputes the recorded native binary hashes, and verifies their included
notices. Root CI runs it after building the complete artifact set.

The package builder also validates the locked production dependency inventory,
rejects unknown licenses/native executables, collects the pinned npm notices,
and retains Node/esbuild/Go and the rebuilt Photon module's transitive notices.
Photon source/archive hashes, Cargo lock, build procedure and paired outputs are
recorded under `release/photon` and `vendor/photon-node/BUILD.json`.

Augmentor source uses [MIT with Augmentor Resale Restriction](../LICENSE). PySide6/Qt and the capture/accessibility libraries
are installed as replaceable Debian dependencies, not embedded wheels. The
native About/Licenses dialog, license texts and LIBRARY replacement/source
instructions are included; see LICENSING.md and LINUX-PACKAGES.md. DSH and
Hindsight are separately installed services, so their server binaries, models
and credentials are absent from Augmentor's artifacts. Bundling either later
requires a new inventory and source-availability review.

## Distribution limits and next evidence

Private authenticated GitHub artifact downloads are the current delivery path,
with a 14-day CI retention period. Checksums detect modification only when the
manifest comes from that trusted channel. There is no public update service or
Chrome Web Store release yet. Before public publication, the owner must settle
the store identity/listing/privacy disclosures, durable release/source hosting
and update authentication, then review the actual final artifacts again.

The supported preview excludes uncertified desktop/browser combinations and
arbitrary customized DSH profiles. Model connection checks prove protocol/input
acceptance; advertised provider models still require live task-quality checks.
The independent assignments and observed update cycle in PRIVATE-BETA.md remain
required. No tester result or outreach is implied by this review.
