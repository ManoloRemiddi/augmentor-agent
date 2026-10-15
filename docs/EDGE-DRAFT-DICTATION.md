<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->
# Direct Handy capture for the EDGE surface

Development, 15 October 2026. The companion presentation lives in
[Corsair-XENEON-EDGE](https://github.com/ManoloRemiddi/Corsair-XENEON-EDGE).
It imports the selected native Augmentor Window/controller/composer rather than
implementing another agent loop. Its layer-shell host requests no keyboard focus
for ordinary panel actions. Direct dictation must therefore never use global
paste: another application remains the keyboard target.

The existing per-session authenticated dictation broker now admits `draft.start`,
`draft.stop`, `draft.poll`, `draft.cancel` and `draft.release`. A start supplies a
fresh 32-character hexadecimal token and the owning live process ID. All later
operations must present that token. The bundled Handy status advertises
`direct_draft_capture: true`; an older component fails explicitly, without
emulating a keyboard shortcut or starting a second speech engine.

Start acknowledges microphone readiness. Stop acknowledges transcription startup;
poll returns recording/transcribing/complete/cancelled/error, worker status and,
only for the matching direct request, its result. Repeated polling is read-only;
the UI accepts a result once and releases it. Capture uses the existing selected
model, load manager, microphone and ASR settings. It bypasses the shortcut action's
clipboard, typing, history and auto-submit pipeline. No model/provider or GPU
settings are changed by this API.

Handy reserves one microphone holder for the operation. Conversation voice,
shortcut dictation and settings edits cannot claim it concurrently. Cancellation
discards text, while a still-running transcription retains exclusion until it
finishes. The broker cancels the exact token when its owner dies or its bounded
180-second lifetime expires; it waits for a worker before release. Restart never
replays start/stop actions. Existing global dictation remains on its original path.

The EDGE caller binds the result to a session, draft revision, selection and page.
A changed session/draft/page cancels or discards late text. Dictation inserts into
the original selection and never calls Send. Explicit keyboard editing remains a
separate focus-taking action. Microphone readiness, ASR completion, text insertion,
actual chat execution and physical touch/focus are separate acceptance checks.

Verification commands (fixtures, no physical microphone):

```sh
PYTHONPATH=apps/native python3 -m unittest discover -s tests -p test_draft_capture.py -v
PYTHONPATH=apps/native python3 -m unittest discover -s tests -p test_dictation.py
```

Six new broker cases and 22 existing dictation cases passed in the MX environment.
The companion repository owns four capture and five real-widget contract tests.
An isolated X/DBus actual-engine test recognized fixture speech through a verified
virtual microphone using the cached Parakeet model on CPU, returned the transcript
without altering an external draft or clipboard, cancelled a second recording and
exited cleanly. Its first run exposed a missing cold-model load; start now invokes
the existing model loader before capture. No physical microphone was used. Live deployment must copy the existing compatible artifact,
apply these reviewed broker/component changes, qualify it, then stage/activate
through `augmentor-update`. Do not overwrite selected release files or restart
active conversation windows to update the broker. The installed artifact and
physical owner acceptance will be recorded after qualification.
