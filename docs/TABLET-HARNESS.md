<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Responsive Harness and independent quick chats

This supersedes the separate Agent presentation proposed in the original
[Android preview](ANDROID-AH.md). One Harness React application and one AH owner
serve desktop, portrait and landscape. No Android agent loop, transcript copy or
second session engine is introduced. The private mobile carrier remains an
authenticated transport, not an execution owner.

## Layout and controls

The right sidebar defaults to expanded at 960 CSS pixels or more in landscape,
and collapsed in portrait/narrow windows. The original toggle remains available.
Only a session or presentation boundary applies that default; ordinary polling,
keyboard height changes and re-renders preserve manual toggles. The conversation,
draft, attachments, approvals and shared voice object stay mounted across rotation.

Microphone, Send/Stop and AI Improve are shared composer controls. Send changes
to Stop during a running turn; stopping spoken playback remains a separate action.
AI Improve uses the existing non-submitting draft/undo contract. On touch devices,
the active editor and these same controls move above floating keyboards, which
can report neither viewport resizing nor keyboard occlusion. There are no cloned
buttons or alternate owners. The normal placement returns when editing ends.
The focused composer stack is raised above the right pane, so its fixed controls
and editor remain visible and receive touch across the landscape viewport.
Qualification checks actual hit targets; visible element rectangles alone can
miss a later sidebar painting over them. The rule uses the stable composer-seat
attribute rather than generated CSS-module class names.

## Ungrouped means separate conversations

General New Chat, including its keyboard shortcut and the Ungrouped action,
requests `session.create` with `ungrouped: true`, without a project directory.
Explicit workspace actions still supply that workspace's directory. An older
owner without `isolatedUngrouped: 1` refuses quick-chat creation rather than
silently inheriting a project.

AH allocates a private `state/ungrouped/SESSION_ID` working directory and a fresh
SDK session. These directories do not become inferred project registrations.
Independent chats have separate conversation histories, compactions, drafts,
attachments and working files. Reopening a chat restores its own history.
Existing project assignments and chats are not migrated or deleted. Existing
long-term personal memory policies remain separate and unchanged.

This is context/working-area separation, not an OS sandbox. Tools retain the
session's existing permission mode; explicitly permitted absolute file access is
not prohibited merely because a chat is Ungrouped. Branching is an explicit
history-preserving action and is not equivalent to creating a fresh quick chat.

## Tablet audio transport

The browser captures mono PCM on the tablet, resamples it to 16 kHz, and plays
24 kHz companion output on that same device. It never opens desktop audio devices.
Fixed, authenticated `/api/voice/` carriers bind client, chat and opening identities.
The Host retains companion credentials and scoped tickets; these never reach the
tablet. Bounded PCM sequences, an expiring client lease and bounded output prevent
unbounded buffering. Neither audio, accepted transcripts nor uncertain submissions
are automatically replayed. Read-only inspection credentials cannot open voice.

Hold Talk to record; release to transcribe into the existing editable message box.
Release never sends a conversation message. Only the original explicit Send (or
its keyboard shortcut) submits the draft, including any edits and attachments.
Talk can add speech to an existing draft at its captured selection. The shared
insertion contract fences editor revisions and chat/epoch ownership; if the draft
changed, the transcript stays visible for explicit insertion rather than replacing
newer text. Duplicate final events cannot insert twice.

Mouse/touch pointer capture and Space/Enter key release end the recording.
Pointer cancellation, focus loss during a hold and page hiding discard unfinished
audio. Assistive click activation can toggle start/finish. Releasing before a slow
permission/setup completes prevents a late microphone start. The held control
stays enabled during setup so it can receive release; other input actions wait
until dictation settles. An older owner without `browserDictationDraft: 1` refuses
this UI's capture, avoiding an automatic-send fallback.

Connecting, microphone startup, transcription and waiting for a sent reply have
explicit busy states. Repeated presses cannot begin another recording while
finalization is pending. Late partials cannot replace the finalization status with
Listening. Playback keeps its
Speaking state until server completion, speech idle and local audio drain agree.
Stop speech interrupts playback without cancelling the AH task; holding Talk
also interrupts playback and starts a new draft recording. Close voice
discards unfinished audio. Microphone tracks close when recording finishes.
The companion's bounded utterance budget is retained. Manual foreground speech is
implemented; hands-free, background capture and screen-lock continuation are not.

