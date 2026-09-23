<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Resonant Voice single-button desktop interaction

Implemented 2026-09-19 for the native desktop. This replaces the expandable voice panel; the browser extension is unchanged.

- First click prepares the voice connection. No recording starts on a short click.
- Press immediately clears local playback and interrupts spoken output, without cancelling the agent task.
- Hold for 230 ms to start the microphone; release to transcribe and submit through the existing controller. A filled centre marks recording. If the connection becomes ready during a continuing hold, recording starts then; readiness after release never opens the microphone.
- Escape, dragging outside the button, hiding the window or losing window activation cancels an unfinished recording. Cancellation closes the voice connection without sending an `end` message, so the unfinished utterance is discarded. The next press reconnects.
- Space supports hold/release when the button has keyboard focus. Enter performs a short click.
- The existing Stop control cancels the agent task. Settings → Resonant Voice disables voice and hides the icon.
- Short, state-dependent tooltips describe each action. The orb uses the live theme accent, with gentle shape/glow motion on hover and active states. Appearance's animation setting disables motion.

The speech session is now a QObject with state notifications, rather than a hidden or visible widget. No voice control changes window geometry. Model selection, speech adapters, voice reference, GPU allocation, DSH workspace handling and the exterior activity effect were not changed.

The website reference is the [Augmentor masthead orb](https://augmentoragent.com/). Its published stylesheet currently disables its earlier orb animations; the native implementation adds the requested hover motion using that orb's organic contour and glow, rather than claiming an identical currently running website animation.

## Validation and local deployment

The final complete native suite passed all 291 tests, including 18 focused voice tests covering tap versus hold, release exactly once, Escape, dragging away, hide, readiness during/after hold, disconnection and reduced motion. Mocked streams test gestures and protocol messages; they are not a live microphone/acoustic test.

Applied only `window.py`, `voice.py` and new `voice_button.py` to the existing user-local 0.2.8 preview after the native maintenance endpoint confirmed it was idle and accepted graceful close. The source tree remains the separate 0.2.9 development tree. Backup: `/home/example/.local/share/resonant-voice/backups/single-button-20260919-085629`.

The reopened installed desktop was inspected visually: no lower audio panel, theme-matched orb, existing conversation and DeepSeek-V41-Flash selection retained. Live speech-service status confirmed an active owner, ASR ready, microphone not capturing, and no queued audio. DSH and speech/model services were not restarted.


## 2026-09-19 follow-up: first hold in a new chat

The first implementation missed the actual controller's new-session transition. `prepare_voice` temporarily sets `navigating`; its session-created notification refreshed the UI while that flag was true, disabling Voice and Send and cancelling the hold. Completion cleared the flag without refreshing the controls. The live accessibility tree confirmed both buttons stayed disabled although the speech service was ready.

The voice-preparation callback now refreshes all controls on completion, including cancelled/error outcomes. The voice button remains enabled during its own preparation so the original hold survives session creation. Ordinary navigation still disables it. The added regression test uses the real Controller preparation path and failed before this fix, then passed.

Validation: all 292 native tests pass. In the running installed XWayland desktop, a real mouse hold armed the microphone in the live speech service; Escape discarded it and no model request was submitted. This verifies real capture activation, not a fresh spoken transcription/model round trip. Existing audio-processing and submission code was unchanged. Both Voice and Send were verified enabled through desktop accessibility after reload. The user's unsent draft was backed up privately and restored exactly. Only `window.py` was updated in the installed preview; backup: `/home/example/.local/share/resonant-voice/backups/hold-fix-20260919-092433`.


## 10-minute recordings and slide-to-lock (0.1.7)

Hold the orb to record. While holding, slide left by 24 logical pixels to lock recording, then release. A small padlock marks the locked state. Click once to finish and send. Escape discards the recording. Keyboard users can hold Space and press L to lock, then release Space; the next Space press finishes. A locked recording survives switching focus to another app; explicitly hiding Augmentor, changing conversation or disabling voice cancels it.

The circle contains a live microphone waveform. It stays flat for silence; an animated outer contour/glow indicates active recording independently. The theme accent changes to orange at 8 minutes and red at 9 minutes. A tooltip displays elapsed time and remaining time during the last two minutes. Appearance's animation setting controls decorative movement; audio-level feedback continues to represent the microphone.

The service advertises its actual limit. Native capture, service framing and the ASR worker support 600 seconds (19.2 MB of mono PCM). At the limit, capture automatically finishes and the available audio is transcribed rather than discarded. The service handles late microphone packets and a simultaneous release without duplicate transcripts. Historical 0.1.7 behavior was batch processing after recording ends. This is superseded by the incremental 0.1.16 contract below.


## Current capture indicator and drag feedback

See [buffered activation and echo protection](HANDS-FREE-IMPLEMENTATION.md#buffered-activation-and-playback-echo-protection--19-september-2026)
for the current hands-free contract. Orange indicates unavailable capture; green
means microphone frames can be retained, including during chat preparation and
transcription. The older complementary-colour indicator is superseded by this
readiness feedback. The eight/nine-minute orange/red duration warnings remain.

Dragging moves the icon with the pointer, up to 12 logical pixels in either
direction. At the existing 24-pixel threshold, left locks manual recording and
right activates hands-free. It snaps to its original position over 150 ms when
the action activates, without waiting for pointer release or changing the window
layout. Releasing that gesture cannot submit/stop the just-selected mode.
Releasing or cancelling an incomplete drag also returns the icon. With Appearance
animation disabled, the return is immediate. Left-lock, right-drag, tap/Escape,
keyboard operation and the separate agent Stop control retain their semantics.

## Incremental recognition and buffered playback — 20 September 2026

Resonant Voice 0.1.16 recognizes during capture, normally after each two seconds
of new PCM, with bounded overlapping windows. The orb tooltip says “Transcribing
as you speak” after matching provisional recognition. Partials never enter the
composer, controller submission or memory; only the final transcript is submitted.
Older companions and older native clients remain compatible through protocol 1.
See the speech package's [algorithm and measurements](https://github.com/ManoloRemiddi/resonant-voice/blob/main/docs/INCREMENTAL-ASR.md).

Native output now collects a 200 ms PCM reserve before playing a new burst, waiting
at most 250 ms after the first packet. A terminal short response drains immediately;
a starvation refills the reserve, and interruption discards it immediately. Clear,
speaking and speech-idle markers update the buffer on the receiving thread in wire
order, so Qt event scheduling cannot reset a completed burst incorrectly. Existing
echo guard, device clock and actual audio-drain checks remain in use.

This addresses a measured opening-word gap: 142 ms of PCM arrived at 220 ms, then
the next chunk at 463 ms. Immediate playback leaves 101 ms of silence mid-opening.
It does not prove the user's device was reconnecting or that all possible audio
underflows are removed. Fake-clock replay preserves the entire opening through
that measured gap. Manual listening remains a separate acceptance check.

Maintenance status adds numeric `voiceTiming`, `voiceBufferStarvations` and
`voiceOutputUnderflows`. Timings distinguish ASR progress/finalization, recorded
seconds, first transport PCM and first playback callback after end-input. Callback
time is not acoustic onset. No audio, transcript, token or private configuration
is logged by these counters. GPU utilization is not treated as a fault; the same
CPU recognizer and the user's 5090 Qwen/Breeze settings are preserved.

Validation: all 395 native tests passed, including provisional-versus-final
routing, numeric counters, generation ordering, short responses, interruptions,
starvation recovery and replay of the opening gap. The speech package separately
passed eight Python worker and 34 Node tests, DSH lifecycle and package-install
proofs, plus real CPU synthetic replay; these are not a physical microphone or
speaker qualification. Source files match the installed 0.2.8 baseline before
this patch; activation uses a separate copied artifact per the deployment guide,
with the 0.2.8 product/DSH compatibility preserved.

## Output-device lifetime check — 20 September follow-up

The output stream is opened and started in `VoiceSession.connect_voice` before
processing the service's ready/reply events. Its callback supplies silence when
no speech PCM is queued. Input release, transcription, model waiting, speech-idle
and interruption leave that stream open; disabling/closing voice or connection
failure closes it. This was already true in the older running preview, not a new
behavior introduced by the playback-buffer patch.

During the reported continued first-word distortion, installed-status inspection
confirmed that all open windows still used the older preview while the buffer fix
was selected in release `20260920-150518-3d939dd3`. The active desktop's ALSA/Pulse
output stream was uncorked; the echo-cancelled speaker route and physical analog
sink were running. PipeWire also showed continuing output processing. This proves
the OS output route is active, not the electrical state of an external amplifier,
and does not qualify audible first-word quality. It provides no evidence that
opening the output stream only at reply time is the cause.

The user elected to keep the active voice session running. No window, voice
session or audio service was restarted. The selected buffer fix still needs the
next close/reopen of that window before its effect can be judged by listening.
The preceding source CI run (`b10ec7e`) passed. Do not silently reload an active
voice session or claim that the selected update is already running.
