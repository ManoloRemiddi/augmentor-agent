<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

[Original DSH microphone](HARNESS-DICTATION.md) now reuses ten verbatim MIT
inputs for recording/waveform/Stop/Cancel/device selection and editable drafts.
Trusted Pi recognition owns credentials, bounded acknowledged PCM and scoped
cleanup; it starts no conversational owner and never sends a prompt or TTS.
Development Host/Chromium checks cover rootless/running turns, the full ten-minute
budget, draft conflicts, read-only denial and both themes. Private 0.1.22 is
qualified separately; shared 0.1.19 pins, current review and installed/services
remain unchanged. Frozen acceptance, isolated MX review, physical audio and full
migration remain open.

# Pi voice integration

## Audio processor lifecycle and hosted POSIX qualification — October 16, 2026

The private companion's next **0.1.21** source
**2d25ba0c52b42f1ed693465cc63b7d63ea0dce8d** fixes a reproduced missing-FFmpeg
pipe-drain failure and joins its owned input/processor before cleanup settles.
Cancellation checks raw passthrough and buffered transformed PCM, retaining the
existing processing settings and SIGTERM path. A failed processor returns a
readable error; speech is not replayed. No agent owner, prompt input mode,
conversation/memory contract, GUI layout or model/device placement changes.

Source and fresh ordinary copies each pass **67 Node cases: 64 passed/three
existing Windows-only skips/zero failures or cancellations**, **15 Python cases**
and **four packed-companion actual Pi Host/SDK/Native/Browser cases** with two
workers and unchanged deadlines. Actual isolated DSH 0.1.5 lifecycle and packed
plugin install/compose/remove pass. All **90 tracked component/66 archive inputs**
match. The new local candidate SHA-256 is
`69313b72e92c60dcf206e9322e1620dcedff2773b51588a2de407e4409780571`.
The older add6fffb archive below remains historical; no shared pin changes.
[Portable acceptance](../release/harness-pi-audio-processor-qualification.json).

