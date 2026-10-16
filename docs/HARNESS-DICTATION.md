<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Original DSH microphone on the Pi Harness

The web composer now selects the original MIT DSH **0.2.1-alpha.2** microphone,
expanded recording toolbar, waveform, Stop/Cancel, device picker and stale-draft
feedback from public ref `d743267388641bc76f17c45ce8b4c231aed1d32c`. Its ten
new supplier inputs are byte-for-byte original and recorded in
[`SOURCE.json`](../apps/harness/vendor/dsh/SOURCE.json), bringing that manifest
to 625 inputs. The existing MIT notice is retained. The source audit in
[Pi voice](PI-VOICE.md#original-dsh-web-microphone--october-16-2026) remains dated
read-only evidence; this guide owns the subsequent implementation.

The microphone creates **editable draft text**. It never presses Send, starts an
agent/session, commits a chat message or enables response playback. Ordinary Send
keeps its typed-input semantics. This also works before the first chat turn and
while an existing Pi turn is running. Full conversational Native/Browser voice
remains separate and required; dictation does not replace it.

## Recognition and UI ownership

[`dsh-dictation.jsx`](../apps/harness/dsh-dictation.jsx) injects readiness and
microphone actions into the original components; it keeps the original activity
slot between model selection and Send. The existing Plugins settings page exposes
the original device picker and its input meter. The adapter reports only the
configured cached English CPU Whisper path. It offers no SenseVoice installation,
automatic download, alternative model/provider or pretend preparation progress.
Cached availability maps to standby; it does not mean a decoder or microphone is
already running. Browser microphone selection uses the original local preference.

At recording/preview start, the browser reserves a private Host recognition
operation **before** acquiring its microphone. The Host requires a companion
advertising `dictation: 1` and scoped Pi support. The privately qualified candidate
is Resonant Voice **0.1.22**, component `1e1e6880`, archive SHA-256
`5f0e2f8ac79ef7d32aa3cb13ea873563e622dca985a3af7e3bf1a1ec0d6e56c9`.
Shared application dependency pins remain **0.1.19**; this source is not an installed
upgrade. The companion source/archive/fixtures and audition assets remain private
and are absent from public application/tests/CI.

The browser receives only an opaque capture ID and public limits. Service token,
ticket, bridge ID and WebSocket stay in the trusted Host. Its recognition-only
lease skips Breeze and TTS profile creation and cannot arm synthesis. Pi remains
the only conversational SDK owner, with no SDK load needed for recognition.
Qwen/Breeze remain on the RTX 5090 and existing ASR/VAD remain on CPU. No service,
model context, concurrency, precision, GPU placement or installed profile changes.

## Transport and lifecycle

Authenticated operator-only loopback `POST /api/dictation/` operations are:

| Operation | Input / effect |
| --- | --- |
| `catalog` | `{}` or `{refresh:true}`; offline cache availability and configured limits |
| `open` | UUID `clientId`, UUID `captureId`, optional human `sessionId`; reserve and ready the recognition lease |
| `heartbeat` | Exact client/capture IDs; renew the browser's eight-second ownership observation |
| `transcribe` | Exact IDs in query; binary `audio/wav`, canonical mono 16 kHz PCM16; one submission only |
| `close` | Exact IDs; idempotently retire only that capture and join accepted local work |

Read-only inspectors cannot use any of these routes. The general JSON RPC gateway
still denies private `voice.ticket` and `voice.close`. Existing same-origin,
loopback host, bearer, no-store and maintenance admission remain in force.

The complete configured budget is retained: up to **600 seconds / 19,200,000 PCM
bytes plus the 44-byte canonical WAV header**. Binary upload avoids the smaller
JSON carrier. The Host sends at most 65,536 bytes per private WebSocket chunk and
waits for the matching utterance/cumulative-byte acknowledgement before the next
chunk or End. Exact-limit input auto-finishes once. This bounds input buffering;
an acknowledgement is not recognition completion or measured answer latency.

The original recorder owns tracks, AudioContext, resampling and late permission
grant disposal. The adapter closes on scope change, pagehide, cancellation or
transport failure. The browser heartbeats while opening, recording and recognizing;
lost heartbeats stop the Host from maintaining a private lease indefinitely.
Client/capture IDs fence stale cancellation. Host shutdown joins accepted setup,
upload, recognition and local WebSocket/lease retirement. Remote disconnect
acknowledgement is not proof the decoder process exited: the companion owns its
retiring worker and keeps maintenance busy until actual worker closure.

Original Lexical detect spans, editor revision and draft/connection scope fence
caption insertion. A changed draft retains the caption for the original explicit
Insert action. Captions remain plain text, including markup-looking characters.
Only ordinary Send creates the normal durable Pi input receipt; no automatic replay.

## Qualification and remaining work

Development checks exercise the actual Host/SDK and original Chromium UI with
independently authored recognizer/provider peers and fake browser audio. They
cover the complete audio budget, acknowledgement backpressure, pending setup/
upload cancellation, stale identities, orphan expiry, compatibility rejection,
rootless use, running Pi turns, read-only denial, stale-draft recovery, plain text
and both themes. The initial held-upload driver did not wait for its read to be
entered; the corrected driver synchronizes that admission. The first Chromium
assertion assumed an optional rewritten-input field on an ordinary user message;
it now checks the actual original content fallback. Both failed records remain.
No implementation bound, worker count or test skip changed to obtain a pass.

The private installed candidate independently recognizes one existing licensed
synthetic 7.36-second audition offline: 25/25 words, zero edits, no TTS/LLM call,
joined worker exit. This is no physical microphone/speaker or general accuracy
claim. Hosted component run **38827292939** passes Linux x64/macOS ARM64 full
suites; Windows retains its working-FFmpeg prerequisite failure and the overall
failed result. The application’s existing Windows/Office/distribution gates remain.

Exact frozen public source/ordinary/companion acceptance, an isolated MX review,
owner microphone feedback and shared distribution/pin/adoption are still required.
Current review `20261015-211446-7474ddb2` and selected installation remain unchanged
and do **not** contain this microphone integration. Full voice, physical speech,
remaining plugin/Home/Office workflows, later OS artifacts and final migration
remain open. The larger Harness goal is incomplete.

Focused reproduction after the normal build:

```sh
npm run build
node --test tests/harness-dictation.test.mjs tests/harness-dictation-host.test.mjs tests/harness-dictation-chromium.test.mjs
```

Chromium uses fake audio devices for this proof; no owner recording or private
component is required. Optional screenshots use `AUGMENTOR_DICTATION_PROOF_OUTPUT`.
