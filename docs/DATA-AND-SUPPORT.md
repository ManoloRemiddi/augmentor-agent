<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Data, permissions and support

Augmentor runs under your Linux account. Pi is bundled; DSH is optional. The Linux
role can use OS/file tools and consented desktop input. Browser-role tool guards
permit browser actions and optional memory recall. Approval modes govern tools;
they are not an operating-system sandbox. Pages and recalled facts are untrusted
content, not permission to run other tools.

The selected model receives your submitted prompt, applicable conversation
history and tool results. A `[clipboard]` template inserts the current clipboard
when you invoke it. Desktop observation can send screenshots to an image-capable
model after OS sharing consent. The executor creates no screenshot files, but the
harness may preserve returned images in its conversation history. Clipboard copy
writes the selected message to the system clipboard. Other applications can read
that clipboard under the desktop's normal rules.

Model keys are stored in private user configuration without encryption. Remote
model and Hindsight endpoints require HTTPS and authentication; numeric loopback
HTTP supports local services. There are two distinct memory integrations:

- **Automatic dual memory (Hindsight 0.10.0):** when enabled, committed human and
  assistant text, including voice transcripts and successful spoken reply text,
  is journaled automatically. This is enabled by default in the local journal;
  without engine configuration the text remains local awaiting processing.
  Eligible live text is processed during bounded activity windows; historical
  import is explicit. Admitted text reaches separate relationship and work banks, with
  different extraction missions. The default person is the persistent local
  profile; the project is the canonical working directory unless explicitly
  bound by trusted code. Hindsight and its configured inference service process
  that text. The tested deployment uses a local model. Cached/retrieved memory
  is supplied to the selected conversational model, which may be remote.
  Audio waveforms, images, reasoning and tool internals are excluded from this
  memory journal. Whole-memory pause stops capture/recall and processing. A separate
  processing pause preserves capture and cached recall, revoking in-flight model
  generation. Partial engine writes may remain recorded for review. Paused
  capture events are not backfilled. Gateway credentials, budgets and stage
  receipts are stored locally; gateway request bodies are not logged.
  Raw records and derived data persist; pause is not deletion. There is currently
  no coordinated automatic-memory erase UI. See [operations](MEMORY-OPERATIONS.md).
- **Optional manual library (Hindsight 0.9.2):** disabled until configured;
  retention is explicitly submitted through its library controls. Its selected
  user/project bank is a global preference, separate from automatic session
  bindings. Manual deletion follows that provider's semantics and does not
  delete automatic-memory banks, earlier model context, backups or provider logs.

Browser speech now uses the same native microphone/playback engine as Desktop,
activated by the sidebar's voice gestures. Closing the panel cancels capture; a
lost UI heartbeat expires within six seconds. The private stdio control bridge
passes final transcripts to the existing session without storing audio. Primary
Desktop and Browser voice settings share one profile; secondary windows retain
independent profiles. The shared response_metrics tool retains up to 20 timing
records per conversation locally, including a short identifying response excerpt;
see [shared surfaces](SHARED-SURFACES-2026-09-24.md).

The speech companion processes microphone audio through configured ASR and sends
reply text to configured TTS. The automatic memory journal stores the resulting
text, not the microphone stream. Speech-engine configuration, transient buffering
and audio asset licensing are described in the
[voice protocol](https://github.com/ManoloRemiddi/resonant-voice/blob/main/docs/PROTOCOL.md)
and [running guide](https://github.com/ManoloRemiddi/resonant-voice/blob/main/docs/RUNNING.md).
This does not promise that every configured external provider has zero retention.

Prompts, conversation history, settings and memory configuration belong to the
local user. The shared Prompt Library synchronizes these interfaces on this
computer, not across devices. Uninstall preserves user data by default. Backups
can contain credentials and retained source text; keep them private.

Diagnostic traces are off by default. If enabled, new trace files contain only
allowlisted metadata, with file-size and rotation limits. Old raw trace files are
not included in support exports. The Support report shows product/platform
versions and component availability. It excludes chat content, clipboard contents,
model keys, provider endpoints, memory banks, user paths, process IDs and full
environment dumps. Review the JSON before saving or sharing it. Export alone does
not send it to anyone.

This repository's checks cover the implemented boundaries and recorded fixtures.
They are not an independent penetration test. Provider policies apply to the
model and memory services you configure. Store publication needs a publisher-owned
privacy policy and accurate permissions/data disclosures for the final build.
