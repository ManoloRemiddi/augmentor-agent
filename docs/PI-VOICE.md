<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Pi voice integration

## Host ownership and joined close — October 15, 2026

Host implementation **83d32ea7**, qualified with the **999c1f5f** Permission
notification correction, connects the passive observer to the existing Pi
Host and its durable queue. This is an internal private-IPC bridge:
`host.describe` reports `voiceBridge: true`, **not** the surface `voice` capability.
Native, Browser and Harness voice controls remain disabled/unconnected for Pi.
Spoken-input memory mode and a separately qualified companion are still required
before enabling them. The current MX review, installed selection and services
remain unchanged. [Portable qualification](../release/harness-pi-voice-host-qualification.json).

`voice.ticket` requires the owning Linux/Browser surface, a connected operator,
a human root, idle confirmed work and no archived, delegated or unknown-outcome
state. The same public SDK owner is loaded; it is not replaced or duplicated.
Authority is checked again after loading and after ticket I/O. Incompatible
companions fail before ticket issuance. `voice.close` bypasses the preparation
lane so it can cancel a setup in flight; the private Harness HTTP gateway does
not expose either voice RPC.

A live SDK human event can open speech forwarding only after `queue.delivered`
has saved its receipt. The Host passes the product request/turn identity, never
a diagnostic provider request ID. Identified human steering retains the same
SDK owner; child, goal and unadmitted extension user events cannot inherit the
lease's human identity. An unowned user event suppresses forwarding until another
known human input is delivered. History reads, duplicate prompt admission and
cold inspection do not speak or reopen voice.

Stop starts its speech cancellation before waiting for model/tool settlement.
An active connection remains usable for the next human turn. During setup, Stop
uses the same cancellation path as explicit close. Last-operator IPC disconnect
or subscription transfer closes the lease; another connected operator preserves
it. Archive, compaction/repair, resource reload and maintenance protect pending,
active and closing speech ownership. Shared model/MCP/reasoning changes require
closing voice. An unconditional runtime shutdown joins voice cleanup before
remaining owners settle; a cold process never reconstructs the connection.

Shared close now joins both setup and earlier HTTP delivery. A cancelled setup
never exposes its ticket; if issuance already completed, the client sends a
scoped disconnect. Close remains busy until the older delivery chain settles,
even after its socket closes. Monotonic sequences retire delayed text. Unknown
remote failure is not replayed; the separately implemented companion lease is
still part of its unqualified production contract. Windows connection-file
verification now uses the existing owner-ACL/reparse helper, while POSIX keeps
its private-file mode and owner checks. The Host tests use this real private
configuration reader, not a production test hook or sibling source import.

The focused Host/observer/Codex and affected guard set passes **68/68**, including
12 actual-Host cases with independent speech/provider peers. The initial broader
focused set had **64 pass/three failures**: old preview/reference/upload prototype
fixtures omitted `sessionExports.active`. All three reproduce against the frozen
`ecab71a4` baseline in a separate control copy. Their setup now includes an idle
export owner and the new voice owner; original assertions/deadlines remain.
The earlier TypeScript check also rejected `Promise.withResolvers` under the
existing ES2023 library. Explicit promise resolution corrects that use without
raising the compiler target or runtime pin. Both failures remain recorded.

Final source **999c1f5f** and fresh ordinary each pass **700 cases/two existing
optional skips/zero failures**, **122 files/all 53 Harness Chromium files**, two
workers and unchanged deadlines. All **1,051 compiled/3,356 tracked inputs** match
at freeze; 615 supplier inputs and dependency pins stay unchanged. Two isolated
guard-removal controls each fail their intended Host case, 22 notice/packaging/
source-boundary cases pass, and tracked-file/branch-history privacy checks pass. The initial 700-case source run retained a Permission dialog
failure (697 pass/one fail/two optional skips). A separate real-notification
control confirms its cause; the authored controller correction preserves the
exact original confirmation across confirmed echoes while new peer revisions
still invalidate it. See [the GUI correction and retained control](DSH-GUI-ON-PI.md#confirmed-permission-notifications--october-15).


The preceding Application SDK run
[38798072784](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38798072784)
at **aeb73888** completed: all three OS jobs passed the **12 foundation observer
cases**; Linux/macOS passed overall. Windows again failed two prompt settlements
before export preparation (47 pass/two fail/one existing POSIX-symlink skip in
that step). This confirms neither the cause of that failure nor the new Host
integration on Windows. The expanded three-OS voice step now includes the Host
and legacy guard cases; its qualification is pending at publication.

Remaining work is truthful spoken/typed input and memory/provenance attribution,
existing Native/Browser and approved Harness entry points, an exactly pinned
companion artifact, actual CPU ASR/VAD and Breeze on RTX 5090, physical audio and
hands-free acceptance, packaged/installed qualification, Windows investigation
and full migration. No model, service, GPU placement or GUI layout is changed.

## Passive bridge foundation — October 15, 2026

Historical foundation-only checkpoint; the Host wiring statements below are
superseded by [the current integration](#host-ownership-and-joined-close--october-15-2026).

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
