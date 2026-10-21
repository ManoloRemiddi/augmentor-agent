<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Attachment upload maintenance safety

## October 11 implementation

The authenticated Harness attachment carrier now reserves a Host upload count
before reading the HTTP body and retains it through immutable attachment storage.
Previously, body reception happened outside `activeUploads`, so a slow transfer
could appear idle to guarded shutdown. The original DSH picker, cards, image
viewer, layout and supplier source are unchanged.

`Host.receiveAttachmentUpload` owns one count per accepted carrier. It checks
conversation authority before reception and again after reception, and releases
its count once in `finally`, including read, cancellation, size-limit and storage
failure. The existing `uploadFile` entry uses the same lifecycle. Completing one
carrier cannot release another. Shutdown continues to use the existing upload
veto; no new RPC, SDK owner, retry or provider request is added.

The existing operator/inspection/origin checks and twenty MiB file bound remain.
An announced oversized body is refused before reservation; an oversized chunked
body releases its reservation without a receipt. Read-only inspectors cannot
upload. This closes the body-reception gap; it does not persist unsent browser
drafts or restore browser-owned File objects after a full reload.

## Source qualification

Source checks/build and **256/256 cases across 40 files** pass, with zero failures,
skips or cancellations, two workers, unchanged deadlines and the prepared QtTest
interpreter. Four authored contract cases cover delayed reception/storage,
independent failures, authority revocation and existing file/image entry points.
One actual public Pi SDK/Host/HTTP case verifies slow and concurrent reception,
guarded `host.shutdown` refusal, completion/abort settlement, both announced and
streamed bounds, read-only/unauthenticated denial, unchanged history, zero provider
requests and final accepted idle shutdown. It uses only authored bytes and an
isolated synthetic provider; it is separate from owner MX acceptance.

Two retained test failures initially could not observe the chunked carrier after
an intentionally incomplete announced-oversize request. Each controlled request
now uses a fresh socket and explicit chunked framing. No production guard or
deadline was relaxed. Focused **10/10** and the full source cohort pass afterward.

Ordinary bundled-Node assembly and installed MX adoption are qualified separately
below when complete. Existing supplier licences, dependencies and model/speech
settings are unchanged. This shared Host change adds no OS adapter; Windows,
macOS and other distro acceptance remain deferred for MX feedback. Full Harness,
draft durability, migration, privacy and public-binary gates remain open.


## Installed MX qualification — October 11

Runtime **71c8295331e3ef6f1a3fadecdee2b3e16dde75cf** is selected and running in
private MX release **20261011-230903-26a85087**, product **0.2.13**, artifact
**a4e02988958781788a17c4e78018cbc7219c6e510e4ed41f0793584d24c3c70c**. The fresh
ordinary bundled Node **24.19.0** also passes **256/256 across 40 files**, zero
failures/skips/cancellations, two workers/unchanged deadlines/prepared QtTest.
All 478 compiled files match source. Compared with the preceding installed
Context-preferences release, only the two changed Host modules and their generated
maps/declaration differ; the complete GUI graph and CSS are byte-identical.
All 19,160 production dependency files, 131 npm instances, six native executables,
723 licence files and 96 browser notice records remain preserved.

Normal stage, idle/draft-empty Native maintenance close, one guarded Host shutdown
and completed activation precede the stable Host launch. Its exact selected Node
and entry root are verified before Native launch. Both running roots match the
selection; Native is online/model-ready/idle. All **21,787 installed inventory
entries** pass before and after original Context/Insights/plugin-card reads. No
owner inference, tool, upload, preference mutation or new conversation is used
for installed acceptance; the real HTTP failure/maintenance cases remain isolated
synthetic evidence. The settled original Insights dashboard stays open at the
normal 513×715 viewport for owner feedback.

All eleven histories and queue identities and all private profile settings are
preserved. Of 243 saved files, **233 are byte-identical**; four original journals
retain exact old prefixes with only two saved-title/session_info, two session/close
and two session/load appends, plus six corresponding counter/index derivatives.
Production selection and the existing model router/model/speech/GPU/context/
concurrency/precision/CPU ASR/VAD settings remain preserved. A comparison first
expected only two generated JavaScript paths; the retained audit accounts for
their two source maps and Host declaration as well, without changing source or
relaxing GUI/dependency checks. This qualification-only follow-up changes no
selected artifact. Full draft durability/migration/privacy/public packaging and
physical platform gates remain open; DSH stays available.
