<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

The original click-preview follow-up is now described in [file previews](HARNESS-FILE-PREVIEWS.md). The reference qualification below remains evidence for its preceding installed runtime.

# Original Harness file references

The copied DSH `@` menu now discovers paths in the selected Desktop conversation's
workspace and inserts original atomic file/folder chips. Original rows, icons,
folder chevrons, Tab drill-down, breadcrumb navigation, quoted paths and editor
presentation remain. A settled folder with spaces closes its quote; drilling
keeps it open, matching the supplier's completed-directory grammar.

This preserves the public DSH file-reference contract: a selection contributes
ordinary `@path` or `@"path with spaces"` text. It neither reads file contents nor
attaches a file. The supported Pi owner's effective `read` tool remains the
content boundary. The unchanged supplier static guidance is composed for Desktop
owners with `read`, including explicitly granted delegated readers; browser-only
owners receive no local file-reference guidance or discovery. Candidate lookup
loads no additional AgentSession and runs no provider/tool action.

## Public reuse and namespace

The pinned MIT DSH baseline is
**d743267388641bc76f17c45ce8b4c231aed1d32c**. Four runtime supplier modules retain
the original path search, grammar, types and static guidance; NodeNext import
substitutions and guidance extraction are marked in their hash/provenance record.
Three added GUI supplier files supply original pure row/breadcrumb/value helpers
and translations. The helper module changes exports only and its supplier
`apply` is not mounted. The GUI selection has **407 files**; all preceding 404
selected file bodies remain unchanged. Original MIT notices and copied CSS remain
preserved. The existing Apache-2.0 dsh-context selection is unchanged.

`session.fileReferences` takes `{sessionId, query}` and returns path/kind records.
It requires operator authority and a current non-archived Desktop conversation;
read-only inspectors, browser-only and delegated conversations cannot discover
local paths. Both initial and completed authority checks use the current
workspace. Discovery uses the same cwd namespace as Pi's built-in filesystem
tools, excluding descendant symlinks and traversal outside that root.

The original provider returns at most 20 candidates from a 50,000-entry bounded
index, with its existing build-directory exclusions, hidden-file rules and fuzzy
ranking. Directory queries read current metadata; bare queries reuse the index.
The October 17 adapter correction below supersedes the earlier stale-while-refresh
behavior: known invalidation waits for a fresh index on that same lookup.
The adapter keeps at most eight session namespaces, discarding an old
workspace namespace when its cwd changes. Queries are bounded to 4,096 UTF-16
units and exclude control characters. Abort/revocation/session changes cannot
insert stale candidates. HTTP cancellation reaches the search caller; search
disposal cancels its bounded background index. No file contents are prefetched.

## External file discovery correction — October 17

Rich spreadsheet/deck GUI qualification exposed a real adapter gap: a file saved
externally after the first fuzzy lookup stayed absent until an agent tool
invalidated the index. The unchanged supplier also answers the first invalidated
lookup with old paths while rebuilding; a pasted complete filename need not
trigger another GUI lookup. A direct reproduction returned no candidate for the
newly created file before this correction.

The Pi adapter now checks root identity, timestamps and a bounded fingerprint of
root entry names/types on each bare query. Filenames are needed because rapid
changes on MX Linux can share a directory timestamp. Root changes and agent-tool
invalidation await a fresh supplier index. Nested external additions refresh on
the first query after the index reaches ten seconds old; there is no idle timer
or recursive polling. Root witnesses and indexes are bounded to 50,000 entries,
with original 20-result ranking/exclusions. Paths beyond those bounds are not
guaranteed discoverable. Directory drilling remains live.

One pending traversal is shared per session. Cancelling a window cancels its
wait, while another window can finish. Concurrent invalidation is rechecked
after traversal; cwd changes, LRU eviction and close dispose the old namespace.
Replacing an index does not dispose a generation still serving another reader.
Root errors are surfaced rather than treating stale paths as current. Discovery
still reads metadata only; original MIT search/menu modules and Host authority,
maintenance and draft contracts remain unchanged.

TypeScript/check and 27 focused Node checks pass without failures or skips,
including actual Chromium file-menu, draft, PDF and spreadsheet lifecycle cases.
New regressions cover first-lookup external add/rename/removal, missing roots,
nested expiry, immediate tool invalidation, overlapping cancellation/invalidation
and close/cwd/LRU cleanup. A separate actual rich XLS/XLSX/PPT/PPTX GUI diagnostic
also passes with files added between previews.
[Rich GUI evidence](../release/office-rebuild/rich-sheet-deck-qualification-20261017.json).
The broader source cohort passes 270 Node and 41 Python checks, including
original queue/plugins, migration lifecycle and the default Office engine.

The correction is now installed in both actual MX reviews at **97d95d58 /
20261017-095821-fb78d6df**, artifact
`1d004a08ac3e8a33b480b1c22c1087fab22ec953935247bde7beded33f81388d`.
Fresh ordinary and exact sealed repeat the 270 Node/41 Python cohort; all 1,120
compiled files and 24,710 sealed inputs verify. Guarded backups/adoption preserve
four conversations/all 36 authoritative prefixes and shared settings. Both actual
GUIs pass with no settings/agent actions. The installed default Office engine,
DSH and production Desktop stay unchanged. Hosted CI remains separate.
[Installed qualification](../release/harness-file-reference-freshness-qualification-20261017.json).

