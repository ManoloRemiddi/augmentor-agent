<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->
# Hands-free native implementation

Hands-free is an optional Conversation mode in Resonant Voice settings. Manual hold/slide remains the default and fallback. Save the mode and pause tolerance (400–2000 ms, initially 800), then tap the existing voice icon to start. Tap again or Escape stops capture and playback; explicit hiding/session changes also close the session. No automatic restart follows a fault.

A single 16 kHz capture stream stays open during the active conversation. Its callback only puts bounded PCM into the worker queue. A CPU Silero ONNX worker uses 32 ms frames, 320 ms pre-roll, 128 ms speech confirmation (320 ms during audible playback), probability hysteresis, and configurable silence endpointing. Silence and brief transients never submit prompts. ASR finalization suspends detection while the same microphone buffers the next utterance; after its response detection processes those frames, including during the agent's work and playback. The existing DSH controller sends or steers each utterance once. The 10-minute safeguard ends the current utterance and leaves conversation mode active; speech during ASR finalization is retained for the next request, without opening overlapping ASR requests.

Playback completion requires the current terminal turn notification, service speech-idle, an empty PCM queue, and PortAudio DAC time plus an output tail. Native sends advisory playback-drained for that audio generation. Late generations/request identities do not set a new turn ready. Confirmed near-end onset invalidates pending local audio immediately and sends the existing interrupt control, independently of DSH tool cancellation.

Both streams use a dedicated per-session PipeWire module-echo-cancel WebRTC source/sink pair. Physical desktop defaults are unchanged. Actual Pulse stream routing is checked after each stream opens; failed routing refuses hands-free instead of silently using an unfiltered microphone. Streams use low latency (MX reported 64 ms capture / 40 ms playback). The module is unloaded when streams close. AEC is an acoustic aid, not proof of speaker double-talk quality: room playback, background speech, and actual interruption timing still require user trials.

## Pinned detector

