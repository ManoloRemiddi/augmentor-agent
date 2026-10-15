<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Pi voice integration

## Native and Browser controls — October 16, 2026

Pi Host now advertises the source `voice` capability. The Native client and
Browser initialize response expose it only when that Host advertises it; older
Hosts leave the control unavailable. Existing orb placement/gestures, hold/lock/
hands-free state machine and common device/playback engine remain unchanged.
This is source integration, not an installed or live-speech qualification. The
original Harness web GUI still needs its separate voice-plugin entry point;
its HTTP gateway continues to deny private `voice.ticket` and `voice.close`.

Native prepares the ordinary Pi workspace/model/session and subscribes before
requesting a scoped ticket. It sends **only final** ASR text through the existing
Controller with explicit voice mode, including in-turn steering. Normal Send/
queued edits stay typed. A retired voice object's request cannot enter a newer
same-chat connection. Browser uses the same Python VoiceSession, forwards native
events for completion, validates current chat and unknown receipts, and sends
spoken corrections through the public Pi steering path. Browser controls can
cancel pending setup without first making a serialized catalog read. Navigation,
settings saves and EOF close speech; accepted operations/workers settle before
connection/process shutdown. No second agent loop or copied UI is introduced.

Each Pi client generates an `openId` for setup/close. It is an ephemeral local
opening identity, separate from the ASR request ID and private companion bridge
secret. Matching opening IDs protect pending, active and closing ownership;
a refused contender's automatic cleanup cannot close an existing actor. Ticket
responses keep the original four fields. Trusted internal Stop/orphan/shutdown
and deliberate legacy unscoped close retain root-wide cleanup. No opening is
restored after restart. Clients cancel immediately, then retire any late queued
ticket after preparation settles; a new local lease stays blocked until joined
close finishes. Native reservations also keep maintenance busy during cleanup.

A retained actual cold-Host control shows that close previously returned while
`load()` was still running, allowing a later ticket. The scoped transport now
owns an optional preparation callback before that public SDK load begins, and
Close/Stop/shutdown join it. The first driver mistakenly held initial session
creation before entering its cleanup-protected test region; that 25-second
cancellation is retained and its owned gate was released. The corrected cold
setup control fails before the fix and passes after it, without changing bounds.

Initial surface tests exposed a missing Pi workspace adapter method and a
fixture using numeric frame IDs with Pi's string correlation contract. The
Native adapter and fixture are corrected; Browser timeouts were not increased.
A later competing-Browser driver correctly hit the broker's one-executor guard.
That guard remains: the corrected contention proof uses a separate real shared
audio worker/private-IPC actor against the existing Browser lease. No executor
or scope guard is weakened to make a test pass. Focus 76/76 and native/controller/
maintenance 145/145 pass. Full source/fresh ordinary and isolated controls remain
pending in this implementation checkpoint.

Preceding [SDK run 38810763428](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38810763428)
at **6db75c8f** passes Linux and macOS overall. Windows's expanded step retains
**73 cases: 46 pass/13 fail/13 cancelled/one existing POSIX-only skip**. Newly
included provenance fixtures pre-created ordinary Windows roots before the strict
ACL helper, cleanup refused an executable identity, and memory/Host cases timed
out. Fresh Windows provenance/native-memory roots now use the existing atomic
private creator; no guard, deadline, concurrency or skip is relaxed. Remaining
cleanup/timeout causes and new-head Windows qualification remain open. Earlier
export settlement and Office/libvips packaging notice gates are not resolved.

A compatible separately qualified Pi companion is still required: old Codex-only
health advertisements refuse before tickets. The private speech checkout and its
four changes remain untouched/unpublished; tests use independently authored
protocol peers and fixed PCM, not real ASR/TTS or private service source. Qwen/
Breeze stay on RTX 5090 with existing context/concurrency/precision and CPU ASR/
VAD. No running/review artifact, installed selection or service is changed.

## Spoken and typed input — October 15, 2026

This dated **cc6bbac5** checkpoint predates the Native/Browser binding above;
its disabled surface-capability status is historical.

`session.prompt.inputMode` defaults to `text`. A new `voice` admission requires a
canonical `resonant-voice:<lowercase UUID>` identity, a connected operator and a
live scoped Pi bridge. A name alone never supplies mode or speaker identity.
Already admitted exact duplicates can be confirmed after disconnect; reuse with
changed text or mode refuses. This is trusted local product attribution, not
speaker authentication. Surface voice capability remains disabled.

Queue schema 1 keeps existing text shapes/fingerprints. Spoken rows retain
`inputMode: voice` and a mode-bound fingerprint through terminal receipts and
cold recovery. Explicitly continued waiting speech retains that admission even
without a live bridge; it does not reopen playback. Unknown outcomes still stop
replay. Editing undispatched speech creates a fresh typed identity while retaining
the removed original's spoken receipt. Goal/delegated input cannot be spoken.

