<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Browser observation repair — 1 October 2026

A readable shopping page returned product names and prices, but September 27's
early context pruning removed the middle of the result before its first model
request. Navigation and control inventories consumed the retained head/tail.
This is a tool-context regression; a separate research browser's HTTP 503 does
not establish that the user's signed-in browser failed. The agent did not use
the original-result recovery tool and later read an unrelated tab.

## Shared repair

The personal DSH context adapter preserves fresh `browser_snapshot` and
`browser_tabs_list` results for their next model step, with a combined admission
limit of 64,000 Unicode code points. The last assistant-message boundary proves
prior evidence has been consumed: DSH can reuse request headers across steps.
Older observations and oversized batches use the configured content pruner.
Binary sanitization still runs first. Other tools retain early pruning.
True context pressure and upstream summarization remain independent.

Every adapter-trimmed result now identifies its saved original sequence and the
`tool_result_excerpt` call needed to recover the omitted text. The excerpt tool
also accepts `find`: a bounded, literal, case-insensitive search starting at the
given offset. It never re-executes a browser action, reads another chat, or
reintroduces binary text. Original evidence is historical; obtain a fresh
observation before acting on changed pages.

The Chromium observer reads a visible main landmark first, falling back to the
document when none exists. `scope: "document"` includes surrounding navigation.
Content controls and heading links precede navigation in their inventories.
Text (6,000 code points), controls (60), and links (40) have independent offsets
and explicit totals/next offsets, so long pages are read in bounded parts.
Both DSH and Pi expose the same observation arguments. The browser still
excludes the Augmentor overlay, password values and hidden DOM text.

Navigation and snapshots return their actual tab ID. Tab listings put the work
tab first. An explicit observation tab ID reads that tab without changing the
target of subsequent navigation/click/type; an incorrect observation cannot
silently redirect later work. Read the work tab again before acting. No tab is
activated merely to observe it, and screenshots still require browser permission.

## Verification

- TypeScript check/build, 196 Node tests, 44 Browser tests, and six DSH setup
  tests pass on Linux with Node 24.19.0 and DSH 0.1.5-rc.1.
- The real DSH fixture verifies product/price text survives its first request,
  older text is trimmed with a recovery reference, and literal search recovers
  it without replay. Oversized/browser-binary cases retain their limits.
- Isolated real Chromium covers navigation-heavy pages, main/document scopes,
  paged text/control/link recovery, hidden/password exclusion and zero clicks.
- The real compiled DSH plugin and WebSocket proof validates schema support,
  forwarded paging arguments, tab identities, missing acknowledgments and the
  existing image/permission contracts. Its browser/model responses are fixtures.

These checks establish the shared code contracts, not every model's buying
advice, Amazon availability, or installed macOS adoption. Linux and macOS use
the same Chromium observer and DSH adapter; no OS-specific behavior or UI layout
changes. Physical Mac/live-site acceptance is recorded separately when run.

## Installation and rollback

Stage the modified context adapter, compiled browser plugin, observer/action
executor, Pi browser binding and recovery guidance over the selected compatible
artifact through [augmentor-update](DESKTOP-DEPLOYMENTS.md). Preserve the product
version, runtime, model, speech and application-SDK composition of that artifact.
Update the owned preset paths/plugin inventory after checking host idle state;
retain private backups and ownership hashes. The unpacked extension must adopt
the matching observer/executor through Reload. Preserve its ID and saved chats.

Source, selected build, loaded preset generation and loaded extension are separate
states. Rollback needs the previous desktop selection, backed-up preset/plugin
ownership files and previous unpacked extension code. Original conversation
events stay append-only. Never restart active work or replay an uncertain action.

## Installed Linux evidence — 1 October 2026

Implementation `13a24e2` was selectively applied over the September 30 SDK
artifact `91ae4b61eb4ce837477acaa19edbd8be1dbe21e5a2e047baf7a61e2a211484b3`.
The managed updater staged and activated compatible product 0.2.11 release
`20261001-161942-544b2e90`, with artifact SHA-256
`9a68b2442a998e0d0bffafc4c37ec8c1a54aa7b712c53c15dfabf664d4157d08`.
The existing SDK composition, product identity, interpreters and speech dependencies
were retained; this is a mixed compatible artifact, not an unmodified source build.

The two owned personal preset adapter paths and recovery guidance, compiled DSH
browser plugin and unpacked 0.2.11 extension observer/executor were updated after
ownership validation, private backups and shared-host idle checks. The DSH service
restarted while idle; open native windows stayed open and reconnected. Authenticated
plugin inventory reports the new adapter active in both Desktop and Browser
compositions and the browser plugin active. All 16 checked model/configuration
and saved-selection files retained their original hashes.

A separate restricted real-model harness loaded the installed adapter and returned
the original saved 18,228-character Amazon observation. The local Qwen model made
two requests; the complete fresh tool result reached the model, and its answer
correctly recovered the observed Lefant V1 price of EUR109.99. This uses historical
page evidence with an actual model, not a fresh Amazon availability check. No
click, purchase, navigation, user-chat prompt or model-settings change was possible.
An initial harness attempt lacked declared reasoning capability and was rejected
before inference; declaring its own minimal-effort capability enabled the test.

**Chromium extension reload remains pending.** Its new files are installed, but
this Codex chat has no external-Chromium control connection. Reload Augmentor
Agent in `chrome://extensions/`, then perform a fresh read-only Amazon comparison
in the existing chat. The extension ID, permissions and saved browser chats stay
unchanged. Source/isolated-browser checks and archived-page model qualification do
not establish that the open extension has adopted the new observer.

Primary, secondary and mobile native windows remain on
`20260928-093018-2d4431f6`, online with voice available and the selected update
pending. Their context handling already uses the refreshed shared DSH service;
native UI adoption happens at close/reopen or login. At this local-install checkpoint, installed Mac adoption and public release
packaging remained unperformed; subsequent public packaging is recorded below. Rollback includes the previous
selection plus the privately backed-up presets, plugin inventory and extension
files; desktop selection rollback alone does not undo backend/extension updates.

## Public distribution — 1 October 2026

The shared repair and general task-reliability dependency are merged into the
canonical application repository and packaged as matched 0.2.13 Linux and Mac
previews from clean source `0eb2ec112afa52b886b63606f80967198a7feb0c`.
Both public downloads match the tested candidates byte for byte. See the
[0.2.13 release record](RELEASE-0.2.13.md) for exact URLs, checksums, package/CI
qualification and website publication. The Mac source-notice copier additionally
preserves all verified upstream notices, including test-directory README files.
This is a general capability repair across websites and task types; historical
Amazon evidence is one regression case, with no shopping-specific agent or rule.

Public packaging does not change the owner's selected compatible 0.2.11 artifact,
open Linux windows or existing Mac installation. The installed Chromium Reload
and fresh live-site acceptance remain separate manual adoption steps.
