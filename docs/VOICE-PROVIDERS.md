<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Voice providers: implementation specification

Owner-approved requirements, October 3, 2026. Voice is an optional input/output
capability of the current Augmentor conversation. The application continues to
own its selected reasoning model, local or cloud, tools, permissions and memory.

## User experience

- Settings → Voice has an On/Off switch. Off closes capture, playback and any
  cloud session. On reveals two setup/configuration paths: **Resonant Voice
  (local)** and **OpenAI GPT-Live (cloud)**. Exactly one provider is selected.
- When On but the selected provider is unconfigured, the existing orb is red
  with an exclamation mark and accessible “Voice needs setup” text. Activating
  it opens Voice settings, without opening the microphone or billing a session.
- Local setup uses the maintained Resonant Voice installer and voice editor;
  existing installation/model/GPU configuration is preserved. Missing services
  show setup instructions and a retry control rather than breaking Settings.
- Cloud setup accepts a masked project API key, voice choice and an explicit
  cloud-processing acknowledgement. **Test and save** checks GPT-Live session
  access without recording audio, closes that test session, then stores the key
  in the OS credential vault. Setup explains that this test can incur duration
  charges. No API key is returned to either UI or saved in appearance JSON.
- Provider switching closes the old voice connection. It changes neither the
  selected model nor the current harness/conversation. Failed setup leaves the
  previous working configuration intact. Credentials can be removed explicitly.
- Both surfaces share provider configuration and the native audio engine.
  The primary and secondary profiles retain their existing configuration scope.
  A secondary window starts with local voice and configures its own cloud key;
  removing that key cannot remove the primary window’s key.
  Cloud works with DSH, Pi and Codex through their ordinary prompt/event paths;
  local support retains the harness capabilities already qualified.

## Delegation and audio

Use `gpt-live-1`, its Live WebSocket transport, mono PCM16 at 24 kHz and
`delegation: {type: "client"}`. Never configure Responses delegation or another
reasoning model in Voice. Supply a short voice-only prompt: every substantive
request must go to Augmentor; speak only verified results supplied by the app.
The voice model may paraphrase those results, so spoken wording need not match
the text transcript exactly.

Collect bounded input transcript fragments. A delegation ID contains no request
text; retain its metadata separately and collect transcript fragments into application
utterances using the configured pause. The delegation event itself never submits
a request.
Submit each request once using an application-generated UUID and the existing
controller/bridge. Manual recording submits after release and transcript settling;
hands-free submits after the configured pause. Delegation notifications and pause
handling must not submit the same text twice. Late fragments and repeated event
IDs must not cause replay. Barge-in clears queued playback immediately and keeps
backend cancellation separate: speaking over a reply does not cancel its tools.
The ordinary Stop control still cancels the backend task.

Only output from a successfully completed matching backend turn may open the
cloud playback gate. Never send private reasoning or raw tool output to GPT-Live.
Return bounded public answer chunks through `session.commentary.append`, each
with at most 500 tokens. The first implementation speaks completed results;
it sends no progress stream.
An interrupted/failed/unconfirmed turn cannot announce success. Match user request
identity and turn IDs where supplied; refuse unrelated or historical events.
Only live events are observed; opening Voice must not read history aloud.

Cloud capture/playback does not load local ASR, TTS or Silero models. Hands-free
uses the existing OS echo route on Linux; other platforms require headphones
until their echo-cancellation adapter is qualified. Both providers participate
in the existing microphone lease and UI teardown/maintenance contracts.

## Lifecycle, privacy and cost

Opening Settings never opens the microphone or creates a billed cloud session.
Cloud sessions are created only by Test and save or an explicit voice gesture.
Use a fixed OpenAI endpoint and no endpoint supplied by a browser.
Bound audio queues, transcript/history size, input commands and outgoing results.
Sanitize failures; do not log keys, audio, transcripts or private backend reasoning.

Close cloud voice after 60 seconds without speech, a pending request or playback;
show a resumable state. Apply a 30-minute maximum connection duration. Voice Off,
Escape, window/page hide, conversation/harness/provider changes, lease expiry,
network loss and process shutdown release all resources. Request `session.close`
and collect `session.closed` usage with a bounded wait; unknown final usage is
reported as unknown. Do not reconnect or replay unknown-outcome requests.

Published rate on October 3: $0.05/minute ($3/hour), billed by session duration,
including silence and backend waiting. Backend charges are separate. Show elapsed
usage as an estimate until final API usage arrives. Audio and selected context
are processed by OpenAI under its API data controls; local speech remains local.

