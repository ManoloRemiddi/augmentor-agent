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

## Ordinary and installed MX qualification — October 13

Runtime **1feaac8376d38a5a739b059e226bf312bd06ed5c**, private release **20261013-082620-e77f3b09**,
product **0.2.13**, artifact **89829618c08be141af900cf630142df8e37e92a247745dfb608f302bdeecd125**, is selected and running.
The separate ordinary assembly passes the same **369/369 across 72 files** and
five packaging cases with matching Node/QtTest, two workers and unchanged deadlines.
It preserves 20,801 dependency files, 151 npm instances, nine native/Wasm
executables and 783 licence files. Only GUI SOURCE.json and the compiled
modification notice differ among the licence/provenance files; all licence
bodies, dashboard records, package pins and native bytes remain identical.
The source graph contains 663 compiled files and 580 MIT/108 Apache supplier records.

The immutable candidate passes **52/52** focused argument, nested tree/Stop,
original DSH/Context, shortcut and Chromium cases. Actual Host/browser tests use
the candidate's bundled Node and compiled GUI/runtime; pure drivers match the
assembly source. Numbered controls are one after the first tool Stop and three
after both turns/cold Host reopening, matching the recorded wire requests.
The first invocation tried tests inside the distribution, which deliberately
excludes them; rerunning the matching source drivers against the immutable
candidate completes qualification. No candidate file was patched.

Fresh preview audits find all nine maintenance counters zero and Native idle
with no draft. Guarded shutdown verifies the previous processes actually exit;
activation uses the supported updater and stable launcher. The actual Host
**1943491** runs the candidate's own Node 24.19.0/main; Native **1944321** uses
the selected root and existing exact Python venv. All **23,894** inventory entries
verify before and after original-GUI reads. The first standalone identity probe
omitted the required host.hello handshake; a supported handshake verifies the
actual process before Native startup. Both diagnostic outcomes remain local.

The twelve existing histories/queues and session identities remain unchanged,
with zero new placeholder/request. Of 247 saved original files, 243 remain
identical; one journal keeps its exact old prefix plus one session/close and one
session/load; three related index/counter derivatives change. Draft/attachment
bytes, settings values/revision, model/auth profile presence/bytes, production
desktop selection and llama-server executables/arguments remain preserved.

Installed owner acceptance opens original Context Insights through the existing
private profile: eleven nonarchived retained sessions, seven newest available
contexts, zero read failures/partial reads/usage gaps. The old 21 calls retain
explicit older/unlinked timing coverage; no missing SDK timings are invented.
This is a retained-data GUI check, separate from authored-provider inference
tests. The original dashboard remains open for owner feedback; its screenshot
and all private proofs stay local. No owner prompt, credential edit, model
configuration write or endpoint discovery is performed. Earlier releases remain
immutable comparators. Full migration/live/privacy/public-distribution/platform
gates and the preceding CI failures remain open.