The public SDK's delivered user event selects current transcript/style mode.
Spoken replies receive concise conversational guidance; a subsequent typed input
explicitly restores ordinary formatting. Text-only conversations gain no style
section. A public `Agent.streamFunction` request copy applies the section **after**
Pi's final system projection; tools, executable policy, model/options and native
messages remain intact. Manual compaction and standalone improvements bypass it.
Context provenance reports the managed contribution and literal presence in the
final provider system field, subject to existing capture/bounds; it does not claim
that a model obeyed the style. Codex retains its existing public return shape and
exact style wording through the shared authored prompt function.

[Managed memory](CONTROLLED-MEMORY.md#pi-interaction-mode-and-native-briefs--october-15)
recalls the admitted mode and records original submitted human text and assistant
text with delivered mode. Goal/delegated user events and unadmitted extension
follow-ups are not human memory receipts. New unattributed replies are excluded.
Legacy events without mode retain their prior text interpretation. A typed
correction changes style/capture mode immediately within the same SDK turn;
recall remains the register consulted at that turn's start. Historical branches
retain their brief's origin mode independently of the new question's style.

Initial testing retained an incorrect test read of Codex's return envelope and
reuse of closed provenance, then two queue fixtures that had not actually paused
the idle queue. A real Host failure showed that Pi's memory-forced system
projection erased a section added in `context_with_system`; stream-time composition
corrects that boundary. Later original-content checks were corrected for Pi's
provider text-part array. Existing Codex native coverage initially used system
Python without QtTest; qualification uses the established isolated interpreter.
No deadlines, guards or skips were relaxed. TypeScript/build and the focused
83/83 set pass with the established Qt interpreter. At **cc6bbac5**, full source
and fresh ordinary each pass **714 cases: 712 pass/two existing optional skips/
zero failures**, **123 files/all 53 Harness Chromium files**, two workers and
unchanged deadlines. All **1,057 compiled/3,361 tracked inputs** match at freeze.
The 16 actual Host cases include same-owner steering and cold/edited queue input;
the real native SDK child/cold proof preserves voice and text recall registers
with no recall/tool replay. Two separate copies that remove live admission or
typed style reset each fail the intended real Host test. The 22 notice/packaging/
private-source cases and tracked/branch-history gate pass. An initial packaging
command named two absent modules (six actual cases passed, two loader errors);
the corrected four existing modules supply the 22-case result. The first generated
GUI parity assertion expected exact bytes: only one spreadsheet chunk reference
and four source-comment paths differ, with normalized code equal. Supplier,
controller/layout/CSS, Node and 151 production npm instances stay unchanged.
[Portable qualification and complete roster](../release/harness-pi-input-mode-qualification.json).

Ten sealed inventories/eleven review owners, the selected configuration, canonical
38 changes, private companion's four changes and six model/service configurations
verify preserved. Qwen catalog returns HTTP 200. Breeze remains failed/zero PIDs
and voice inactive; RTX 5090 has 2,012 MiB free against its existing 2,828 MiB
startup requirement. It is not retried or moved and no model settings change.
The current MX review remains application **8c159cb7**, without this new input-mode
or Host-speech implementation; no new artifact is staged or activated.

The preceding hosted run [38806598923](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38806598923)
passes Linux and macOS overall at **d491e22b**. Windows advances through Host
startup but refuses the fixture's raw token file ACL. The fixture now atomically
creates that protected file through the existing private writer before replacing
its raw bytes, preserving the speech protocol and ACL checks. Corrected hosted
Windows behavior remains unqualified. Validation [38806598830](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38806598830)
stopped on npm ECONNRESET; macOS packaging [38806598832](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38806598832)
retains the Office MPL/libvips LGPL notice-review refusal. Neither is silently
retried or presented as passing. The older Windows export-settlement failures
remain separate. No private speech source or owner data is copied; the original
GUI, current MX review, installed selection and services are unchanged.

## Platform fixture correction — October 15, 2026

This dated fixture checkpoint is superseded for hosted status by the
[spoken/typed checkpoint above](#spoken-and-typed-input--october-15-2026).

Fixture source **760dd242** preserves the runtime at **999c1f5f**. The completed
[38804829700 run](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38804829700)
passed Linux overall. The macOS voice step passed 36/37, including every actual
Host case; its preview assertion expected a temporary-directory alias rather
than the reader's canonical path. Windows passed 24/37: the same path assumption
failed, and twelve Host cases stopped before startup because their speech
fixture pre-created an ordinary directory that the private ACL helper correctly
refused. No Windows Host/speech behavior was qualified by those failed cases.

The corrected preview still submits its alias path and now requires the actual
file's `realpath` namespace. Speech fixtures create a fresh unpredictable Windows
directory through the existing atomic private creator. Existing directories are
not repaired and no security check, assertion meaning, timeout or skip is relaxed.
All 37 matching cases pass locally on Linux; corrected Mac/Windows hosting
remains pending. The earlier Windows export-settlement failure is separate and
unresolved. [Portable failed-run and correction record](../release/harness-pi-voice-platform-fixtures-20261015.json).
This changes fixtures/documentation only; installed/review artifacts and model,
voice and GPU configuration remain unchanged.

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
