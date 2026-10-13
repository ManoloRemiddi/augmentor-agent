<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Recorded provider requests in original Trajectory

The original DSH Trajectory inferred request controls for every unmatched assistant
step. Pi can emit an empty aborted assistant receipt after a tool Stop without a
new provider payload hook. That receipt must remain visible, but it cannot attest
another provider request, request timing or cumulative request usage.

The Pi binding enables an optional recorded-only mode in the copied MIT
`TrajectoryView`. Only entries in the existing projection's observed request list
receive the original numbered request controls. Unmatched assistant messages,
interrupted output, tool rows and stable detail selection remain in the ledger.
There is no temporal/sequence-based attribution to a neighbouring request, no
change to the execution owner, and no claim that an unobserved adapter made no
network call. The default upstream mode remains unchanged.

One existing supplier file has a prominent modification notice and recorded
original/adapted hashes. Original layout, widgets and all CSS are unchanged. The
580-file MIT selection and the 108-file Apache-2.0 `dsh-context` selection retain
their own licences. No dashboard source, dependency pin or licence body changes.
Compiled and staged notices include the adaptation.

The actual Pi SDK/isolated-provider/Chromium regression reproduces the old
behaviour: one wire request yielded two controls after Stop. Corrected source
shows one control after Stop, then three controls for exactly three wire requests
across two Host turns, including after cold Host reopening. Existing nested
argument/read/error/selection and byte-identical-history checks remain required.
The first focused run fails on the old compiled view; corrected focused checks
pass 14/14. Strict source check and build pass on Node 24.19.0.

Source, ordinary assembly and immutable installed qualification are recorded
separately below. Linux evidence does not establish physical macOS/Windows or
other-distro acceptance. This shared presentation binding adds no OS adapter;
further OS implementation awaits owner MX feedback. Full Harness migration,
live-provider, privacy, public-distribution and platform gates remain open.

## Source qualification — October 13

Strict check/build and the exact 72-file MX cohort pass **369/369**, with Node
**24.19.0**, two workers, matching isolated QtTest and unchanged deadlines; five
notice/workspace packaging cases pass separately. The source change touches one
existing supplier view and its explicit provenance/compiled notice, with no new
package or supplier CSS changes. The earlier 14-case focused pass and failing
old-view regression remain distinct evidence. Private logs/screenshots stay local.

The completed preceding publication head **38c7b0f** has 24 completed checks,
including eight failures: Windows command/jobs (x64/ARM), Windows contracts,
Windows Native (x64/ARM), macOS bundled runtime (14/26), and Debian. Packaging
checks may be skipped; this source qualification does not close those failures
or establish platform acceptance. Ordinary and immutable qualification follow
from a separate artifact before replacing the selected private MX preview.
