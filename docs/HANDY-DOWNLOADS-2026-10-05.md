<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# October 5 matched dictation repair downloads

The owner confirmed the installed recording overlay is fixed. [PR #39](https://github.com/ManoloRemiddi/augmentor-agent/pull/39)
merged as `ea1c620569f98a8a72b8682fc647b4c476ecd7ac` after all 28 final-head
checks passed at `08510c30b043490da05ec34bcede696d3842f66f`. Its merge tree matches
the reviewed head. Saved enabled dictation now restores automatically after login;
the Linux recording pill keeps its static border/cancel elements during the
circle/waveform animation on WebKitGTK 2.54. The source/native/installed regression
proof and unchanged settings are recorded in [Handy integration](HANDY-INTEGRATION.md).
Actual reboot acceptance remains separate from verified automatic component startup.

## Publication preparation

Preview 3 is being prepared as one matching source cohort for Linux, Apple-silicon
Mac and Windows x64/ARM64. All platform customer packages and their required native,
installer, application and SDK qualification gates must pass at the frozen source
before publishing any platform. Release tags, source identity, full file sizes and
SHA-256 values will be recorded here after qualification and anonymous full-byte
verification. Website download/checksum/copy-prompt links change only after all
platform assets are published and verified. The older [October 3 preview-2 bytes](HANDY-DOWNLOADS-2026-10-03.md)
remain immutable and public until this new cohort is ready.

Models and personal settings are not bundled. Mac/Windows physical microphone,
permission and cross-application typing acceptance remain separate. Existing
unsigned/ad-hoc status and no automatic-update claim are retained. Windows must
not install preview 3 over another build; follow its bundled maintenance guide.
The owner's compatible 0.2.11 deployment remains separate and is not replaced by
customer package tests. Preserve working conversations and DSH/speech selection.

## October 5 publication pause checkpoint

The owner requested a pause to restart their computer at `2026-10-05T10:19:15Z`.
Customer source remains frozen at `3d1e6153f1e3aed86f56d915d60cd1d55ea49190` on
`release/handy-preview-3`, with [draft PR #40](https://github.com/ManoloRemiddi/augmentor-agent/pull/40).
PR #39 is already merged. Seven of eight required workflows pass; the full
Windows application gate remains in progress on ARM64, while its x64 fourteen-stage
installation/repair/recovery/removal job has passed. Hosted qualification can
finish independently of this computer. Local transfer/staging workers are stopped.

Completed retrieval receipts exist for Linux, Mac, Windows x64 customer bytes
and Windows x64 native evidence. Linux verifies all 20 archive checksums and
matching tracked source; Mac verifies its DMG digest and managed-setup reports.
The ARM64 customer transfer is incomplete and must be resumed/reverified; its
native evidence and final gate remain outstanding. Preview-3 release drafts are
private and incomplete. Draft discovery must use the authenticated release list,
with a fresh response/retry after creation; the tagged endpoint may return 404
until publication. No draft is a published customer release.

The website candidate is saved on its own `release/handy-preview-3` branch.
All 15 website tests pass. It is not merged or deployed, and public website
downloads still select preview 2. Resume by checking the exact-source results,
finishing receipt-verified downloads and all 35 draft assets, merging PR #40,
publishing the prepared matching cohort, anonymously hashing every public file,
then merging/deploying and verifying the website. Publish final owning records
without moving immutable customer tags or modifying the owner’s installed app.

Qualification runs at the checkpoint:

- [Matched Linux and Mac](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37289881200): passed.
- [Windows customer packages](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37289880919): passed.
- [Shared application and installed packages](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37289881123): passed.
- [Windows full application](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37289932600): pending ARM64 full application.
- [Windows installer](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37289936481): passed.
- [Mac product](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37289941015): passed.
- [Windows desktop](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37289944854): passed.
- [Application SDK platforms](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37289949607): passed.
