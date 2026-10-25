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

Tap Talk to begin; tap Finish & send once to finalize. Connecting, microphone
startup, transcription and waiting for a reply have explicit disabled states.
Repeated taps cannot begin another recording while finalization is pending. Late
partials cannot replace the finalization status with Listening. Playback keeps its
Speaking state until server completion, speech idle and local audio drain agree.
Stop speech interrupts playback without cancelling the AH task. Close voice
discards unfinished audio. Microphone tracks close when recording finishes.
The companion's bounded utterance budget is retained. Manual foreground speech is
implemented; hands-free, background capture and screen-lock continuation are not.

Final transcripts enter the existing durable AH queue once with the canonical
`resonant-voice:` identity and scoped voice admission. The companion does not run
the conversational model. CPU recognition and the existing Breeze/Qwen device
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