[Hosted run 38822272331](https://github.com/ManoloRemiddi/resonant-voice/actions/runs/38822272331)
at this exact component source passes **Linux x64 and macOS ARM64** full Node
suites, each 67 cases/64 passes/three existing Windows-only skips, zero failures/
cancellations. A pinned source-built FFmpeg **7.1.5** tool supplies the missing CI
processor. Source/ordinary Linux recipes independently produce identical binary
bits. Both actual processor safeguard-removal controls fail their one case as
intended: removing buffered-output cancellation emits post-abort PCM; removing
joined exit returns while the owned processor is still running.

The tool selects PCM/WAV and tempo/volume/resampling support plus FFmpeg's command
line dependencies. Source digest and configuration are locked; network,
autodetection, GPL and nonfree configuration are disabled. FFmpeg remains a
separate **LGPL-2.1-or-later CI tool**, excluded from the companion npm payload and
public application/tests/CI; the companion's own source stays MIT. This does not
adopt or redistribute a new product processor. See the
[official release](https://ffmpeg.org/releases/ffmpeg-7.1.5.tar.xz) and
[licensing](https://ffmpeg.org/legal.html). Windows x64/ARM64 still stop at their
working-FFmpeg prerequisite. No audio assertion is skipped, and the overall
workflow remains failed; actual Windows app/audio support is not qualified here.

Retained failures include the original missing-process control (unsettled await,
exit 13), first buffered-PCM cancellation failure, and initial minimal configure
names that omitted raw PCM support. The latter focus reports seven passes/two
EPIPE failures; its complete development set reports 67 cases/62 passes/two
failures/three existing Windows skips. Selecting `pcm_s16le` in configure and
requiring a real PCM smoke test corrects the tooling. Prior cancelled hosted
runs and failed prerequisite checks remain distinct from the qualified POSIX run.
No bounds, worker counts or old skips are relaxed.

These package/application integration checks still use a synthetic provider,
ASR, PCM and audio devices. Recognition quality, Breeze generation and physical
listening remain unqualified. No private source, fixture, archive or CI tool is
copied into the public application. Reproduction requires private component
access. Public application **4cb16513**, official Pi **1.1.0**, preserves all
**3,366 tracked/1,057 compiled inputs**; the private external test copy's entire
**27,067-entry inventory** is unchanged before/after, with no bytecode writes.

Postflight re-verifies ten sealed reviews/eleven owners, selection, 38 canonical
changes, four original companion changes and six service/model configurations.
Qwen models return HTTP 200. Breeze remains failed/voice inactive with 2,012 MiB
free on RTX 5090 against its existing 2,828 MiB admission requirement. The current
MX review stays **20261015-211446-7474ddb2/application 8c159cb7**; it has no new
speech artifact. Private distribution/pin/adoption, original DSH web microphone
wiring, physical speech, full migration/owner feedback and later OS/public release
gates remain. This component result also leaves application Windows and Office
notice/public-rebuild packaging gates open.

## Original DSH web microphone — October 16, 2026

The complete pinned public DSH snapshot **d7432673** includes an optional original
web voice interface, outside the current selected GUI supplier subset:
[`@deepseek-ai/dsh-experimental-client-ui-voice-input`](https://github.com/deepseek-ai/deepseek-harness/tree/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/experimental/client-ui-voice-input),
version **0.2.1-alpha.2**, with **MIT** in its package metadata and the upstream
MIT copyright/license. Its bundle is MIT as well. The original microphone uses
`conversation.input.activity`, between the model selector and Send. It provides
the original recording toolbar, waveform, Cancel/Stop, device picker and setup/
readiness views. This is a reusable original DSH interface for the remaining web
entry point; a newly designed composer is unnecessary.

The upstream workflow transcribes into an **editable draft**. It creates no
conversation event and does not automatically send, speak replies, maintain a
hands-free conversation, stream captions or listen for a wake word. Revision-bound
insertion retains a transcript for explicit insertion if the draft changed.
Session changes, cancellation, page hiding and disposal retire late results and
join audio resources. See the [original subsystem](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/docs/subsystems/voice-input.md).

Reuse the original public UI/components and attribution, then adapt recognition
to Augmentor's existing CPU ASR service through an authenticated, bounded and
cancellable Host contract. The upstream bundle installs its own SenseVoice
runtime; selecting UI source does not authorize replacing the existing recognizer,
downloading that runtime or changing model/device placement. Draft dictation must
stay distinct from admitted spoken/hands-free submission and remain editable.
Private HTTP ticket/close methods remain denied while a scoped recognition
adapter is designed and qualified. Original supplier selection, composer/settings
integration and retirement/late-result proofs are still implementation work.

This is read-only source/license analysis, not a shipped microphone control. The
full snapshot has **14,987 files**; all **615 existing supplier entries** verify
against their recorded upstream source paths/hashes and selected-body hashes,
including 20 already recorded body adaptations. New candidate file hashes and the
MIT license digest are in the [portable audit](../release/harness-original-web-voice-audit-20261016.json).
No new supplier code, UI layout, dependency, ASR model, installed/review artifact
or service configuration changes in this audit.

## Companion package acceptance — October 16, 2026

A separately built **Resonant Voice 0.1.21** candidate now explicitly supports
Pi's scoped bridge. Its [private draft PR #5](https://github.com/ManoloRemiddi/resonant-voice/pull/5)
and component source **add6fffbec1ddf16c8369333652c0f9e5eade6ec** retain 0.1.19's
private configuration and joined maintenance while porting the scoped Codex
contract. A pending opening can now be closed before microphone redemption;
its exact ticket is revoked even if another same-ID harness owns audio. Pending
heartbeats and sequences carry through redemption, abandoned tickets expire on
the host lease, and a surface cannot renew a missing host. Task Stop keeps voice
connected; Close retires it and normally disposes the worker. Existing DSH ticket
shape and speech settings remain compatible. The distinct version avoids the
separate DSH 0.2 branch's 0.1.20; this candidate qualifies legacy DSH 0.1.5-rc.1
and Pi 1.1.0, not that DSH 0.2 adapter.

This is **private component acceptance**, not a public speech-source import or
installed voice update. Application source remains **4cb16513**. In the private
component repository, source and a fresh ordinary copy each pass **61 Node cases
with three existing Windows-only skips**, **15 Python cases** and **four actual
Host/SDK/Native/Browser cases** against an installed candidate tarball. Existing
Native orb/hold/release/original Send and Browser audio worker/spoken steering
are exercised without layout changes. Actual pinned DSH lifecycle and disposable
tarball install/compose/remove pass. All 85 tracked component/64 archive files
match; a separate pending-revocation removal fails its one test as intended.
The archive SHA-256 is
`14ea3b49a93f7841652cce9d0bb9ec253127b9aee9494dbc74f26378e84a5cb1`.
[Portable record](../release/harness-pi-voice-companion-qualification.json).

The provider, ASR, PCM and audio devices are synthetic. These tests do not certify
recognition quality, Breeze generation, real microphone/playback or listening.
No private source, test fixture or candidate archive is added to the public
application/tests/CI. Reproducing component acceptance requires access to that
private candidate; public app tests continue to use independent protocol peers.
The original dirty companion checkout and its four changes remain preserved.
The shared application archive stays 0.1.19 until deliberate distribution/pin
qualification and adoption; package version alone cannot enable installed Pi voice.
The Harness web entry point, voice-brief upgrades/downgrades and full migration
remain open.

Retained early failures include the pre-fix pending-ticket controls, a corrected
closed-heartbeat response regression, silent-PCM test-fixture observation failures
and refusal of a global DSH version different from the pinned test contract.
Early component tests generated untracked Python cache files in the retained
ordinary app test copy; tracked/compiled inputs verify unchanged and the caches
are retained. Final proofs use a new private copy of public application 4cb16513:
all **3,366 tracked Git blobs/1,057 compiled files** verify, and the complete
**27,067-entry** inventory is identical before/after, with bytecode writes disabled.
Deadlines and two application-test workers remain unchanged.

[Application SDK run 38817253387](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38817253387)
at **544bf035** passes Linux/macOS overall. Windows's expanded voice/memory step
retains **75 cases: 55 pass/five failures/14 cancellations/one existing POSIX-only
skip**. Protected fixture creation no longer produces the earlier provenance
setup failures, but strict companion executable-identity cleanup and memory/Host
timeouts remain unresolved; the timeout cause is unproven. The separate Windows
desktop build passes. macOS bundle checks still stop at the existing MPL Office/
LGPL libvips notice gates. These component checks do not clear those application
or physical-platform gates.

The private component's first [hosted run 38819354223](https://github.com/ManoloRemiddi/resonant-voice/actions/runs/38819354223)
at **f3547ddd** reaches the existing ten-minute limit on all four OS/CPU jobs.
Reported progress stops after two preference checks, before the tempo/pitch
result. The cause is unproven; local CI-environment repetition still passes 61
plus three existing Windows-only skips. The separate diagnostic follow-up
**f0b61c15/run 38820874680** checks FFmpeg availability/version before the unchanged
full suite, without installs, skips or bound relaxation. The follow-up now fails the explicit working-FFmpeg-on-PATH prerequisite on all
four jobs, before full npm test. That identifies a hosted tooling blocker without
proving the only cause of the earlier stall. Provision and record the test
processor, Linux first, then requalify the unchanged audio assertions. No complete
hosted Pi qualification follows from either failed attempt. Application Validate **38817253540**
also refuses Debian packaging at its existing Office public source/rebuild gate.

Read-only postflight re-verifies ten sealed reviews/eleven owners, selection,
38 canonical changes and six model/service configurations. Current review
**20261015-211446-7474ddb2/application 8c159cb7** stays unchanged and available,
without the newer source speech controls. Qwen models return HTTP 200; Breeze is
failed and voice inactive, with **2,012 MiB** free on RTX 5090 against its existing
**2,828 MiB** start requirement. No new retry, placement/tuning, installed
activation, public binary or merge occurs. Physical speech remains blocked on
that existing resource gate; other authorized migration work can continue.

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
maintenance 146/146 pass. At final source **4cb16513**, source/fresh ordinary each pass **735 cases:
733 pass/two existing optional skips/zero failures**, **126 files/all 53 Harness
Chromium files**, two workers and unchanged deadlines. Both native/controller/
maintenance runs pass **146/146**. All **1,057 compiled/3,366 tracked inputs** match
at freeze, and every ordinary tracked Git blob verifies against the exact commit.
Two separate copies that move cold preparation outside ownership or omit the
client opening ID each fail their intended actual Host/shared-worker case. The
22 notice/packaging/private-source cases and tracked/branch-history gate pass.
Supplier/Harness controller/layout/CSS/assets and Node/151 npm instances remain
unchanged. The generated Harness GUI normalizes equal after one spreadsheet
chunk reference/four source-comment paths. [Portable qualification and full
roster](../release/harness-pi-voice-surfaces-qualification.json).
Qualification setup also retained a self-referential manifest read and a Native
invocation from the wrong directory; neither ran its advertised cohort. Separate
corrected copies/launches supply the recorded results. The initial 46121ad1 source cohort
passes 733/two existing optional skips/zero failures, but final review found that
an initial spoken Send rejection had no submission receipt for VoiceSession.
A retained failing real-VoiceSession/controller control proves it; the corrected
Pi Controller now reports an unconfirmed result and hands-free shuts down without
replay. Successful/failed initial spoken input uses the same receipt path as
spoken follow-ups. The corrected native set passes 146/146. This supersedes the
initial candidate; its ordinary copy was prepared but its cohort was not run.

The 76-case development focus is supplemental evidence, not a separate frozen
commit claim. Both final main cohorts reverify 74 of its case names; the two
native-memory snapshot/branch cases pass separately against both frozen source
and ordinary trees (**2/2 each**, zero skips/failures). The portable record lists
that supplement separately from the 126-file main roster.

Preceding [SDK run 38810763428](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38810763428)
at **6db75c8f** passes Linux and macOS overall. Windows's expanded step retains
**73 cases: 46 pass/13 fail/13 cancelled/one existing POSIX-only skip**. Newly
included provenance fixtures pre-created ordinary Windows roots before the strict
ACL helper, cleanup refused an executable identity, and memory/Host cases timed
out. Fresh Windows provenance/native-memory roots now use the existing atomic
private creator; no guard, deadline, concurrency or skip is relaxed. Remaining
cleanup/timeout causes and new-head Windows qualification remain open. Earlier
export settlement and Office/libvips packaging notice gates are not resolved.

Read-only postflight verifies ten sealed inventories/eleven review owners, the
selected configuration, 38 canonical changes, the private companion's four changes
and six model/service configurations. Qwen catalog is HTTP 200. Breeze remains
failed and voice inactive, with 2,012 MiB free on RTX 5090 against the existing
2,828 MiB startup requirement; it is not retried, moved or silently tuned. Current
MX review **20261015-211446-7474ddb2** remains application **8c159cb7**, without this
Native/Browser source binding. No new artifact is staged or activated.

At this Native/Browser checkpoint a separately qualified Pi companion was still
required; the candidate above now supplies component acceptance while distribution/
adoption remain open. Old Codex-only health advertisements still refuse before
tickets. This public test cohort uses independently authored protocol peers and
fixed PCM, not real ASR/TTS or private service source. The original private
checkout and its four local changes remain preserved. Qwen/
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
