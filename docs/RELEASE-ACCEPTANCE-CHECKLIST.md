<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Linux/macOS release acceptance checklist

**Current release order:** [Linux with DSH first](LINUX-DSH-RELEASE-PRIORITY.md),
then macOS with DSH if budget allows. Pi qualification is paused. The historical
Pi/macOS columns below retain evidence and do not gate the Linux DSH release.

This checklist implements the approved release plan's feature inventory. It does
not replace or narrow that plan. Windows and additional Pi extensions remain
later work. Candidate-specific evidence is in
[CROSS-PLATFORM-RELEASE-STATUS.md](CROSS-PLATFORM-RELEASE-STATUS.md).
“Implemented” in the feature matrix is not a completed release gate.

Current artifacts: Debian candidate 14, macOS Desktop candidate 14, macOS Browser
Companion candidate 8. Debian 14 is a clean build from
`8b7a98583d5744be165ce73c24184d15a229986d` and passes artifact/hash/notice review.
Its application code differs from candidate 12 only in the two capture files;
those changed files pass ten GStreamer tests and a full staged Wayland VM proof.
Both packages' install/removal hooks match candidate 8 byte-for-byte. These
comparisons justify retaining the relevant earlier evidence, not claiming that
all feature workflows have been tested. No artifact is public-ready.

| Feature | DSH requirement/dependency | Pi requirement/dependency | Linux evidence and remaining work | macOS evidence and remaining work |
| --- | --- | --- | --- | --- |
| Prompt records, revisions and conflicts | Product prompt adapter 0.2.8 | Shared prompt service 0.2.8 | Candidate 14 extracted-code Qt editor with real shared service passes conflict preservation, stale-save refusal, rename and delete controls | Companion 6 installed browser passes; Desktop 12 native workflow not rerun |
| Prompt editor | Shared service and surface editor | Same | Candidate 14 extracted-code editor save/reload/rename/delete passes offscreen; native source regressions also pass | Companion 6 browser passes; Desktop 12 native editor acceptance pending |
| Clipboard token, one snapshot, no automatic send | Shared template contract | Same | Candidate 14 extracted-code Qt picker substitutes clipboard text without submitting or later draft changes; current installed browser refresh check remains separate | Companion 8 forced refresh during click passes after correcting a proof-driver click on a hidden menu; older uninstrumented timeouts remain unattributed |
| Copy, visual feedback and timing | Shared surface behavior | Same | Existing UI evidence; current artifact acceptance incomplete | Prior browser evidence; physical desktop clipboard/shortcut coverage incomplete |
| Branch preserving completed tool context | DSH 0.1.5-rc.1 and product exact-fork adapter | Pi SDK 0.85.1 | Installed DSH candidate 12 exact-prefix fork and continuation pass; candidate 14 adapter code is identical | Companion 6 DSH/Pi passes; Desktop 14 installed DSH exact-fork fixture passes |
| Edit on a child, unchanged parent, no replay | Same exact-fork adapter | Supported Pi session branching | Candidate 12 DSH lost-ack no-replay passes; candidate 14 adapter code is identical; Pi qualification paused | Companion 6 browser passes; Desktop 14 lost-ack check passes |
| Models, streaming, Stop and history | DSH 0.1.5-rc.1; Model Picker Augmented 1.1.2 for curation | Pi SDK 0.85.1 | Candidate 8 clean Pi setup/Stop/reopen and DSH Model Picker checks pass; full platform matrix incomplete | Prior desktop evidence and Companion 6 browser checks; full current desktop acceptance pending |
| Checked connection and explicit save | Shared DSH setup service | Pi setup service | Installed DSH candidate 12 checked-save/profile preservation and custom-compaction fixture pass; candidate 14 setup/UI code is identical | Companion 6 DSH save and fresh Pi setup pass; Desktop 14 native DSH setup passes |
| Browser navigation, snapshot, typing and clicking | Bundled browser plugin 0.2.8 and browser-only policy | Pi browser binding 0.2.8 | Earlier installed/source browser checks; current artifact run pending | Companion 6 DSH and Pi actual-page results pass |
| Desktop capture, click, keys and ASCII text | Desktop adapter 0.2.8 and OS executor | Same OS executor | Candidate 12 installed capture/input/Stop and 30 captures pass; candidate 14 capture change passes ten GStreamer tests and staged VM input/Stop; intermittent capture root cause remains unresolved | Native backend exists; Screen Recording/Accessibility acceptance incomplete |
| Bounded desktop specialist | DSH implementation unavailable; required release scope unresolved | Pi isolated SDK session preview | Existing preview evidence is not full release qualification | Not qualified |
| Memory and user data controls | Memory adapter 0.2.8, optional Hindsight 0.9.2 | Shared memory binding, optional Hindsight 0.9.2 | Source Pi/DSH checks; current artifact qualification pending | Desktop 10 native and role bindings; Companion 4 browser controls; current artifacts not rerun |
| Private support export | Shared support service and surface dialogs | Same | Source checks and prior installed evidence | Companion 6 export passes; Desktop 14 native DSH setup passes |
| Questions, approvals, rejection and cancellation | Product scoped interaction leases; DSH ask-user tool | Declared Pi approval behavior | Candidate 12 installed DSH fixture passes reject/allow-once/cancel and question reply through offscreen Qt; candidate 14 interaction/UI code is identical | Desktop 14 Cocoa DSH fixture passes; full browser interaction acceptance incomplete |

