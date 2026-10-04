<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Mac preview 2 — September 27, 2026

The owner accepted the fixed flare and live App size control on the 32 GB Mac and
explicitly requested GitHub merge and website publication. This release carries
that exact application, including runtime-first DSH setup, native resizing and
the optional second-window shortcut. The Linux download is unchanged.

[Download and install](https://augmentoragent.com/macos.html) ·
[Versioned release](https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.12-macos-preview.2) ·
[Live zoom evidence](MACOS-LIVE-ZOOM-2026-09-27.md)

## Source and artifact identity

- Binary source and release tag target: `b8dac9d36ab3e2d91c2d532e05638e89fa7910e5`.
- [PR #16](https://github.com/ManoloRemiddi/augmentor-agent/pull/16) merged into
  `main` at `482a63a4503b8b0dfc151e65ef706ff8df919a60`. Its changes after `b8dac9d`
  are documentation only. Later publication documentation does not rebuild the app.
- Product version 0.2.12; release tag `v0.2.12-macos-preview.2`.
- DMG: `augmentor-desktop-0.2.12-macos-arm64-preview.dmg`, **519,286,460 bytes**,
  SHA-256 `946a546c98f37ca43ac3fd4596ef3c87100520bc7639ae0737fedbde72b52ae4`.
- Application inventory: 590 entries, SHA-256
  `f125ef11e11da5a579dd60cce8495ee91c50d98f538f234e4db55f03d8c8461f`.
- Accepted build ZIP (local provenance, not a public download): 339,767,464 bytes,
  SHA-256 `9445e86466fe917abde886ac829ba5199cd58fa385ef23fd0debf5a61d16b02e`.
- DMG external `Start here.html` / released `Start-here.html`: SHA-256
  `ea1d4220883cae7b5d6022f14b885fbf137098ec00ed6c62105d595d8bd906a0`.

The DMG was assembled from the accepted ZIP on the 16 GB ARM64 Mac. No file inside
the sealed application was patched. Only the external guide was refreshed for
preview 2 and immediate App size changes. The bundled older source-guide link
still resolves to preview 1's identical dependency archives.

Python 3.12.13, Node 24.19.0, DSH 0.1.5-rc.1 and PySide6 6.8.2.1 / Qt 6.8.2
remain pinned. The exact Qt, PySide and native source archives are reused without
modification from preview 1 through their permanent download URLs in release notes
and `DEPENDENCY-SOURCES.json`; `SOURCE-ARCHIVES.json` retains their original release
provenance. They are not duplicated for an unchanged dependency set. The full Qt archive includes Qt Quick/Declarative, now required by the
shared flare renderer. The current app includes its QtDeclarative notices and
retains the required framework closure. The historical Widgets-only trimming
policy in [preview 1's record](MACOS-PREVIEW-RELEASE.md) no longer describes it.
No private DSH profile, provider credential, conversation or model weights are
packaging inputs. Library replacement rights remain as documented in
[the LGPL guide](MACOS-LIBRARY-REPLACEMENT.md).

## Qualification

The owner installation passed native pointer drags, live zoom during a real model
reply, draft preservation, reopening and signature/inventory verification before
acceptance. Its retained 120% setting remains installed; publication does not
replace it again. There is one canonical application on the owner Mac.

Both final implementation workflows passed at documentation ref `4b24c9c`:
[macOS 14 and 26](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36316148621)
and [full Home, Debian, browser and installed lifecycle checks](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36316148628).
Local source qualification is 528 native cases (three environment skips), 182 Node
cases and TypeScript check/build, plus the platform-specific visual proofs in the
live zoom record. No new runtime change is introduced by this publication. The merged `482a63a`
[main workflow also passed](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36317111874).

Fresh managed setup on the 16 GB Mac (macOS 26.5.1) starts DSH without a model,
opens authenticated DSH without a manually copied key, preserves login after
restart and activates all three required plugins. Actual desktop Send and Enter
after reopening, saved conversation restoration, and fresh Chrome 153 native-host
chat pass. These use a deterministic isolated model, not the owner's credentials.
The fixture's temporary launch agent and shared services are stopped afterward.

The final DMG passes checksum/inventory verification, read-only mount and copy
to a Unicode path, LaunchServices launch, DSH payload/Qt runtime, approval
allow/reject/cancel, questions, exact conversation branching and lost-acknowledgement
protection. Strict application signatures remain valid after use.
`BUILD-AND-TESTS.json` records these checks and the manual-consent boundaries. Source checkout fixtures and built test
dependencies must be present when invoking `macos-bundle-proof.py`; running that
proof from the sealed app's scripts omits test-only fixtures. Early operator
invocations exposed missing fixture/dependency paths, not a product change.

Temporary test applications and their five LaunchServices registrations were
removed after confirming their processes had stopped. The owner installations
were not changed. Sealed archives and private evidence remain in non-indexed caches.

## Preview boundaries

This remains an explicitly approved **ad-hoc signed, unnotarized preview** for
Apple silicon and macOS 14+. The website and guide retain Open Anyway instructions,
manual Chrome/Chromium Load unpacked, and the absence of automatic updates.
The builder's `publicReleaseReady: false` and generic gate list are retained as
stable-release boundaries; the operator record separately establishes preview
acceptance, published sources and checksums. Do not label it a signed stable release.

Existing-install migration and coordinated service-draining updates remain
unfinished. Do not direct users to overwrite an active app. Speech engines, local
memory, complete desktop-control privacy attribution and all model/provider
sign-in flows are not qualified by this release. The Apple approval dialog and
manual extension folder chooser were not automated acceptance steps. No global
security bypass or quarantine-removal instruction is supplied.

## Publication verification

The prerelease was published on September 27, 2026 at **12:30:07 UTC**. All seven
attached files matched their prepared sizes and GitHub server SHA-256 digests.
The published tag resolves to the accepted `b8dac9d` binary source. The three
unchanged dependency archives remain at their pinned preview 1 URLs; all return
HTTP 200, and their server digests match the locally verified originals.

Website commit `e627dcc` passed [website checks](https://github.com/ManoloRemiddi/augmentoragent.com/actions/runs/36319266879)
and [Pages deployment](https://github.com/ManoloRemiddi/augmentoragent.com/actions/runs/36319266526).
The live homepage, Mac installation guide and Desktop page were fetched over
HTTPS and matched their committed HTML byte for byte. Mac links select preview 2;
the copied Linux installation prompt remains byte-identical, and its download
and checksum destinations return HTTP 200. All 15 local website tests and five
JavaScript syntax checks passed.

A local IPv4 connectivity outage delayed transfer. Publication and direct live
HTTP verification used a temporary IPv6 route with normal TLS verification;
no host, browser or LAN network settings were changed. The in-app browser still
could not load the site, so this run does **not** claim a fresh rendered-layout,
live copy-button or clipboard interaction check. Those limitations do not change
the successful source tests, live HTML comparison or artifact verification.

At **12:34:28 UTC**, an anonymous full download of the public DMG completed:
519,286,460 bytes, SHA-256
`946a546c98f37ca43ac3fd4596ef3c87100520bc7639ae0737fedbde72b52ae4`.
The public `SHA256SUMS` file also exactly matched the prepared release. This is a
complete byte-stream check, not only a HEAD request or server metadata comparison.
Later documentation-only commits retain the same website interface and app binary.
