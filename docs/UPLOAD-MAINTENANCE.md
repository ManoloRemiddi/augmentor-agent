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