The audio relay returns final transcripts once and never calls `session.prompt`
or reads/submits the conversational queue. Draft insertion uses the original
shared persistence path. Explicit Send retains the normal durable draft/request
identity and editable-text input mode, and the live scoped companion can still
speak that admitted human turn's reply. The companion does not run the
conversational model. CPU recognition and the existing Breeze/Qwen device
placement, model choices and precision are preserved.

The live MX deployment uses a separately packed Resonant Voice 0.1.22 scoped
companion and a private AH-profile connection. The existing Desktop/DSH companion
is retained. Its source/package remain outside the public Augmentor repository;
no private implementation is copied into this application or its tests.

## Build, qualification and deployment

`scripts/build-mobile-ah.py` runs inside the managed build workspace, preserves
the 64-GiB reserve and uses matching locked dependencies. It builds the shared GUI
and a small compiled runtime overlay, runs focused and backward-compatibility
checks, then records file hashes and the product version.

`scripts/stage-tablet-harness.py` verifies the declared installed base and candidate
hashes/version. It stages a new immutable release through the deployment helper.
The bounded Host overlay preserves the installed default-provisioning and macOS
Search/Wiki changes that are absent from this older source branch. Existing
releases are never patched. Activation follows the registered review's guarded
shutdown, private cold backup and normal registration/startup paths.

The private gateway can run as an enabled user service against a stable candidate
selection, with the existing private Tailscale Serve route. This differs from the
October 22 session-only preview. Enabled startup is not a physical reboot test.
Do not expose the underlying AH operator credential or use a public proxy.

## Evidence and practical limits — October 25, 2026

The Lenovo TB323FU runs Android 16 and Chrome, connected through private Tailscale
HTTPS. Physical portrait/landscape rotation retained an unsent draft; one Send
admitted one human message and no tool call. Two physical New Chat actions created
distinct Ungrouped directories. Chat A received an authored token; fresh chat B
returned NO PRIOR TOKEN. The original 132 saved conversations were retained.
AI Improve completed without admitting a conversation prompt.

Microphone capture stayed active through physical rotation. The owner confirmed
actual recognition and a spoken reply, and reported awkward tap/finalization
behaviour. That report led to the explicit busy states and playback-drain guards;
it is not evidence that the earlier interaction was smooth. The initial permission
timeout and the projectless hero's disabled composer were reproduced and repaired.

An independently authored 5.45-second synthetic speech clip took 907 ms to
transcribe through AH's configured offline CPU recognizer; reservation took 446 ms.
This is a local-host batch measurement, not an end-to-end tablet latency claim.
Handy's selected desktop recognizer is Parakeet Unified EN 0.6B Q8; the current
scoped speech path uses Whisper small.en CPU. No model was swapped to obtain this
result. On-device ASR is a separate adapter decision, not claimed by this release.

Authored tests cover real SDK/provider-context isolation, separate drafts/files,
project creation, rotation defaults, wrong-client voice authority, repeated PCM,
duplicate transcripts, delayed microphone permission, finalization re-entry and
playback drain. The expanded source/artifact cohort passes 80 tests with no failures or skips, including the existing Pi voice and workspace suites. Final installed evidence belongs in the release receipt. Test-provider/PCM evidence is distinct from physical speech feedback.
An added native-surface regression initially found a missing QtTest test dependency
in the pruned production Python. A matching Debian QtTest module was used only by the test runner; app dependencies were unchanged. The broader run also exposed test-owned dictation brokers left alive; the surface fixture now closes its own isolated broker before removing its private test root.

The shared implementation applies to Linux/macOS source; installed macOS/Windows,
Pixel regression, hotspot/cellular transitions, all attachment/Office combinations
and unrestricted arbitrary-failure exactly-once semantics are not qualified here.

## Earlier installed qualification — before hold-to-dictate correction

