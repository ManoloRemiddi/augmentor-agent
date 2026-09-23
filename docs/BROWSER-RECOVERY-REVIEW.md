<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Browser recovery review — 19 September 2026

The latest desktop DSH session was inspected directly from its compressed event
log: `augmentor-linux-product-265dba26dd104f87af326ef2f911c905`.
The proposed “try two alternatives” instruction is insufficient: the failure
included incorrect targeting, misleading tool success, missing capabilities,
and unsupported claims about the interface. A fixed attempt quota could reward
repeated guesses or unnecessary actions.

## What the session establishes

| Events | Observation | Implication |
| --- | --- | --- |
| 247–248 | Snapshot read the manifesto tab rather than the requested NAS. | Tool access alone did not establish the correct target. |
| 257–265 | Three snapshots reported blank title, URL and text. | This was repeated failed observation, not a single abandoned attempt. |
| 243, 345–346 | Desktop snapshot required connection; connection then failed with “This preview requires one connected monitor. No sharing session was opened.” | No successful screenshot was obtained. Promising to take one next time does not fix the backend restriction. |
| 318–333 | Guessed settings routes, then described a sidebar without supporting observation. | The answer exceeded the evidence. |
| 360–406 | Clicked `body` to extract text, then guessed selectors, including nonstandard CSS. Some responses were merely “Clicked”. | The action channel was being used as a read fallback; missing acknowledgements could appear successful. |
| 424 | User reported the update was running. | This is a user report, not an independently verified completed upgrade. |

The session also spent substantial effort probing administrative commands and
possible API endpoints before using the requested vendor interface. The revised
instructions preserve the user's chosen workflow and prohibit speculative
administrative detours as a substitute for observing it.

## Implemented changes

1. **Durable instructions.** `config/browser-recovery.md` supplies both generated
   DSH personas and the Pi system prompt. The same guidance was appended to the
   user's existing `~/.dsh/AGENTS.md`, preserving prior instructions and saving a
   backup under `~/.local/state/augmentor-repair-backups/browser-recovery-20260919-120149/`.
   It requires evidence, useful alternatives, bounded recovery, and accurate
   capability reports, rather than an arbitrary attempt count.
2. **Better observations.** The extension makes at most three DOM reads, separated
   by 350 ms when content is missing. It collects visible controls with exact CSS
   selectors, bounded same-origin frame text and open shadow-root text, and omits
   the agent overlay. Frame/shadow text is explicitly not a main-document action
   target. Missing script output is an explicit failure, with known tab metadata.
3. **Explicit targeting.** Snapshot and screenshot tools accept an optional tab
   ID from the tab list. The list identifies the current work tab. Observation
   selects that target without navigating or activating another tab.
4. **Browser screenshot tool.** DSH and Pi can request an actual image of the
   visible work tab without the single-monitor desktop backend. They reject
   text-only model routes. The extension rejects inactive targets and discards
   captures if the target changes. It excludes image bytes from diagnostic logs
   and caps the payload for native messaging.
5. **Action guards.** Following an inconclusive observation, DSH/Pi refuse click
   and type until a readable observation or screenshot arrives. Page-root actions
   cannot be used to read text. Missing action acknowledgements report an unknown
   outcome instead of success. No mutation is automatically retried.

These guards address specific failure paths; they are not a proof that a model
will never guess, misuse another tool, or make an unsupported final claim.

## Verification

- TypeScript check and build passed.
- Full Node suite: **105 passing** (including real isolated Chromium DOM/layout
  recovery and synthetic targeting, permission, cancellation and image contracts).
- DSH setup Python tests: **4 passing**.
- Isolated DSH plugin proof passed with its real schema validation, compiled
  bundle and WebSocket transport. DSH services and browser replies were fixtures;
  this was not a live-model acceptance run.
- `git diff --check` passed.

The real Chromium test covers delayed application rendering, exact selectors,
frame/shadow text, empty pages, absence of speculative clicks, overlay restoration,
and exclusion of hidden text/password values. Screenshot permission/race behavior
and image delivery are contract tests, not proof of capture in the installed user
profile. No NAS update or other NAS action was performed during this review.

## Activation and remaining acceptance

**Saved now:** persistent DSH instructions, for subsequent instruction loading.
**Built and tested in source:** extension, DSH browser plugin/policies and Pi
runtime changes. The running installation has not been replaced or restarted.

The user's loaded Chromium extension is in the legacy Desktop checkout, while
the native application runs packaged code under `/usr/lib/augmentor`. Updating
this repository alone does not update either runtime. Deploy the observation
module and action executor together, along with the matching browser plugin,
policies and runtime/prompt assets; then reload the extension and restart/reload
idle runtimes. Preserve the existing unrelated edits in both working trees.

Chrome capture requires an applicable `activeTab` grant or `<all_urls>` permission.
The patch retains existing permissions. When a grant is absent, it explains how
to invoke the extension on the intended tab instead of requesting broader access
or pretending a screenshot succeeded. See the official
[Chrome captureVisibleTab documentation](https://developer.chrome.com/docs/extensions/reference/api/tabs#method-captureVisibleTab).

Installed acceptance should use a harmless local delayed-rendering fixture and
the selected vision model: start from a different work tab, select the intended
tab, recover its controls, obtain a real screenshot with the current permission
state, and verify the resulting answer. A permission refusal should produce a
specific blocker. No firmware update is needed to validate this behavior.
