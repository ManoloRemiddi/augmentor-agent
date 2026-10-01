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