## Acceptance and delivery

Tests cover setup with no local installation, On/Off, red actionable orb,
credential-vault failure, failed test preserving the previous key, provider switch,
deduplicated delegation, split/late transcripts, matched backend results, failed
turns, barge-in, bounds, idle closure, final usage and browser lease teardown.
Run the existing native voice/browser/Codex regressions and shared build checks.
Record fixture evidence separately from a real API/microphone trial. Linux/macOS/
Windows use shared implementation; platform acoustics and installation remain
separate qualification. Source changes do not replace installed release artifacts.

Cloud voice requires only the audio/runtime libraries, not local ASR/TTS weights.
Source environments install `requirements-voice.txt` alongside native requirements.
Debian runtime metadata now includes sounddevice, PortAudio and QtCore; existing
Mac Desktop and Windows bundles already include the audio libraries. Windows keys
use the bundled pywin32 Credential Manager adapter. Mac browser-only companions
intentionally exclude Qt/audio: their settings remain available, but Voice needs
the Desktop audio runtime. That packaging gap is shown as red setup status rather
than an attempted microphone session. This work does not qualify those companions
for standalone audio.

Pi accepts speech only when its current task is idle. DSH/Codex use their existing
steering/queue policies. A busy Pi submission fails visibly without replay. Local
setup links the maintained installer; it does not silently install model weights
or change GPU placement. Acoustic quality, latency and exact GPT-Live paraphrasing
require a real API/audio trial. The PCM gate correlates verified application results;
it does not independently fact-check speech generated from those results.

## Sources

- [Live connections](https://developers.openai.com/api/docs/guides/voice-websockets)
- [Client delegation](https://developers.openai.com/api/docs/guides/live-delegation)
- [Session lifecycle](https://developers.openai.com/api/docs/guides/live-conversations)
- [Duration billing](https://developers.openai.com/api/docs/guides/voice-latency-cost?api=live)
- [API data controls](https://developers.openai.com/api/docs/guides/your-data)
- [Local setup](COMPLETE-INSTALL.md#local-speech)

## Implementation evidence

Implemented on `feat/voice-providers`, based on
`c7f895d416e6b94ca601b66a09caf4846a64b907` in a separate checkout. The existing
canonical checkout’s uncommitted work and installed applications were preserved.

Validation covers implementation commit `5127253`; the subsequent documentation-only
commit records this identity. Validation on the review source:

- TypeScript check and shared production build pass.
- Main Node suite: 503 pass, 2 platform skips; browser UI suite: 88 pass.
- Full native suite: 857 cases, 36 platform/environment skips; focused voice suite:
  102 pass. Tests use an isolated dictation state to avoid shared-helper interference.
- Real pinned Codex host/native/browser voice regressions pass against scripted
  speech transcripts, health responses and PCM. Live transport/audio tests use
  synthetic sockets and devices; they do not contact OpenAI.
- Native setup screens were rendered and visually checked. No local speech models
  were provisioned, and the owner’s speech placement was unchanged.

No OpenAI project key was supplied for a real GPT-Live trial. Actual account
availability, microphone quality, latency, interruption acoustics and platform
bundles remain requirements for public release qualification. The initial source
qualification did not replace an installed build or claim a better acoustic
experience than Resonant Voice. The subsequent owner-requested compatible Linux
build is recorded below.

## Owner-requested build qualification — October 3

The owner subsequently authorized an autonomous build. Provider forms now reuse
an existing embedded settings frame; ordinary dialog-based builds retain their
existing lifecycle. Browser embedding allows its native host to finish accepted
work and billed-session closure on EOF, instead of terminating it early.

Validation after these compatibility corrections: 858 native cases (36 platform
skips), 506 Node cases (504 pass, 2 platform skips), 103 focused voice cases.
The separate compatible 0.2.11 candidate preserves the installed app's chat
runtime, model integration, settings and Handy fixes: 103 focused candidate
cases pass, including its actual settings frame; 89 pass under the installed
Python and the 14 QtTest gesture cases pass under the isolated test interpreter.
Candidate browser voice cases: 20 pass; native-host/embedding cases: 5 pass.
The new form screenshots were inspected. These remain synthetic audio/socket
proofs; a real OpenAI trial requires the owner's project key and setup consent.
Selected versus running deployment identity is recorded after guarded activation.
