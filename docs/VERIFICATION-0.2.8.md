<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Local 0.2.8 preview verification — 2026-09-10

This is the unified browser/native preview, based on the existing uncommitted
computer-use and history work at commit `8eb63c68`. It is not the public DSH-only
0.1.32 release. DSH's npm `latest` was checked as 0.1.5-rc.1 on this date.

## Passed before local installation

- TypeScript build and 73 Node tests, including Pi/OpenCode, history recovery and
  the new desktop specialist's protocol behavior.
- Native suite: 92 tests before adding the transport/branch regressions; the final
  DSH subset passes all 14 tests, including explicit-401-only retry, same request
  identity, history pagination and refusal before an unsafe fork mutation.
- A fresh real DSH 0.1.5-rc.1 profile: actual Qt Check/Install/Save, ownership-aware
  refresh, refusal to overwrite customized presets, native saved chats and browser
  role isolation. Model Picker Augmented 1.1.2 loads, native changes its pins and
  visibility settings, and Chromium receives the same curation.
- Actual Chromium with DSH: navigation, observation, typing, click and resulting
  page verification; branch preserves tool context and source history; unsafe
  Edit is refused before child creation or prompt submission.
- Native Qt with DSH: streamed replies and durable final-answer recovery, including
  a deliberately missing final frame. The companion bootstraps local authentication
  without passing a web login token to that test process.
- Extracted runtime DEB + matching Chromium extension, using both the real Pi SDK
  and real OpenCode server: page actions, copy/scroll, reconnect without replay,
  branch context, exactly one edited submission, shared prompt operations and
  private diagnostics download. Model responses are deterministic local fixtures.

## Limits of this evidence

The new specialist has not yet completed a real desktop task using a vision model.
Previous KDE desktop-control evidence does not establish performance of that new
specialist. No macOS, Windows, other Linux desktop or new distribution certification
is implied. The current package target remains Debian 13 x86-64 with KDE Wayland.

DSH 0.1.5 fork can carry an inbox-splice containing the next input past the selected
closed turn. Augmentor refuses that ambiguous case. DSH approval/questions remain
in its authenticated web UI. These are open compatibility items before claiming
full feature parity. See [the distribution plan](CROSS-PLATFORM-RELEASE-PLAN.md).

The private preview remains separate from the website's stable public download.

## Local installation

Both runtime and desktop packages were installed at 0.2.8 on 2026-09-10.
The existing DSH profile was refreshed to the matching product integration,
retaining Model Picker 1.1.2 and user data. DSH 0.1.5-rc.1 restarted without loader
errors. The native app opened and its installed adapter passed the live local
Qwen reply, final-frame recovery, copy and no-replay checks. A separate Chromium
profile passed the browser fixture using `/usr/lib/augmentor` and the actual
updated extension folder. The user's normal Chromium profile was then reloaded through desktop control;
the extension card visibly confirmed Augmentor Agent 0.2.8.

A first package attempt correctly refused live file leases. The remaining owners
were isolated proof daemons, which were stopped before retrying successfully.
The proof cleanup now closes its own remaining runtime/prompt processes as well.
The installed-browser proof confirmed the cleanup change.
