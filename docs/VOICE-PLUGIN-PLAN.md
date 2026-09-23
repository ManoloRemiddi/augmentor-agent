<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Local voice for Augmentor through DSH

**Superseded planning baseline, 17 September 2026.** The project is now **Resonant Voice**, with its own local repository. The user selected Breeze, English, and single-5090 inference if it preserves quality and existing capabilities, with 5060 Ti fallback. The current [architecture and delivery plan](../../resonant-voice/docs/PLAN.md) and [hardware/latency qualification](../../resonant-voice/docs/QUALIFICATION.md) replace this document's model choice, deployment recommendation, component ownership and performance targets. Keep the following as the original video analysis and proposal, not a current deployment instruction. No implementation or service change has been made by this planning update.

Planning only, 2026-09-14. No implementation, installation, model loading, or service changes performed. User confirmed two NVIDIA GPUs (5090 and 5060 Ti) and English-only speech. This proposal is not an approved implementation specification.

## Recommendation

Build a distributable `dsh-voice` plugin, a local speech companion, and voice controls in the existing Augmentor surfaces. Keep DSH as the owner of model calls, tools, permissions, and conversation history. Keep the current Qwen model on the 5090; dedicate the 5060 Ti to speech after resolving its existing workload. Run voice activity detection and audio buffering on CPU.

The plugin alone cannot add microphone capture and playback to the separate Qt and Chromium applications. Those require small surface integrations. Speech workers should be independent of DSH's JavaScript event loop and replaceable through a versioned local contract. No second conversational agent is needed.

## Video evidence and lessons