## Installed DSH composition

The authoritative installer is `services/dsh/setup.py`. It checks the supported
CLI and API versions, preserves existing profile content, and refuses unreviewed
custom integration replacements. Its current composition includes:

- DSH CLI and first-party packages pinned to 0.1.5-rc.1 in `release/dsh`.
- Product adapter, browser plugin, prompt adapter, persona, and memory adapter.
- Desktop role: bash, filesystem, ask-user, Augmentor desktop tools and the
  reference preset capabilities recorded in [plugin acceptance](LINUX-DSH-PLUGIN-PARITY.md).
- Browser role: Augmentor browser policy and browser tools.
- Model Picker Augmented 1.1.2 is separately required for DSH model curation.
- Hindsight 0.9.2 is optional and configured explicitly; installing a DSH profile
  does not provision it or model credentials.

Resonant CORE is mentioned as an architecture boundary in the plan but has no
verified release integration. The user has specified parity with the working installation; its observed active
external plugins are recorded in [plugin acceptance](LINUX-DSH-PLUGIN-PARITY.md).
Do not silently remove a requirement or claim all DSH plugins work. The desktop specialist's DSH
scope also remains unresolved; its absence cannot be hidden by Pi subset labels.

## Remaining distribution and platform gates

- Candidate 14 has a clean source/artifact identity and passing engineering artifact
  review. Preserve that identity through distribution; any subsequent application
  changes require a new reviewed build.
- Complete current-candidate install, upgrade, rollback, removal, retained data,
  restart and fresh-user acceptance for each advertised component and platform.
- macOS: actual capture/input consent, denial, revocation, screen lock, changed
  targets, display changes, unsupported cases and independent Stop; physical
  shortcut delivery and logout/login; qualify only tested OS/architecture targets.
- Linux: resolve or characterize the intermittent capture failure; retain safe
  refusals for unsupported environments; expand distro/session support according
  to the plan without treating package installation as desktop-control evidence.
- Complete native license/source availability and build-provenance review.
- macOS only (deferred): obtain Developer ID signing and notarization, then test
  the distributed identity.
- Establish durable public source/download locations, immutable assets and hashes.
- Publish matching extension/companion/desktop installation and recovery guidance;
  add the two planned website download cards with truthful platform labels.
- Validate extension identity and native-host allowlists. A browser-store listing
  may follow unpacked ZIP distribution, as allowed by the plan.

No passing unit suite, single VM run or earlier-candidate proof closes all of these
gates. Record new evidence against the relevant row and exact installed artifact.
