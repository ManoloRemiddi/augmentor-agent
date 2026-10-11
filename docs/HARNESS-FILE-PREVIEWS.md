<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Original Harness file previews

The copied DSH file chip now opens the original right sidebar. Chat Markdown
file links use the same opener, including the original line navigation. The
supplier sidebar, docking planners, title strip, collapse/fullscreen controls,
text reader, syntax viewer, Markdown/frontmatter, image viewer and CSS remain
in use. This adds no new AgentSession and sends no preview contents to a model.

## Use and scope

In a Desktop conversation, select a file from the original `@` menu, then click
its chip. The original reader provides line paging, wrap, automatic refresh,
manual reload and viewer selection. Its sidebar keeps per-session tab metadata,
supports split panes and becomes fullscreen at narrow widths. Reloading the same
browser origin restores layout metadata and reads the actual file again; file
bytes and rendered bodies are not persisted in browser storage.

Text, code, Markdown and supported images are connected. HTML is source text.
PDF, Office, spreadsheets, rendered HTML, native open/download, terminal,
explorer and sidebar keyboard command bindings remain unqualified or unbound.
The original Start tab has no invented entries for these missing integrations.
This is an MX-first increment, not full GUI/Harness or other-platform acceptance.

## Read contract and lifetime

`workspaceFiles.stat`, `workspaceFiles.read` and `workspaceFiles.readBytes`
return the supplier-style `{ok,value}` / `{ok:false,error}` envelope. They require
operator authority and a current, non-archived, non-delegated Desktop session.
Read-only inspection credentials and browser-only sessions cannot read local
preview files. Initial and completed reads check the current workspace and
maintenance state. No owner is loaded for these IO operations.

Reads preserve Desktop's existing read namespace: relative paths resolve from
the selected cwd, and explicit absolute/outside-cwd paths remain readable when
the OS allows it. Path discovery remains cwd-contained as described in
[references](HARNESS-FILE-REFERENCES.md). A regular file is opened read-only;
leaf symlinks, directories and special files are rejected. File identity, size,
mtime and ctime produce a version; pre/post checks refuse replacement or change.
No write, upload receipt, prompt admission or tool execution is created.

The original streaming page cutter returns up to 200 lines and 256 KiB of UTF-8
page text, preserving blank lines, Unicode and EOF meaning. Invalid UTF-8,
page-local NUL content and oversized pages fail explicitly. Paged text does not
impose a whole-file size cap; walking a distant line reads its prefix. Byte RPCs
are bounded to 256 KiB. Complete images use the authenticated same-origin
`GET /api/preview/bytes` route, capped at 20 MiB, with exact offset/EOF/byte-count
and version metadata. Typed size/read errors retain their actual limits.

Tab lifetimes cancel reads and release text/image caches. Session, role or Host
epoch changes discard body bytes and abort outstanding resources; late results
cannot cross that authority boundary. Original metadata sources refresh every
three seconds while a file tab is held. Collapsing retains its tabs; closing
ends the occurrence. In-flight reads veto guarded maintenance through
`activeFilePreviews`; HTTP reception also uses the existing operator lease.

Markdown local images resolve from the Markdown file's directory through the
same authenticated read API, with at most 20 destinations and a combined 20 MiB
retained-byte budget. Their actual file resources participate in invalidation.
Object URLs are revoked on cleanup. Remote and protocol-relative image sources
are inert, including on failure; no external fallback is used. Original markup
and styling remain unchanged.

## Public sources and licensing

GUI selection: **482 files** from public MIT DSH
**d743267388641bc76f17c45ce8b4c231aed1d32c**. This adds 75 records. Of the preceding
407 bodies, 406 remain identical; the Markdown primitive receives a marked,
optional remote-image suppression flag whose default preserves upstream
behaviour. The new Markdown preview body receives a marked optional authenticated
image vocabulary. All selected CSS is verbatim. SOURCE.json preserves upstream
and selected hashes; the build validates them.

The separately selected MIT runtime page cutter has its own LICENSE,
SOURCE.json and SOURCE.md, copied into the compiled/runtime distribution.
No supplier Cordis/backend/resource service is mounted. The original persistence
validator adds **zod 4.4.3 (MIT)**, pinned to the public baseline's lock. Both
browser and production notice inventories must include it. Other dependency,
native-binary and licence claims require the fresh artifact comparison below.

The retained **dsh-context 0.68.1** selection remains unchanged: Apache 2.0,
Copyright 2025 bowenliang123, preserved licence/attribution and marked Pi
adaptations. Its Context, `/context`, Insights and preferences evidence remains
in [the original GUI guide](DSH-GUI-ON-PI.md). Augmentor's authored-code licence
does not relabel either supplier licence.

## Qualification

Source checks, ordinary packaging and installed MX evidence are recorded
separately. Fixtures use independently authored files/messages, actual public Pi
SDK/HTTP and Chromium. They do not represent private history, a live model call,
physical other-platform acceptance or support for the unbound viewers above.

Source checks/build, source hashes, browser graph and notices pass. The 47-file
cohort passes **277/277**, with zero failures/skips/cancellations, prepared QtTest,
two workers and unchanged deadlines. Four IO/Host cases cover real file bytes,
absolute namespace, original page semantics, invalid ranges/binary/UTF-8,
cancellation, maintenance leases and late workspace revocation. The original
Chromium fixture covers chat-link line navigation, rich-chip draft preservation,
wrap/page/reload, Markdown/frontmatter/local images, cold layout restoration,
narrow fullscreen, split/close controls, inspection/browser denial and typed
size errors. One explicit deterministic loopback provider request creates its
chat link; subsequent preview/reload/dock actions preserve history and request
bytes and execute no tools. This is not a live-provider or installed-owner call.

The GUI bundle has **98 npm notice records**: it newly uses the already locked
ISC yaml 2.9.0 for original frontmatter and newly pinned MIT zod 4.4.3. Other
browser records retain their preceding versions/notices. The copied supplier
manifest contains a duplicate identical office-to-pdf key; the build warning is
retained with the original manifest. No Office renderer/service is registered.

The broader [migration gates](AUGMENTOR-HARNESS-MIGRATION.md) remain open.
DSH stays available while these replacements are tested.