The registered MX `pilot` review now selects and runs the separately sealed
`20261025-105801-5def1568` artifact, built from feature commit `592ec36d` with the
declared installed-base overlays. Its SHA-256 is
`62963e266c97bb71dd7627d187cbd8b8af934c8c2f19f4c56178061d9962824b`.
The final exact-package cohort passes 47 tests, without failures or skips,
in addition to the 80-test build cohort. See the
[installed receipt](../release/tablet-harness-installed-20261025.json).

On the final build, physical Lenovo portrait hides the right sidebar; landscape
opens it. All three controls and the active editor stay reachable above the
floating keyboard in both orientations. A landscape draft survived rotation to
portrait and one physical Send. The same test chat returned its earlier token
on Desktop and then its tablet continuation on Desktop: exactly three human
messages, three completed turns and zero tool calls. All 132 original saved
conversations remain among the 134 current conversations.

Physical microphone start and Finish displayed recording and disabled
Transcribing states on the final build. Silent recording admitted no extra human
message. Recording was explicitly closed after the test, and the device's original
automatic-rotation preferences were restored. This validates the control state,
not a new acoustic or end-to-end latency acceptance: the owner's spoken-reply
confirmation and awkwardness report preceded this final fix.

The private gateway and AH-scoped voice companion are enabled user services;
the existing Desktop/DSH voice companion, Handy and model placement are unchanged.
Current and needed rollback artifacts remain, and twelve verified obsolete test
artifacts were removed. No scratch build is selected or retained.

## On-device recognition follow-up

Android provides native `isOnDeviceRecognitionAvailable` and
`createOnDeviceSpeechRecognizer` APIs. Availability must be checked on the actual
device and language; installed recognition services alone do not prove an offline
model is ready. See the [Android API contract](https://developer.android.com/reference/android/speech/SpeechRecognizer).
[Sherpa ONNX's Android examples](https://k2-fsa.github.io/sherpa/onnx/android/prebuilt-apk.html)
also support offline recognition, including streaming and Qualcomm QNN variants.
These are candidates for a device benchmark, not qualified integrations here.

A device adapter should keep interim words local, show editable final text, and
submit the final transcript through the same AH client/request identity once.
Compare finalization time, recognition errors, battery use and first reply audio
against the current CPU path before choosing a model. A faster recognizer cannot
by itself remove network, conversational-model or reply-synthesis time. No Android
wrapper or recognition model is installed by this change.

## Installed hold-to-dictate correction — October 25, 2026

This supersedes the automatic-send interaction in the earlier installed receipt.
Feature commit `d62f9e40` is staged as `20261025-132556-b39f82c2`, artifact SHA-256
`c387ce36cf5ceb48956d67fb93d01e2e0a31916a856fc53d03ff628324080ac2`.
The registered MX pilot selects and runs that exact sealed package; the private
mobile gateway selects its matching assets. The normal guarded registration path
was used after a fresh private cold backup. All 134 conversations present before
this correction are retained; no recording or prompt was replayed during update.

The build cohort passes 82 tests and the exact sealed package passes 49, without
failures or skips. The added real Chromium/Host/SDK test holds a mouse in landscape
and a touch pointer in portrait. Each release inserts the scripted transcript into
the original persisted draft with zero human messages/model requests. It preserves
existing text, then edits the draft and presses the original Send exactly once;
one ordinary text-mode human message is admitted and its reply reaches the scoped
speech observer. This uses fake browser audio and an independent protocol peer,
not a physical recognizer. The test accepts only the existing ScriptProcessor
deprecation warning; unexpected browser errors and failed HTTP responses fail it.

Unit/runtime checks additionally cover release during delayed microphone
permission, duplicate final events, late partials, editor conflicts, session
changes and absence of conversational calls from the audio relay. An empty
transcript cannot delete the selected draft text. Existing CPU recognition,
Desktop/DSH speech, Handy and model placement are unchanged.

The desktop page was refreshed to the corrected shared interface. The Lenovo
remains connected over Wi-Fi, but its secure screen lock prevented a fresh
physical hold/release check and page refresh. The owner was asked to unlock it;
this receipt does not claim that physical check passed. Earlier orientation and
acoustic results above describe the preceding build. The device's orientation
preferences are restored after attempted checks. See the
[correction receipt](../release/tablet-dictation-installed-20261025.json).
