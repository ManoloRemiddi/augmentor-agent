<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Original Timing Stats on Pi

The original Apache-2.0 dsh-context Timing Stats card, donut, slice rows and
session-time strip now receive measured public Pi SDK lifecycle data. The existing
Context tab/sidebar/modal and Insights layout/CSS remain intact. The runtime adds
private observation records rather than another execution owner or network
reporter. The original public 0.68.1 timing fold was inspected at
[2c8095c](https://github.com/bowenliang123/dsh-context/blob/2c8095c34da3fcef729a01437d2df65c83e08499/src/host/fold.ts);
Pi capture uses its supported SDK boundaries and a separately authored adapter.

## Measurement and durable records

`step/start` and `step/end` pair by an opaque step ID and the same host turn.
They describe public SDK `turn_start`/`turn_end`, which are individual model-loop
steps, distinct from the application's complete foreground turn. Durations and
interval offsets use one monotonic clock per step. The recorded UTC start anchors
the presentation only; a changing wall clock is never subtracted for duration.
SDK preparation between steps and user idle time outside them are excluded.
Manual summary requests retain their existing model durations and are not
invented SDK steps.

The versioned `augmentor-sdk-step-timing/1` summary contains measured model
windows, first observable stream markers/deltas, reasoning/text/argument marker
windows, tool lifecycle intervals and pending question/approval windows. Model
wait starts at the managed payload hook after earlier transformations. Stream
windows end at assistant-message settlement; they measure observable SDK events,
not provider-internal prefill or decoding. Block counts are actual SDK starts;
unsupported delta-only streams retain unsplit generation and omit the strip.
No inferred throughput is supplied.

Tool windows run from public `tool_execution_start` to `tool_execution_end`,
including validation, approval and waiting; they do not prove a tool's effect.
Nested/parallel intervals each retain their true duration and parent ID. The
original ring clamps overlapping sums; the strip tiles their union once and
fills unclassified intervals with Other step time. Pending UI intervals identify
the actual loaded owner, including delegated owners; they contain no question,
answer, tool arguments or credential values. These are observed pending UI
windows, not a claim that all concurrent work stopped. Per-step time minus their
clamped union is retained separately; the existing Context Trend remains its
recorded model-duration measure, so old and new points do not silently mix units.
Timing Stats totals include the complete step window and therefore include these
pending intervals.

Superseded, interrupted, disposed or host-ended steps without SDK `turn_end` get
an explicit `step/incomplete` record. Missing/duplicate/mismatched boundaries,
invalid intervals do not contribute totals. Completed steps with dropped or
unclosed windows retain their measured values and are explicitly marked partial.
Captures are
bounded to 512 entries including stream blocks, 128 blocks per model and a
conservative 6,000-byte capture budget; a tested summary stays below 8 KiB even
with escaped names. Dropped/unclosed observations remain partial. Per-tool
rankings are bounded to 128 names while aggregate counts/durations remain intact.
Private metadata remains available with payload capture disabled. Existing
request/body/native evidence is not modified or replayed.

## Coverage and original presentation

Context and Insights show completed, partial, incomplete/invalid and older/unlinked
coverage. Older histories without these records stay unavailable; durations are
not reconstructed from unrelated timestamps or invented by adding model/tool
sums. Timings cover loaded retained metadata and measured steps, not a guarantee
of complete all-history capture. Inspector authority and the existing bounded
metadata/body reads remain unchanged.

Insights retains its existing Recorded model time KPI. Only the Timing Stats card
receives the SDK-step labels/totals, scoped to the original selected session range.
Cross-session totals exclude missing/error/partial metadata reads and preserve
unknown stream splits. The optional supplier seat changes one already-marked
`overviewPanel.tsx`; the original card/strip/CSS and all other 107 records stay
unchanged. Apache selection remains 108 files, 92 verbatim/16 marked, with original
Copyright 2025 bowenliang123/licence/source hashes and updated adaptation notice.
DSH MIT GUI remains 580 files. No supplier Host, pricing/registry fetch, telemetry
exporter, credential UI, model configuration or speech/hardware change is added.

## Qualification and deployment boundary

Deterministic clock/metadata tests cover stream buckets, nested/parallel tools,
UI waits, gaps/duplicates/invalid summaries, privacy pruning, byte bounds,
delta-only/mixed streams and diagnostic failures. An actual isolated public
SDK/Host/provider test records two model steps and a real pending question;
cold reopen preserves timings, native history and provider-request count.
Original Chromium Context/card/strip and Insights aggregate checks preserve
history/provider requests and existing layout bounds. They use authored fixtures,
not owner model prompts or physical speech.

The first focused real question test mistakenly used SDK confirm (an approval
request) while waiting for a question; it now uses SDK select. The first full
349-case run has 348 passes and one sidebar fixture failure: added timing events
move a request outside its initial 100-record metadata page. The sidebar check
now derives expected coverage from that actual page, retains the eight-body cap,
and continues all shared-read/scroll/file/role/restart/no-replay assertions without
changing product pagination, deadlines or concurrency. The final strict check and
build pass; the complete source MX cohort passes **349/349 across 68 files**, zero
failures, skips or cancellations, with Node **24.19.0**, two workers, unchanged
deadlines and matching isolated QtTest. Five notice/workspace Python cases pass.
Focused actual Chromium Context/Insights acceptance passes **5/5**. This is source
and authored-fixture evidence; ordinary and installed proof follow separately.

At this source checkpoint, selected/running MX remains model lifecycle runtime
79ee4ff / release 20261013-013249-f43fa0d0; the installed qualification below
supersedes that selection. Source implementation is
**008ef29551406fa08f21508d548603a6f9200f81**.
The full P0/P1 migration, live/privacy/public distribution and platform requirements
remain open; further OS implementation awaits owner MX feedback and DSH is retained.

## Ordinary and installed MX qualification — October 13

Implementation **008ef29551406fa08f21508d548603a6f9200f81** is selected and running
in private MX release **20261013-030020-abfa89ec**, product **0.2.13**, artifact
**5d6596b90da90856cfa1b670bf5be6f6c58c52e0ea3b08786bbc22ae6a19253e**.
The complete source and ordinary MX cohorts each pass **349/349 across 68 files**,
zero failures/skips/cancellations, with bundled Node **24.19.0**, two workers,
unchanged deadlines and matching isolated QtTest. Five notice/workspace Python
cases pass on both source and the ordinary artifact's actual packaging scripts.

The separate ordinary candidate contains **660 compiled files**, **20,801 production
dependency files**, **151 npm instances**, nine native/Wasm executables, **783 licence
files** and 127 browser notice records for 126 versions. It reuses the complete
previously reviewed production dependency seed, including all Photon/QuickJS notices
and the three generated exclusion/override/prerequisite records. Dependency paths,
Node/native binaries and notice bodies are unchanged. Only three source provenance
files differ: the two Apache adaptation records and the browser source manifest.
All other 107 Apache records and all 580 MIT GUI records remain unchanged. Existing
Office/PDF/HTML/spreadsheet/shortcut provenance checks pass.

The supported updater stages a fresh immutable release. Its dist, Node,
node_modules, licences and generated distribution records match the ordinary
candidate exactly. **Thirteen** focused immutable tests pass, including actual
public SDK/Host steps/questions, original Context/Insights/sidebar Chromium and
bounded/privacy/invalid metadata contracts. This is isolated authored-provider
evidence; it does not claim owner live-provider or physical speech acceptance.

A fresh owner-state comparator and actual idle/no-draft checks precede guarded
Native/Host shutdown. Terminal absence is confirmed before activation. Stable
configuration starts the selected Host; its actual Node executable and main entry
are verified before Native starts. Selected/running identities match, Native is
online/model-ready/idle, and all **23,885** immutable inventory entries verify both
before and after GUI inspection. No selected release is patched in place.

Actual owner Insights shows eleven nonarchived metadata entries, seven newest
contexts, zero failed/partial/usage-gap reads and **21 older/unlinked calls** with
no invented measured step times. A separate manual test profile runs the same
immutable Host with an authored deterministic provider: one conversation, two wire
requests, two complete measured steps and one read tool. Original Context displays
the timing ring/stream slices/tool interval/session strip; original Insights shows
the same step totals. Browser reload returns to the original Chat panel; an initial
wait for the unopened Insights panel times out. Explicitly reopening Insights
preserves identical timing card text and the provider request count remains two.
This preparation correction is retained separately from the passing checks; no
panel persistence feature is added. Screenshots/proofs remain private, and the
isolated fixture is closed with both its supervisor and Host terminal.

All **twelve** preceding owner histories and queue items, draft/attachment bytes,
profile values/revision, models.json/auth.json presence and bytes, production
selection and router executable/arguments are preserved. Of 247 saved files,
**243 are byte-identical**; one journal retains its exact old prefix plus one
session close/one load, with three corresponding counter/index derivatives.
No new owner conversation, placeholder or saved original is added or removed.
No owner prompt, endpoint discovery, credential entry or configuration write is
performed. Qwen/Breeze GPU placement and CPU ASR/VAD remain unchanged; canonical
main's 38 pre-existing changed paths are preserved. Earlier immutable releases
and all original comparators remain available.

This qualifies the private MX timing increment. Full migration, live/privacy/public
distribution and platform gates remain open. The previously recorded Windows
Immer build and Darwin Office/libvips licence CI gaps are not resolved by these
Linux checks; see the [CI checkpoint](HARNESS-MODELS.md#ci-publication-checkpoint-and-platform-gaps).
Further OS implementation still awaits owner MX feedback, and DSH remains available.