`host.describe.activeFileReferences` counts waiting discovery calls, including
the native RPC carrier. They veto guarded maintenance before quiescing. Operator
HTTP carriers retain their separate reception/response guard. Completion,
rejection and abort release their own lookup count. A background metadata index
is not an execution owner or a pending mutation.

## Draft continuity

Private draft records retain optional `references` in clipboard-text coordinates:
source, ref, label, file/folder appearance, clipboardText, ordered offset/length
and an optional invalid flag. They persist no runtime node keys or occurrence
IDs. Legacy version-1 plain records read without modification; only a rich edit
adds this optional field. At most 256 ordered, non-overlapping exact-text spans
are accepted, with source/grammar/label validation. Unsupported identities cannot
be silently substituted. An invalid saved reference blocks Send.

Reference-only edits use the text revision even when clipboard text is identical.
Separate attachment revisions remain independent. Reload and cold Host/new-origin
restoration reconstruct the original Lexical nodes and decorators, preserving
their clipboard and ordinary prompt projection. The existing durable submission
marker freezes edits, explicit acknowledgment preserves rich content, and matching
accepted queue settlement clears reference spans together with text. No upload,
prompt, tool action or reference expansion is replayed. Older previews that lack
this field cannot edit a rich record; the qualified reader must be restored to
continue, and retained history/text bytes remain preserved.

## Qualification and remaining work

Source type/build, supplier hashes, browser graph and notices pass. The 45-file
cohort passes **272/272**, zero failures/skips/cancellations, prepared QtTest,
two workers and unchanged deadlines. Five independent contract cases cover public
hashes, real authored filesystem discovery/exclusions/refresh, private cold
reference/CAS/uncertainty records, late candidate revocation and a controlled Host
maintenance/abort lease. The controlled lease is component evidence, not a live
provider claim.

Actual original-GUI Chromium/public SDK/HTTP evidence covers folder drill-down
and breadcrumbs, a quoted file chip and a folder-with-spaces chip, reload, a fresh
Host/origin, identical metadata, zero implicit uploads/inference, inspector and
browser/foreign denial, then one explicit prompt with ordinary mentions and one
actual filesystem read of independently authored bytes. The received provider
request contains the unchanged guidance and exact user text. The synthetic
provider does not establish semantic task completion or owner live-model parity.

Retained preparation failures are fixture assertions: the existing missing-session
error says “Conversation not found”; the original breadcrumb label is “Folder
navigation”; a controlled Host fixture initially omitted its jobs seat; and
provider text must be read from its actual string/text-block representation rather
than comparing JSON-escaped quotes or assuming a string-only carrier. No guard,
original layout or deadline is weakened.

Session references,
file-chip click previews/right-sidebar resources, native rich-editor parity,
complete command/skill discovery, the remaining Harness migration/privacy/public
packaging gates and other platforms stay open. Existing DSH workflows remain
available; this increment does not complete the Augmentor Harness goal.

## Installed MX qualification — October 12

Runtime **debe8040c7a02ea958c9d5aabbf07cacff757a89** is selected **and running**
in private MX release **20261012-002708-3571d021**, product 0.2.13, artifact
**1b08c0220f3e5760e905f60430bca530645878aaaeb7412d7e1c149813da853a**.
Later qualification edits change documentation only.

Source and fresh ordinary bundled Node **24.19.0** each pass **272/272 across
45 files**, zero failures/skips/cancellations, prepared QtTest, two workers and
unchanged deadlines. All **502 compiled files** match the ordinary assembly.
The preceding installed draft release's **19,160 dependency files / 131 npm
instances**, six native executables, bundled Node and **96 browser notices** match
byte-for-byte. The **726 licence files** add three file-reference records and
update only GUI source provenance among preceding records; all original licence
bodies remain unchanged. Four public runtime and three GUI supplier selections
are verified against the pinned source and marked as described above.

Normal immutable guarded stage/activation finishes before stable Host launch.
The selected runtime entry and bundled Node are verified before stable Native
launch. Both running roots match selection; Native is online/model-ready/idle,
and all **21,821 installed inventory entries** pass after GUI verification.
No selected release is patched.

Actual installed acceptance types an unsent fixture into the original composer,
selects the original `@file` completion row for an existing authored demo file,
and reloads. The atomic chip, exact clipboard text, reference fields and revisions
restore unchanged. The dirty draft vetoes guarded shutdown before and after
reload. Original Ctrl+A/Backspace clears only that fixture, leaving an empty
legacy-compatible record and zero dirty drafts, lookups, operator requests,
uploads, turns and compactions. Of the prior private draft/attachment files,
only that owned draft metadata changes; no object or receipt is added and all
old attachment bytes remain preserved. Context Insights finishes its retained
reads and stays open at the normal 513×715 viewport for owner feedback. No owner
model request, content read tool or prompt admission is made during acceptance.

All **eleven histories and queue identities** remain preserved, with zero new
conversations, admissions, provider requests or tool actions. Of **243 preceding
saved files**, **233** are byte-identical; four original journals retain their
exact prior prefixes with only two saved-title/session_info, two session/close
and two session/load appends, plus six corresponding counter/index derivatives.
Private profile settings and production selection/model router remain unchanged,
as do model/speech/GPU/context/concurrency/precision and CPU ASR/VAD placement.

This qualifies path completion and reference draft continuity in the private MX
preview, separately from the synthetic SDK execution evidence above. Session
references, click previews/right-sidebar resources, native rich-editor parity,
complete migration, public packaging/privacy and other platforms remain open.
