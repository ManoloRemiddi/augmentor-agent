<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Pi voice integration

## Passive bridge foundation — October 15, 2026

Application source `ecab71a4` extracts Augmentor's existing public Codex speech
transport into [the shared bridge](../packages/voice/src/scoped.ts) and adds a
[passive Pi SDK observer](../packages/runtime/src/voice.ts). The selected Pi
`AgentSession` remains the sole conversational owner. The new observer creates
no session, submits no prompt and has no model or device implementation.

This is an internal foundation. **Pi Host RPC, Native, Browser and Harness GUI
voice entry points are not connected to it yet.** The current unselected
[MX export/Context review](HARNESS-MX-REVIEW.md#export-and-live-context-review--october-15)
remains application `8c159cb7` without this source change. Installed selections,
existing review processes, speech services and Qwen/Breeze settings are preserved.
The original GUI and its layout are unchanged.

## Ownership and delivery contract

The owning adapter must call `admit(session, productRequestId, productTurnId)`
only after a durable receipt confirms delivery of an accepted **human** input.
A model observation request ID, request-name prefix, loaded historical message,
autonomous goal or delegated child is not that authority. The observer consumes
only the same owner's live public `AgentSession.subscribe` events with the
matching product turn. It never reads history or uses private SDK fields.

Each public assistant message has a fresh capture identity; text blocks retain
SDK content indexes. Reasoning, tool calls, arguments, results and other session
or turn events are excluded. A final text block must preserve the exact streamed
prefix; only an omitted final suffix is added. Changed or missing blocks fail
closed. Duplicate finals and post-settlement events cannot replay speech.
Aborted/error messages suppress playback. A successful turn receipt with an
unfinished message closes the bridge instead of claiming successful completion.

The shared transport retains private loopback configuration, redirect refusal,
single-use scoped tickets, monotonic event sequences, an eight-second remote
lease, two-second heartbeat, 25 ms text coalescing, 128 queued events, 256 KiB
queued bytes and at most 256 streams per turn. Final text now also checks the
existing 262,144-character stream limit before queuing its body. Stop sends a
newer sequence immediately, invalidating delayed HTTP text and retiring queued
completion. Failure disables forwarding without replaying an uncertain action;
a new connection is explicit. Disconnect and shutdown close their lease.
Existing Codex callers retain their import path and notification adapter.
The existing Codex desktop VM proof records the shared compiled voice module in
its input hashes; no new VM run is claimed by this checkpoint.

## Companion compatibility boundary

The wire remains `resonant-voice/1`. In addition to
`capabilities.scopedHarnessBridge: 1`, Pi requires an explicit additive
`capabilities.scopedHarnesses` list containing `pi` before it requests a ticket.
Ticket and event bodies bind `harness: "pi"`, product session and private bridge
identity; a surface receives only its one-use WebSocket ticket. A Codex-only
capability or an older companion is refused before ticket issuance.

This Pi capability is a **proposed additive companion contract**, exercised by
an independently authored public synthetic peer. No Pi-compatible production
companion version or distribution is qualified or pinned here. The private
Resonant Voice implementation has not been copied, modified, packaged into
public tests or installed. Its existing 0.1.17 Codex development work and earlier
0.1.16 installed speech are separate from this application-source qualification.
Private component changes must stay in that component repository and be tested
and published there before Augmentor pins an exact compatible artifact.

## Evidence and remaining integration

[Portable qualification](../release/harness-pi-voice-foundation-qualification.json)
records the exact source, roster, ordinary-copy comparison and retained failure.
The public [Pi tests](../tests/pi-voice.test.mjs) use scripted speech/PCM and a
local provider. One test runs the actual pinned Pi 1.1.0 SDK through its public
session lifecycle and verifies text forwarding without reasoning. This proves
the observer seam, not the product Host's input authority or an installed speech
service. The seven existing Codex tests additionally exercise its actual pinned
runtime, Native Qt controls and Browser native-messaging path. They do not
establish Pi surface parity or real ASR/TTS quality.

The initial focused run had 16 passes and one teardown failure: the synthetic
peer closed before its proxy/client, causing a refused loopback fetch. Ordered,
joined fixture cleanup corrected it without changing a timeout or product
behavior. That failure is retained; it is not relabelled as a pass. The corrected
17-case run passed; the final expanded focused run passes all 19 cases.

The three-OS Application SDK workflow now includes the same 12 Pi observer cases.
Source and a fresh ordinary copy each pass **673 cases, two existing optional
skips and zero failures** across **118 files/all 53 Harness Chromium files** with
two workers and unchanged deadlines. All **1,051 compiled/3,353 tracked inputs**
match at the application freeze; dependency pins and 615 GUI supplier files are
unchanged. Twenty-two notice/packaging/source-boundary cases pass, as does the
actual tracked-file/branch-history private-source gate. Two isolated controls
removing the Pi capability or final-prefix guard each fail their intended case.
All ten sealed inventories, eleven review processes, installed selection, six
model/service configuration files and the companion's four pre-existing local
changes remain preserved. Source GUI output differs only by a spreadsheet chunk
name derived from temporary build comments; normalized code is equal. The current
MX artifact is not rebuilt or replaced.

Local Linux success is not a macOS/Windows result; hosted status is recorded
separately. The preceding Windows session-export prompt-settlement failures
remain unproven and are not resolved by this voice checkpoint.

Required next work is:

1. Bind Pi Host ticket admission, durable human delivery, Stop, disconnect,
   maintenance/busy guards and exact owner shutdown. Exclude child and goal work.
2. Preserve spoken/typed input identity and truthful memory recall, retained
   transcript mode, native context snapshots and request provenance.
3. Connect existing Native/Browser voice controls and the approved Harness
   entry point without duplicating UI or creating a second agent loop.
4. Qualify and pin the separately published companion, then test actual
   CPU ASR/VAD and Breeze on the RTX 5090 alongside unchanged Qwen settings.
5. Qualify exact packaged artifacts, microphone/playback, interruption,
   hands-free behavior and owner acceptance before enabling or adopting them.

The current Breeze out-of-device-memory failure and incomplete full migration,
platform and installed release gates remain open. No lower context, precision,
concurrency, alternate GPU or workload eviction is introduced by this work.
