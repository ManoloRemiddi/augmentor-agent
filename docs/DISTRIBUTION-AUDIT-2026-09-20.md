<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Installed/GitHub/distribution audit — 20 September 2026

## Findings before release work

The product checkout at `37c2d4f`, speech at `009b4c4` and Adaptive Reasoning at
`15d9981` matched their remote branches with clean working trees. Product and
speech repositories were private; the public `augmentor-agent-app` repository
contained guidance and an older Fedora preview, not a current complete Debian
bundle. Product development remained on PR #3, ahead of `main`.

| Component | Installed versus published source | Distribution gap |
| --- | --- | --- |
| Native desktop | 82 files matched; remaining differences were the 0.2.8 label and two newer mobile-touch changes in 0.2.9 source | No current complete public Debian download |
| Second window/shortcuts, skins, recovery | Present in source and installed native UI | Fresh-user startup/second-window setup needed integration |
| Active dual memory | All 15 checked adapter/service/compiled files matched | Docker/model engine provisioning separate from app installation |
| Resonant Voice | 18 runtime files matched; launch helper source was newer and already published | No guided portable engine/service installation |
| Adaptive Reasoning | All five runtime files matched 0.2.2 source | Public release remained 0.2.0; defaults contained developer-specific routes |
| Browser shipped inside selected desktop | Six files differed; voice/worklet/orb and observation modules absent | Matching extension needed rebuilding and public distribution |

This checks code and components, not private message content. It does not claim
that the user's currently loaded Chromium extension is identical to the copy
inside the selected desktop artifact. No live chat, model placement, DSH profile
or browser session was replaced during this audit.

## Release contract

The complete Debian bundle is built from clean, recorded source commits and
matched desktop/browser artifacts. It includes public source snapshots while
leaving private repository histories and all machine-specific state private.
The [guided installer](COMPLETE-INSTALL.md) provisions required components with
fresh local secrets and explicit model/voice/memory choices. Existing-user
migration is separate from first installation; runtime compatibility and retained
data take precedence over simply replacing files.

Adaptive Reasoning 0.2.3 retains the 0.2.2 replay-log fix and starts with neutral
routes. Resonant Voice 0.1.15 adds pinned Linux provisioning and includes the
published explicit GPU admission correction. These package releases are distinct
from the unchanged currently running user's 0.2.2/0.1.14 packages.

Website captures use the actual native surface with synthetic demonstration
content and built-in appearance settings. They must never capture the user's
conversation, private window titles, personal background image or credentials.
The website must label capabilities and platform limits to match the artifacts.
macOS parity follows this Linux distribution/website work.

## Qualification and release identity

The complete public candidate is `v0.2.9-complete-preview.1`:

- Augmentor source: `07fd8080319881fd83dbe730a411edf5b563a75f`.
- Resonant Voice: `cc9b73d64313e6c02b226cce9b01346f8e98994a` (0.1.15).
- Adaptive Reasoning: `64a1ef82e3d69f57a69809d530c1b9ed0bc67480` (0.2.3).
- Archive SHA-256: `8149ac66866d79422cdcd84f672b228c4b6ac7db162e07eef846454e20035da4`.

Completed checks:

- Native product suite: 388 passing. TypeScript build/check, 114 Node tests and
  21 Browser tests passed. This includes five focused complete-installer checks.
- Real fresh DSH composition: all three external plugins and shared product,
  prompt and memory adapters installed; restart, authenticated discovery and
  saved connection succeeded with fixture model metadata.
- The exact packaged bundle installed in pinned Debian 13 as a new ordinary user.
  Private key-file permissions, DSH/plugin/product integration, native Qt
  rendering, second-window/login/recovery entries, matching browser registration
  and repeat-run preservation passed. Test used `--no-services` in the container:
  it does not establish a physical desktop login, microphone, GPU or model reply.
  This test found and fixed missing pnpm provisioning and a fresh empty-profile
  compatibility bug. pnpm 11.23.0 is now in the installer runtime lock.
- Voice: 33 Node and 10 Python tests; real DSH structured-speech fixture and
  package install/remove proof passed. A fresh isolated CPU speech runtime was
  built from the pinned source; its health endpoint and pinned ASR imports passed.
  The model file was checksum-verified from a local cached copy. This does not
  claim a fresh model download or a physical microphone/playback trial.
- Adaptive: 63 unit tests, real DSH integration including compressed cold-history
  reopening, greeting/structured-speech fixtures and package install/remove passed.
- Artifact review verified Debian and Browser hashes, file inventories and native
  binary notices. Reviewed source snapshots exclude private repository histories,
  installed settings, conversations, memories and model files; known private
  credential values were checked without emitting them.
- Website captures use actual Qt widgets with synthetic conversation/model labels,
  built-in Blossom lake skin and a six-second silent butterfly animation. Local
  browser verification covered rendering, video decoding/playback and motion pause.

The current live installation was preserved. Code publication and this fresh-user
release do not silently upgrade the user's running 0.2.8/voice 0.1.14 deployment.
Future installed updates follow the coordinated deployment/migration contract.

## Next priority: current macOS parity

The existing ARM64 development candidate already has a self-contained app,
transactional install/rollback, browser registration and a launchd shortcut
service with prior Mac Mini evidence. It is not qualified for the newer Linux
voice, dual-memory and desktop-selection changes. Next: re-audit those deltas,
provision speech using an explicit supported Mac backend, verify second-window
and login/recovery behavior, test browser/native permissions, then build and
qualify one matching distribution. Developer ID signing/notarization and actual
logout/login, microphone/playback and desktop-control checks remain public
macOS release gates. Do not advertise full macOS compatibility from Linux tests.
