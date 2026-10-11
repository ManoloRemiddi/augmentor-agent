<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

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
Tool settlements invalidate the index, retaining supplier stale-while-refresh
behaviour. The adapter keeps at most eight search instances, discarding an old
workspace instance when its cwd changes. Queries are bounded to 4,096 UTF-16
units and exclude control characters. Abort/revocation/session changes cannot
insert stale candidates. HTTP cancellation reaches the search caller; search
disposal cancels its bounded background index. No file contents are prefetched.

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

Ordinary/installed qualification follows separately. Session references,
file-chip click previews/right-sidebar resources, native rich-editor parity,
complete command/skill discovery, the remaining Harness migration/privacy/public
packaging gates and other platforms stay open. Existing DSH workflows remain
available; this increment does not complete the Augmentor Harness goal.
