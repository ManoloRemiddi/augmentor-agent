<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Synthetic voice protocol peer

`synthetic-voice-peer.mjs` is authored test code based on Augmentor's public
adapter and test expectations. It issues loopback tickets, receives adapter
events and emits fixed transcripts and PCM. It has no recognizer, speech model,
device implementation, private configuration reader or copied Resonant Voice
source. `codex-voice.test.mjs` uses it through the actual pinned Codex runtime,
native adapter/Qt controls and Browser native-messaging bridge.

These tests verify Augmentor request identity, text forwarding, cancellation and
client playback plumbing. The scripted peer's ordering/cancellation behavior
does not qualify the real speech service. Physical audio, hands-free behavior and
the separately installed production companion still need independent testing.

Public tests must not import private sibling checkouts or package their source
into archives. Production voice remains a separately installed dependency.