- [Silero VAD v6.2.1](https://github.com/snakers4/silero-vad/tree/v6.2.1), MIT © Silero Team.
- Installed model: `~/.local/share/resonant-voice/vad/silero-v6.2.1.onnx`.
- SHA256: `1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3` (verified before loading).
- License beside it: `SILERO-LICENSE`.
- Tested existing ONNX Runtime 1.28.0 in Resonant's Python environment; explicit CPUExecutionProvider and one inference thread. No torch/CUDA inference.
- Model source: `https://raw.githubusercontent.com/snakers4/silero-vad/v6.2.1/src/silero_vad/data/silero_vad.onnx`.

Local CPU measurement on Clara's stored preview: median 0.056 ms / p95 0.069 ms per 32 ms frame. Speech onset/end were detected against added leading/trailing silence. This is detector compute time, not end-to-end conversational latency. Live MX PipeWire 1.4.5 routing was verified with real source/output streams and unchanged defaults; no user speech was recorded for that route test.

Backend contract additions: `turn-complete {generation, requestId}` from durable DSH driver idle, and advisory inbound `playback-drained {generation}`. Existing begin/end/interrupt and PCM transport are reused. No second microphone or conversational agent is introduced.

## Direct gesture activation

The existing icon now supports right-drag (24 px) to start a temporary hands-free conversation without changing saved preferences. Left-drag retains locked manual recording. Release after right-drag is consumed so it cannot send a partial manual recording or stop the new conversation. A pending connection is reused; changing from a live manual hold cancels that unfinished hold before opening hands-free. Tap or Escape stops; the default manual behaviour returns. The active hands-free icon uses a split ring marker and explicit orange/green capture readiness; orange/red recording deadline warnings take precedence. See the current buffering correction below.

Historical evidence: the native gesture patch passed 319 discovered tests. A later discovery audit found three gesture/colour methods below the unittest main guard; those methods were not exercised by that run. The current correction moves them into the discovered test class and checks connected-controller fixtures. Three native files were installed from a hash-checked staged artifact; backend/model services were unchanged.

## Capture readiness correction — 19 September 2026

Historical implementation at `cc8845c`; startup and ASR-gap behavior below is superseded by the current correction.

The initial implementation opened hands-free capture only after the companion's
ASR-ready event. The active-mode colour also appeared during connection and
recognition gaps. This allowed users to start a sentence before capture opened.
Historical microphone audio is not retained, so an old truncated transcript alone
cannot establish whether capture, VAD or recognition lost its beginning.

Native capture now opens as soon as its dedicated AEC route/output is prepared,
without waiting for the resident recognizer. A bounded 10.24-second in-memory PCM
queue preserves the opening while ASR loads; no begin/audio is sent until ready.
The existing VAD processes those frames in order. Overflow fails visibly and
clears the buffer rather than submitting only its tail. Closing/cancellation
clears pending startup audio; it is never reused in another session.

Orange means capture is not yet available, or transcription currently suspends
speech detection. Green requires an actual delivered microphone frame and an
active capture/detection path (including startup buffering). A missing frame
stream turns orange after 500 ms. Hands-free keeps its ring marker; the existing
eight/nine-minute orange/red deadline warnings still take precedence. Recognition
is still utterance-based, and speech during recognition remains unavailable;
the icon now makes that interval explicit. The UI does not promise instant ASR
or an instant answer. Turning on voice may still require DSH session preparation.

Validation: 346 native tests passed, including a five-second opening captured
before recognizer readiness, exact PCM preservation, single begin/end, readiness
colours, overflow cancellation, stale-generation and manual-gesture regressions.
A local actual Rode/PipeWire probe delivered the first microphone frame 353 ms
after constructing VoiceSession (319 ms to audio preparation), before ASR ready.
It discarded microphone audio immediately and submitted no user message. This
excludes the preceding DSH ticket/session preparation and is a single measurement,
not end-to-end response latency or human listening acceptance. A separate process
check measured the current ASR worker's startup at 886 ms. GPU/model placement,
voice identity and conversation authority are unchanged.

Source baseline: `ee5c406` on `productization/shared-memory-and-desktop`; this
section and its accompanying commit identify the correction. The user-local
preview receives only the three changed native modules; unrelated installed
window differences are preserved by applying the tested diff. The queued ASR
vocabulary correction is deployed from the separately published Resonant Voice
0.1.14 source with its existing profile support. Rollback retains the prior
native modules, speech artifact and private configuration outside this repository.


## Buffered activation and playback echo protection — 19 September 2026

Current change follows source baseline `cc8845c` on
`productization/shared-memory-and-desktop`. Hands-free activation (right-drag or
saved hands-free mode) starts `EarlyVoiceInput` before DSH ticket preparation.
It opens the dedicated AEC microphone immediately and retains PCM in memory.
`VoiceSession` adopts that same stream and drains the buffer under a lock before
forwarding live frames: no second microphone, reordered audio or handoff gap.
The voice-session queue also retains speech while the previous utterance is being
transcribed; those frames become the next utterance after ASR finalization.

Each waiting queue is bounded at 320 × 32 ms (10.24 seconds). Overflow/device loss
fails visibly and discards the unfinished recording; it never sends only a tail.
Tap, Escape, disable, close and harness changes discard pending audio.
Maintenance refuses to close the app during preparation or early buffering,
including before a VoiceSession exists. Buffers
are memory-only and belong to the active voice session. This does not change the
600-second utterance limit or make batch transcription instantaneous. Manual
hold/release keeps its existing activation contract.

Orange now means the microphone cannot retain incoming audio. Green requires
actual microphone frames, including buffering during preparation/transcription.
A 500 ms frame stall removes readiness. Orange is still necessary for device
opening or failure, but DSH/ASR preparation no longer adds an unavailable interval
to hands-free capture. Eight/nine-minute recording warnings still take precedence.

`PlaybackEchoGuard` supplements the existing PipeWire WebRTC echo cancellation.
The output callback queues bounded copies of actual played PCM; the VAD worker
compares recent output with the incoming waveform before allowing a speech onset.
Correlated speaker leakage and very quiet residual input during playback cannot
start an interrupt. This is acoustic matching, not transcript filtering or a
canned prompt. Detection requires 320 ms of confirmed speech during playback
(128 ms when idle). Once near-end speech starts, normal capture continues.
The reference resampling/correlation uses NumPy on CPU and does not change voice,
GPU placement, output samples or the DSH conversation authority.

This is a heuristic additional guard. Quiet speech under loud speaker playback
may need a clearer onset; human double-talk, different output levels and room
acoustics still need acceptance testing. AEC already had extended/delay-agnostic
filtering enabled on the tested PipeWire version, so its settings were retained.
See the [PipeWire echo-cancel module](https://docs.pipewire.org/page_module_echo_cancel.html)
and [Pulse-compatible module](https://docs.pipewire.org/page_pulse_module_echo_cancel.html).

Validation for this change:

- All 359 native tests passed after test discovery correction using
  `QT_QPA_PLATFORM=offscreen PYTHONPATH=apps/native python3 -m unittest discover -s tests`.
  Matching PySide6 QtTest was available for actual Qt widget events. Fixtures cover exact startup/ASR-gap PCM ordering,
  single begin/end, cancellation, overflow, lost frames, echo rejection,
  independent/dominant mixed speech, left/right gestures and snap-back geometry.
- An isolated live companion/ASR/Breeze/AEC probe deliberately deferred session
  attachment by 2.5 seconds. The first physical microphone callback arrived at
  187 ms; attachment reused the same input stream. The spoken reply finished,
  with zero detected onsets and zero transcripts; the guard rejected 130 frames.
  No DSH prompt was submitted and microphone samples were discarded in memory.
- A preceding short physical speaker probe did not reproduce the intermittent
  self-interruption even without the added guard. Historical microphone PCM is
  not retained, so the exact earlier acoustic cause cannot be proven from text.
  The successful controlled probe is not universal room or human-interruption
  qualification, and 187 ms is capture startup, not answer latency.

Deployment scope: six native modules (`voice.py`, `voice_input.py`,
`voice_echo_guard.py`, `voice_vad.py`, `voice_button.py`, `window.py`) applied as a
hash-checked focused patch to the idle user-local preview. Unrelated installed
window differences and the draft are preserved. Speech 0.1.14 and model services
remain unchanged. A private baseline snapshot and manifest support restoring the
four prior modules and removing the two added modules while the app is closed.

## Latency investigation after the buffer correction — 19 September 2026

Read-only runtime investigation of the last three foreground voice turns with
native `0eafeac` and Resonant Voice 0.1.14. No microphone was recorded, no chat
prompt was replayed, and no model, memory or voice service was restarted. Private
conversation wording and identifiers are excluded from this report.

| Stage | First observed turn | Second observed turn | Third observed turn |
| --- | ---: | ---: | ---: |
| DSH inbox acceptance → step start | 16 ms | 13 ms | 10 ms |
| DSH inbox acceptance → complete structured reply | 15.266 s | 4.090 s | 25.078 s |
| Correlated Qwen prompt processing | 12.932 s / 37,263 tokens | 1.142 s / 2,595 tokens | 15.695 s / 42,792 tokens |
| Correlated Qwen response generation | 2.189 s | 2.817 s | 8.744 s |
| Breeze synthesis → first generated audio | 272 ms | 366 ms | 313 ms |

The model-server requests were correlated by launch/completion time and reply
completion. These are server timings, not a recording of audible device output.
The second request reused the foreground slot's prefix; other requests then
replaced that slot. The third request selected another slot by LRU and processed
a large prompt again. Background Hindsight retain/consolidation activity was
present during this interval and its configured LLM was the same Qwen endpoint.
This establishes competing work and lost cache reuse; the logs do not identify
every competing request's caller. Earlier pre-buffer turns also varied from
2.65 to 20.28 seconds, so the new capture buffer is not established as the cause
of the variability.

The input side has an additional, separate delay. Hands-free endpoint silence
is configured at 800 ms. The current small.en int8 recognizer uses six CPU
threads and performs batch recognition after the utterance ends. A separate
worker benchmark, using an existing synthetic 7.36-second Clara preview and the
installed worker/model revision, returned final text in 803 ms on the first trial
and 705 ms on the second; model startup took 572 ms. These samples did not enter
DSH. They are not measurements of the user's earlier speech: native currently
discards the service's timing events and does not retain acoustic endpoint or
ASR timestamps across sessions. Longer/noisier audio can take longer.

The UI submits only final transcripts, so endpoint silence plus ASR can leave a
visible gap before the user message appears. After DSH acceptance the measured
turns begin promptly. Expressive delivery uses a validated reply tool and waits
for the complete structured response before publishing text/TTS; generated reply
text is not incrementally spoken while tool arguments are incomplete. This is
another serial stage, distinct from first-token latency. The previous 187 ms
capture-start measurement never measured end-to-end reply latency.

Recommended next implementation work, not applied by this investigation:

1. Give live conversation priority over background memory inference and preserve
   foreground cache reuse, retaining memory retrieval and pending background work.
2. Record bounded, content-free stage timings (speech endpoint, ASR final, DSH
   acceptance/start, validated speech delivery, first PCM and actual playback)
   so the next real session can be diagnosed without storing microphone audio.
3. Show transcription/submission progress immediately. Assess streaming ASR and
   independently validated speech segments without guessing unfinished JSON,
   changing DSH authority, or forcing canned responses. Tune endpoint silence
   only after measuring pauses so reducing latency does not split user sentences.


## Automatic thinking selection restored — 19 September 2026

A subsequent greeting exposed a separate configuration drift: the installed
adaptive selector only allowed the legacy tray provider/model, while this native
session used the current mx-qwen 262k route. No adaptive decisions were recorded.
Saved minimal effort enables low thinking on this Qwen adapter; it is not off.
The selector also had no greeting rule and would otherwise classify it as high.

[DSH Adaptive Reasoning 0.2.1](https://github.com/ManoloRemiddi/dsh-adaptive-reasoning/blob/main/docs/VALIDATION-0.2.1.md)
adds the current exact route and a whole-request greeting rule with thinking off.
Structured Resonant Voice delivery remains available, including for transformations.
Substantive work, media, explicit deep thinking and ambiguous follow-ups keep the
selector's conservative depth rules. This uses no classifier model call and does
not rewrite the saved model default. The recorded decision is the effective effort.

Validation: 62 unit checks, real pinned DSH/HTTP routing and structured voice
contract checks, disposable installation/removal, and an isolated live Qwen greeting
with no reasoning output (789 ms with a small test context). The installed plugin
matches source and appears once in the composed profile. DSH was restarted only
after idle checks; the native conversation/draft were preserved. Native source,
Breeze, GPU placement and memory processing were unchanged by this plugin fix.
Large-context prefill and model contention from the previous investigation remain
separate latency issues; the small greeting proof is not full-chat timing.


## User-directed speech placement on 5090 — 19 September 2026

The user has superseded the prior 5060 Ti fallback. Breeze now shares the RTX 5090
with Qwen. Qwen's process and unit/drop-in hashes were preserved, including context,
concurrency and precision; only Breeze restarted. The native app, DSH and CPU
ASR/VAD stayed in place. The saved Clara voice synthesized successfully. See
[placement evidence](https://github.com/ManoloRemiddi/resonant-voice/blob/main/docs/DEPLOYMENT.md#user-directed-rtx-5090-placement--19-september-2026)
for measured memory/timing and the launcher admission override. No automatic
fallback or context reduction is authorized. Report an actual failure to the user
and wait for their direction on the next configuration change. Older GPU placement
statements in the dated entries above describe their respective historical tests.

## TPS investigation with both engines on 5090 — 19 September 2026

A read-only check of the latest session found foreground generation at 73–81 TPS
on earlier requests, then 18.57 TPS averaged over a later 339-token response.
That request processed 41,681 prompt tokens in 15.057 seconds before generating
for 18.258 seconds. While it generated, the other Qwen slot processed roughly
40,000 prompt tokens. The foreground timing report showed 6.76 TPS during that
competition and 75.10 TPS in the subsequent interval after the competing prefill
finished. This directly identifies shared-model scheduling/prefill as a cause of
that drop; it is not a permanent loss of model decoding speed.

Hindsight retain/consolidation/reflect/recall activity overlapped the interval,
although server task IDs alone do not attribute every model call. Breeze had no
synthesis in that particular slow interval. No allocation/CUDA errors appeared
in the inspected model log, and GPU thermal-slowdown counters were zero at the
check. These observations do not establish that all future slowdowns have one
cause or that speech and chat never contend.

The adaptive selector was active, but its conservative fallback selected xhigh
for every inspected turn, including a one-word hesitation. That increases work
and latency separately from TPS. Proposed next work is foreground priority over
background memory processing/cache replacement and a qualified lower-effort
handling of brief conversational acknowledgments. No runtime parameters, model
context, GPU placement or active tasks were changed during this investigation.
