<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Original Branch and Fork operation ownership

The original DSH message Branch control and sidebar/keyboard Fork use the existing
Pi Host `session.branch` reply boundary. One supported AgentSession continues to
own each conversation; this presentation correction creates no execution loop.

Previously each click allocated another child ID, and a late history/branch
response could open its child over a newer selection or unsent draft. A single
controller operation now guards duplicate clicks and captures the conversation
epoch. A retired history read cannot dispatch a branch; late acknowledgments/list
refreshes cannot select over another conversation. A changed composer revision
prevents automatic selection while preserving the acknowledged child in the list.
Running/unconfirmed/compaction-blocked and read-only states cannot acquire branch
authority. The original message button uses its existing unavailable seat while
the operation is pending.

A request uses one child identity for its exact parent/message/reply boundary.
An invalid, foreign or lost acknowledgment keeps that identity for an explicit
same-boundary retry; the Host returns its existing child without replaying model
or tool work. A confirmed response must match all four identity fields before
selection. Authoritative rejection releases the intent; a confirmed operation
releases it so a later intentional Branch creates a fresh child. The controller
retains at most 64 unconfirmed boundary identities; it refuses new boundaries at
that limit while allowing existing ones to reconcile. There is no automatic
mutation retry. Current-scope failures retain their rejected Promise contract;
the Pi binding presents one scoped error instead of overwriting its unknown-outcome
guidance. Retired failures have no current-view authority. Unconfirmed identities belong to this loaded controller; durable
recovery across browser process replacement remains a separate migration gate.

Only the authored Pi binding and test driver change. Supplier source, hashes,
licence text, controls, layout and CSS remain intact. This shared binding adds no
OS adapter; actual Linux checks do not qualify physical Windows/macOS. Further OS
implementation awaits MX feedback. Full migration/live/privacy/distribution and
platform gates remain open.

Ten controller cases exercise concurrent history/branch ownership, late reads and
refreshes, changed drafts, exact loaded targets, foreign responses, explicit
reconciliation, known rejection and blocked admission. Original-GUI tests use an
authored provider and hold/corrupt this client's actual RPC responses after the
Host creates its child. They verify original native tool context and unchanged
parent history/request counts. Private output stays local.

## Qualification checkpoints — October 13

The initial eight controller cases reproduce seven failures on the old binding.
Ten corrected cases pass; the original-GUI test passes with the real Pi SDK/Host,
two wire requests and one read, byte-identical parent display/native history,
exact inherited native tool messages and restoration of the newer parent draft
after browser reload. Duplicate pending clicks create one child; corrupting the
next acknowledgment leaves one new child, and an explicit retry returns that same
child. The existing modal is closed before retrying through the original sidebar.
The old immutable runtime **1feaac8 / 20261013-082620-e77f3b09** fails the same
duplicate-click assertion (three sessions instead of the expected two).

Retained driver failures include quoting a CSS attribute inside an evaluated
string, trying to hover a sidebar row behind the original error modal, and
dereferencing the composer during its normal selection-loading gap. The driver
now uses quoted selector construction, actual modal dismissal and ready-state
predicates; no supplier widget, deadline, geometry or outcome assertion is
relaxed. A first full cohort passes **379/380**: the original controller caller
contract expects failed Fork Promises to reject. The implementation preserves
that contract with a scoped presented-error marker, and the old fixture now
enters ready state before exercising a branch. Sixteen focused branch/organization
cases pass after the correction. Strict check/build pass; full source, ordinary
and immutable qualification follows separately.

The preceding published **e8959f6** has 24 completed CI checks with eight failures:
Windows command/jobs and Native on x64/ARM, Windows contracts, macOS bundled
runtime on 14/26, and Debian. This increment does not qualify or fix those
platform failures. Further OS implementation awaits owner MX feedback.

The corrected source passes **380/380 across 74 MX files**, with Node 24.19.0,
matching isolated QtTest, two workers and unchanged deadlines; five packaging
notice/workspace cases pass separately. Strict check/build also pass. This is
source qualification; separate ordinary/immutable and installed read acceptance
follow before changing the selected preview. Supplier records and CSS remain
identical to the recorded-request selection.
