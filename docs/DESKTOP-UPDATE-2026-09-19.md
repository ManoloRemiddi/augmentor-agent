<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->
# Desktop development snapshot · 19 September 2026

This snapshot publishes the accumulated Augmentor Agent Desktop/Browser work
since the previous GitHub update. It remains a private development preview;
earlier signed/package acceptance evidence applies to its recorded artifacts.

## Architecture and ownership

- **Augmentor Agent** owns the native and Chromium surfaces, shared prompt library,
  transcript journal, lifecycle/recovery, person/project routing and DSH/Pi adapters.
- **Hindsight 0.10.0** owns automatic extraction, embeddings, consolidation,
  relationship knowledge pages and project semantic retrieval. It is reused under
  MIT and pinned by upstream commit and Docker digest; it is not vendored into the
  application. The custom automatic summarizer has been retired. Raw transcripts
  and old revisions are preserved, and journal migration runs automatically.
- **[Resonant Voice 0.1.14](https://github.com/ManoloRemiddi/resonant-voice)** is a
  separate versioned speech package. DSH remains the conversational agent. Voice
  adds replaceable ASR/TTS and a scoped audio/session protocol, not a second agent.
  The source is MIT; Breeze models and generated speech assets have separate terms.

See [dual memory](DUAL-MEMORY.md) for storage, retrieval, setup, migration,
pause semantics and rollback boundaries. The relationship bank follows the
person across projects; each project bank is independently scoped to that person.
Voice changes the interaction register without inferring speaker identity.

## Accumulated product changes

| Area | Included work | Qualification boundary |
| --- | --- | --- |
| Automatic memory | Durable text capture; separate banks; automatic knowledge pages; hybrid recall; source preservation; pause/status controls | Real local engine/model and fixture harness evidence; human continuity trial remains |
| Audio | Native/browser integration, hold/release, slide-lock, 10-minute capture, saved synthetic voices, speed/volume and structured delivery | Native preview active; browser source/fixture evidence; listening acceptance remains |
| Hands-free | CPU VAD, configurable pause tolerance, PipeWire echo cancellation, generation-aware interruption and right-drag activation | Native preview only; acoustic double-talk/echo acceptance remains |
| Desktop personalization | Skins, formatting colors, backgrounds/scenery, visual effects, independent named windows and shortcut settings | Native regression coverage; KDE-specific shortcut behavior |
| Commands and recovery | Prompt Tab vs command Enter behavior, queue/history handling, browser observation and recovery policy, connection/lifecycle fixes | Source and targeted regression evidence; earlier live checks retained in their guides |
| Distribution | Fedora RPM builder and lifecycle checks, shared/browser assets and service changes | Fedora container preview evidence; real Fedora desktop/browser checks remain |

Guides: [voice control](VOICE-SINGLE-BUTTON.md),
[hands-free](HANDS-FREE-IMPLEMENTATION.md), [appearance](SKINS.md),
[second window](SECOND-WINDOW.md), [commands](SLASH-COMMANDS.md),
[browser recovery](BROWSER-RECOVERY-REVIEW.md), [Fedora](FEDORA-PREVIEW.md).

## Verification for this snapshot

- 106 JavaScript tests pass, including real DSH 0.1.5-rc.1 and Pi 0.85.1 lifecycle
  adapters with deterministic model/engine fixtures.
- 339 native/Python tests pass using the project's PySide6 environment. The system
  Python lacks QtTest; its initial test run was not considered a product failure.
- 21 browser DOM tests pass.
- Resonant Voice: 33 Node tests and 3 Python ASR tests pass. Real DSH lifecycle
  integration with fixture LLM/TTS and 0.1.14 tarball installation/removal pass.
- The final memory/runtime subset passes 28 tests after removing the old
  selected-chat-model distillation callbacks.
- Actual Hindsight 0.10.0, CPU embedding/reranking models and the existing local
  Qwen model generated all four synthetic knowledge pages automatically. A bridge
  restart and fresh session recalled calm check-ins, SQLite and the unfinished
  export screen. Semantic retrieval and person/project isolation passed.

Live memory evidence uses synthetic text labelled as voice; it is not a physical
microphone-to-speaker assessment. Tests do not establish subjective relationship
quality, long-term drift resistance or a guaranteed end-to-end voice latency.
Generated logs/proofs, private transcripts, credentials, runtime state and model
weights are excluded from the source publication.

## Installed state

The local Hindsight container listens on loopback 8889 and persists its PostgreSQL
store in `augmentor-hindsight-data`. The existing Qwen endpoint is used without
changing its model, context, precision, GPU placement or the chat default. One
background worker and CPU embeddings/reranking bound the memory workload.

The Linux/browser DSH memory adapter is activated through a versioned user-local
release. The deployment checks task and voice idleness, backs up the raw journal
and existing files, and records paths in `~/.local/share/augmentor-memory/active.json`.
Migration is asynchronous: source capture is durable while older records process.
Native controls appear on the next natural desktop restart. The root-owned
application package and the installed Chromium extension are not replaced by
this memory-only cutover; their updated source is included here.

## Published CI evidence

[Run 35441917540](https://github.com/ManoloRemiddi/augmentor-agent-history/actions/runs/35441917540)
passed all three jobs for implementation commit `29231fdf367fdade2aee74530785d29af2bee95e`:
Debian/source/native checks, installed-package lifecycle and packaged browser.
The final fix makes the persistent memory companion participate in lifetime
leases and maintenance shutdown; installed checks verify journal backup and
socket closure. Documentation-only revisions do not change this evidence scope.
See [agent handoff](AGENT-HANDOFF.md) for continuation instructions.

## Remaining release gates

Human voice continuity and acoustic interruption trials; broader memory quality
and contradiction evaluation; real Fedora
UI/browser acceptance; and existing platform/distribution gates. This snapshot
publishes the implementation and evidence without declaring a public release.

Publication links: [desktop pull request #3](https://github.com/ManoloRemiddi/augmentor-agent-history/pull/3)
and [Resonant Voice initial snapshot](https://github.com/ManoloRemiddi/resonant-voice/commit/cac49f6).
The voice snapshot includes only catalogued synthetic audition clips; human
microphone recordings remain excluded.
