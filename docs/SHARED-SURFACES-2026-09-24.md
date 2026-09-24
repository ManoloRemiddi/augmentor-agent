<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# One personal agent, two presentations

The September 24 user direction supersedes the earlier browser-only role policy.
DSH Desktop and Browser now use one maintained personal-agent composition and
`config/agent-persona.md`. The two existing preset IDs remain compatible aliases;
existing conversations are not rewritten or replayed. Both UIs can access either
personal preset's chats, shared saved chats, exact forks and the same tools.
Unrelated roles and subagents remain outside the personal UI boundary. Pi remains
an explicitly selectable subset with its own sessions; fresh Browser profiles now
default to DSH, matching Desktop. Explicit engine choices and saved data survive.

`services/dsh/setup.py::personal_agent_entries` owns the composition. Desktop
control still requires consent and a model with image input for screenshots.
Browser observation rules, execution recovery, memory and model/approval settings
remain shared. Browser tool access is not proof that a particular web editor can
be operated successfully. A modified installed preset requires a reviewed
migration; the installer still refuses to overwrite user customization.

Both interfaces use the authenticated product interaction broker. A conversation
has one approval presenter at a time; another open window cannot take over its
pending decisions. Browser claims that lease before submitting a task. A lost
answer acknowledgement is never retried automatically; disconnect releases or
expires the lease without granting permission.

## Speech

The sidebar's `voice.mjs` is a presentation/controller binding. The native host
starts `services/voice/browser-client.py`, which directly imports the same
`augmentor_linux.voice.VoiceSession` as Desktop. Capture, buffering, CPU VAD/ASR,
playback reserve, echo protection and interruption have one implementation. The
old browser AudioWorklet/WebAudio speech loop is removed. Resonant Voice remains
the separately versioned 0.1.16 service; no model or GPU settings change.

Both presentations support tap-to-prepare, hold-to-talk, left slide to lock,
right slide for hands-free, release/tap to send and Escape to cancel. Hands-free
and locked input survive focus changes, while hiding/closing the sidebar cancels
voice. The host stops capture if the sidebar heartbeat disappears for six seconds;
closing the native pipe also closes the worker. Only complete transcripts reach
the existing DSH session, once per request ID. Unknown submission outcomes are
shown, never resent. No second conversation engine is created.

Browser Settings → Voice uses the primary floating window's speech profile,
speed, volume, pause and default mode. Secondary named windows retain their
independent voice profiles. Settings take effect for a newly opened voice session.
The browser orb's context menu opens that section. Playback and capture use the
companion's operating-system audio devices; there is no second browser microphone
permission path. Explicit voice gestures remain the capture boundary.

## Stopped tasks

DSH can become idle without writing `turn/end` (observed after a cancelled tool).
Desktop now consumes `api-session/status` and `api-session/error` as well as durable
history. Opening/reconnecting a chat reads its current runtime status; Stop also
checks that status after the cancellation acknowledgement. The UI clears its
busy state and reconciles history without inventing a terminal event or replaying
the user's request. Browser also surfaces runtime errors for its current chat.
This fixes stale presentation; it does not assert why an upstream task stopped.

## Response metrics and data

The existing response_metrics feature is retained for both personal aliases.
Its generic implementation was selectively ported from the installed licensed
module; no private history or configuration is published. It stores at most 20
response timing records per session under `$DSH_HOME/local/response-metrics`,
including a 160-character response excerpt to identify the measured reply.
These records are private local conversation data, not diagnostic telemetry.
Observed stream rate includes the whole response step and is not server-only
decode throughput.

## Qualification and deployment

The isolated DSH setup proof now verifies identical generated compositions/tool
catalogs, a Browser filesystem read, shared saved chats, real native-messaging
approval/rejection, Qt approvals/questions and exact forks. Model responses are
synthetic fixtures. The status bridge separately read the affected installed
conversation as idle without submitting or changing it.

Source checks include controller status/Stop regression, shared worker lifetime,
no capture after release during preparation, exactly-once voice transcript
submission, unknown-outcome handling and browser hold/lock/hands-free gestures.
Run the recipes in `tests/README.md` and `scripts/dsh-setup-proof.py`.

This is a compatible 0.2.11 development update; version numbers alone cannot
identify it. Final source ref, artifact identity, selected/running builds and
physical acceptance are recorded below after staging. Public npm/GitHub 0.2.11
security-release bytes are immutable and are not silently replaced by this work.

Validation before staging: TypeScript check/build, 176 Node tests, 24 browser DOM
tests and 422 native tests pass. The real isolated DSH proof completed 16 fixture
model requests across native and browser transports, including explicit approval,
rejection, questions and exact-history continuation. The live installed speech
service returned ten voices; the new worker reached Ready with recording off and
closed normally. This readiness check did not record speech or exercise acoustic
quality. The stopped local voice service was started with its existing GPU/CPU
configuration and enabled for login. Physical microphone/echo and reloaded
Chromium acceptance remain separate from these checks.

## Combined Home client integration

The Home client source `a983491` is integrated with the shared-surfaces change
`6b2fe74`. Both personal aliases include the paired Home capability and both
Voice and Home settings are available in Browser. This avoids selecting one
local update that removes the other. The NAS runtime remains separately deployed;
this merge does not restart or modify it. Existing per-preset model/compaction
settings are preserved during the reviewed local migration. They are user
configuration, not separate maintained agent implementations.