Source: Codacus, [How I Built an End-to-End Local Voice Agent, and Made It Fast](https://www.youtube.com/watch?v=xbedfuqYQYA). Analysis uses the retrieved creator description and complete English automatic transcript; the audiovisual demonstration was not independently watched or benchmarked. Automatic captions can contain transcription errors.

| Video section | Lesson for Augmentor |
| --- | --- |
| 01:08–06:55: Qwen3.6-35B-A3B, Whisper, Breeze-TTS-2, Silero VAD; CPU offloading to fit 12 GB | Reuse the modular pipeline. Our separate GPUs remove the need to copy the creator's LLM offloading configuration. |
| 06:55–11:40: sentence splitting and overlapping synthesis/playback | Emit coherent phrases as model text arrives; synthesize ahead while playing, with a bounded queue. |
| 11:40–16:04: transcription during speech, deliberate end-of-turn delay, first-step reasoning changes, quantized streaming TTS | Reduce serial waiting. Reconcile provisional transcription before submitting one final user message. |
| 16:04–23:31: browser/terminal/canvas panels, faster prompt ingestion, caching, spoken progress | Reuse Augmentor's tools and transcript; expose actual work. Measure prompt ingestion and reasoning separately from audio latency. |
| 23:31 onward | Model replacement should not require replacing the voice interface. |

The creator reports fastest responses around 2.5 seconds and a middle result under 3.5 seconds, including about one second for turn completion. These are creator measurements, not a target already demonstrated on our hardware. Spoken acknowledgments do not measure task completion.

[Pithagoras](https://github.com/thecodacus/pithagoras) is a Pi front end. Treat it as a design reference, not a DSH plugin we can install. The inspected main tree at `7e1e6c6a8da1c0a8ebdf7bf9aed5effc7a5098ce` did not expose voice/audio-named files; this does not establish absence elsewhere or in another branch. Reuse of implementation would require locating the actual voice revision and inspecting its license and contracts.

## Hardware and admission

Read-only inspection found:

| Device | Total memory | Used at inspection | Current workload | Proposed role |
| --- | --- | --- | --- | --- |
| RTX 5090 | 32,607 MiB | 28,061 MiB | llama-server, Qwen3.8-27B GSQ IQ3_S MTP, port 8080 | Existing DSH reasoning and tools model |
| RTX 5060 Ti | 16,311 MiB | 13,743 MiB | Separate llama-server, same model file, port 8100 | STT and TTS workers |

The 5090 server advertises total context 524,288 across two parallel slots; the 5060 Ti server specifies 65,536. These launch values do not establish the effective context of every DSH request. An AMD integrated display controller is also present; it is outside the requested two-GPU compute plan.

Before deployment, identify consumers and the service owner of port 8100. Retire or relocate that workload deliberately if the 5060 Ti is to become the speech card. Its present free memory is not enough to assume a comfortable speech installation. Do not automatically terminate it, shrink the 5090 configuration, or spill speech onto the 5090.

Select devices by GPU UUID. Load a single chosen TTS model and a single STT model, then measure peak simultaneous memory and leave approximately 2–3 GiB headroom as an initial admission policy. Actual limits depend on the model/runtime measurements. Prioritize transcription when the user starts speaking; cancel obsolete TTS work. Keep models resident during an active voice session, with optional idle unload, not periodic dummy inference.

## Candidate speech stack

| Component | Initial candidate | Qualification |
| --- | --- | --- |
| Speech detection | Silero VAD on CPU | Tune for the microphone, pauses, and room noise. VAD does not supply acoustic echo cancellation. |
| Speech recognition | faster-whisper, compare small.en and larger English-capable variants | Evaluate accent, technical names, partial stability, final latency, and GPU contention. The inference library alone is not a complete streaming session controller. |
| English TTS reference | Breeze-TTS-2 through audio.cpp, Q8 | Closest to the video; verify incremental PCM, cancellation, peak memory, quality and Blackwell build support. |
| Product TTS candidate | Qwen3-TTS 1.7B CustomVoice; compare 0.6B if necessary | Published weights carry Apache-2.0; benchmark the actual serving path and voice quality before selecting it. |

[Silero](https://github.com/snakers4/silero-vad) documents lightweight CPU inference. [faster-whisper](https://github.com/SYSTRAN/faster-whisper) documents CTranslate2 inference and quantized execution. Versions and GPU builds must be pinned only after testing.

[Breeze's model card](https://huggingface.co/BreezeBlue/Breeze-TTS-2) documents English/Chinese and restricts model weights and self-hosted outputs to research/non-commercial use. Its source-code license is separate. Keep it an evaluation option; do not assume it is suitable as the default for commercial Augmentor use. [audio.cpp's Breeze documentation](https://github.com/0xShug0/audio.cpp/blob/main/docs/models/breeze_tts.md) documents Q8 storage and incremental streaming. [Qwen3-TTS CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice) is a candidate with Apache-2.0 weights. Published latency claims from other GPUs are not 5060 Ti guarantees.

## Integration boundaries

The maintained source is this repository, following [composable ownership](COMPOSABLE-AUGMENTOR-PROPOSAL.md) and the current [feature matrix](FEATURE-MATRIX.md). Older Pi-only and setup documents contain historical limitations; inspected source can be ahead of installed release candidates.

Proposed ownership:

- `adapters/dsh-voice`: plugin configuration, allowlisted sessions/presets, assistant text/status subscriptions, connection to the companion. Package it separately using the existing DSH bundle pattern and tested 0.1.5-rc.1 compatibility boundary.
- `services/voice`: audio session state, STT/TTS adapters, buffers, health, GPU admission and cancellation. Serve authenticated local connections; heavy inference stays in worker processes.
- `packages/voice-contracts`: proposed protocol and shared fixtures, including session/turn IDs, stream generation IDs, sequence numbers, PCM format, capabilities and errors.
- Existing Qt and Chromium surfaces: microphone permission, capture/playback, input/output selection, listening state, draft transcription, mute, push-to-talk and Stop. Browser audio should use a dedicated bounded stream; keep control messages on the existing bridge. Qualify MV3 lifecycle and microphone ownership explicitly.

These are proposed paths, not created modules. A later Pi adapter can reuse the speech service; DSH is the initial target.

Existing code provides useful seams: `agent/assistant-stream` and distinct `text-delta`/`reasoning-delta` handling in Adaptive Reasoning; request hooks for reasoning policy; tool execution/status events; responsive steering; authenticated product endpoints; session-scoped desktop/browser tool boundaries. Native approvals exist in current source but require release qualification. Do not equate source presence with installed support.

Runtime flow: microphone → local VAD and incremental STT → finalized text submitted once through the current Augmentor DSH route → existing Qwen on 5090 → assistant text deltas → phrase buffer → TTS on 5060 Ti → incremental audio playback.

Only the initiating voice session receives audio. One capture/playback owner should hold the local voice session at a time, avoiding simultaneous Qt and browser microphones. Reattachment reads state without resubmitting user text or replaying old speech. Keep raw microphone audio ephemeral by default; retain ordinary text in DSH history under existing controls. Speech service failure should leave text chat usable.

## Conversation behavior

Start with push-to-talk and read-aloud. Add hands-free mode after the audio path works. Use roughly 700–1,000 ms of silence as a tunable starting point for endpoint detection, plus an explicit finish action. Partial STT is preview data: it must not trigger tools. Commit one finalized utterance with an idempotency identifier.

Speak only user-facing assistant text. Suppress reasoning, tool arguments, raw HTML and code blocks. Encourage concise spoken responses and place detailed reports in visible artifacts; do not silently truncate the user's requested content. Build phrases with abbreviation/number handling and a maximum wait/length, rather than treating every period as an end. Bound queued audio by duration as well as item count.

For interruption, stop local playback immediately and invalidate queued/in-flight audio with a generation ID. Late chunks must be discarded. Recognized corrections should use the existing DSH steering behavior, which defers changes during active tools to a safe boundary. Explicit task Stop uses the existing cancellation path and clears pending work. Stopping sound, cancelling inference and undoing a completed external action are different operations. Never replay unknown-outcome actions.

Track playback progress separately from generated text so the interface can show an interrupted answer and avoid assuming the user heard all of it. Test with a headset first; speaker mode requires echo cancellation and separate qualification against self-transcription and false interruptions.

Do not copy the video's blanket first-step thinking-off policy. Our Adaptive Reasoning evaluation already found quality regressions for some writing tasks. Keep one owner for reasoning selection. Add only evaluated voice-specific rules there; let the voice plugin request concise style without overriding reasoning independently. A short cached acknowledgment can report received input while the actual model thinks. Tool progress must reflect real lifecycle events, be rate-limited, and yield immediately to substantive speech.

## Tools and visual parity

Voice requests should use the tools already granted to the selected surface. Browser DSH has page navigation/snapshot/input; native DSH has its existing desktop and OS tools. Voice grants no additional capabilities. Verify image support on the chosen model route before promising screenshot descriptions.

The video's combined browser, terminal and live canvas is additional UI scope. First show existing tool activity and link generated files. Then add work panels to the current surfaces where useful. A live editable document canvas is a separate artifact/editor feature. Native voice must not silently inherit browser-role tools: combined workflows need an explicit cross-surface contract or must remain within the active surface's capabilities. The bounded Pi desktop specialist is not currently a DSH feature.

## Delivery sequence and acceptance

1. **Resource and model qualification:** resolve port 8100 ownership; benchmark STT and candidate TTS independently and together; record exact models, revisions, licenses, CUDA/runtime support and device selection. No deployment until the speech workload fits without disrupting the 5090 route.
2. **Basic DSH voice slice:** companion, packaged plugin, Qt push-to-talk, visible transcription, streaming read-aloud, mute and Stop. Prove one submission per utterance, correct session routing, selected-model preservation, and text-chat survival after worker failure.
3. **Conversation latency:** incremental STT, endpoint detection, phrase queue, streaming playback, interruption, generation invalidation, and existing steering integration. Prove that tool actions are neither duplicated nor treated as undone.
4. **Agent feedback and browser surface:** truthful progress, concise spoken artifact summaries, browser capture/playback, capability negotiation and single-owner arbitration. Check pending approvals, switching chats, reconnection, extension suspension, and microphone denial.
5. **Product qualification:** end-to-end native/browser runs, background-load tests, packaging/uninstall, optional idle unload and compatibility matrix. Add richer work panels after voice reliability passes.

Initial goals, not measured promises: simple warm conversations should aim at median end-of-speech to substantive first audio ≤2.5 seconds and p95 ≤4 seconds; detection-to-playback-stop ≤200 ms; TTS preferably at least twice real-time speed with STT active. Report cached acknowledgment time separately. Deep reasoning, long contexts and tool completion need separate measurements, not the same latency promise.

Record endpoint delay, final STT lag, first model text, phrase-buffer delay, first TTS PCM, audible playback start, underruns, interruption time and GPU peaks. Include accents/technical names, silence, long pauses, long answers, interrupted tools, long contexts, cold starts and a second busy chat. Unit/contract tests are necessary for races; real microphone-to-speaker measurements and actual DSH tool runs establish user-facing evidence.

Next implementation deliverable, once requested: the resource/model qualification slice, followed by a minimal DSH voice path. The present task stops at this plan.
