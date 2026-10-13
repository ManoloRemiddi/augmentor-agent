<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

[Original HTML previews](HARNESS-HTML-PREVIEWS.md) now supplies rendered HTML separately from Office conversion. Office/PDF engine and native supplier bytes/notices remain preserved; ordinary/installed qualification and full migration/public distribution gates stay distinct.

[Linux packaging source review](#linux-packaging-source-review--october-13) now
exports the exact Office engine notices and build sources through production
staging. Private payload identity passes; public source/rebuild approval remains
open. Existing installed and unselected runtime artifacts are unchanged.

[Installed original spreadsheet previews](HARNESS-SPREADSHEET-PREVIEWS.md#ordinary-and-installed-mx-qualification--october-12): runtime 64d52917684307cb2a29c75e908209c83d4f06de, private MX 20261012-190657-be20be18, product 0.2.13, artifact 231dd41c550624399cea35a3c6e2d7244d938fb751c83d80373643f2b290e676, selected and running. Source and ordinary Node 24.19.0 each pass 301/301 across 58 files plus five notice/workspace cases. Actual installed original grid/warnings/sheets/readonly/scroll/reload/tab acceptance preserves native history with zero subsequent inference. Eleven prior histories, drafts/attachments, profile values/revision and model-router arguments are preserved; one additional empty Linux placeholder has no history or request. All 23,790 installed entries pass. MIT GUI is 527 files; Apache dsh-context remains 108. Full migration/live/privacy/public distribution/platform gates remain open; preceding selections below are historical checkpoints.

# Original Harness Office previews

## Original document registration — October 12

The original public DSH Office registration selects `.doc`, `.docx`, `.ppt` and
`.pptx` in the existing file sidebar. Original loading, Retry, missing-font
toolbar/details, retained per-tab results, PDF child slot, zoom and CSS remain
in use. The existing original PDF renderer presents converted bytes; no new UI
layout or agent owner is introduced. Client cache generations, pending readers,
authorization-before-reuse, reset disposal and tab lifetimes remain original.

The public MIT GUI selection adds **eleven files**, bringing it to **507** at
**d743267388641bc76f17c45ce8b4c231aed1d32c**. Ten bodies are verbatim, including
both CSS files and the document hook contract. One marked locale adaptation
names the unavailable local service without directing users to a DSH Host.
The preceding 496 supplier bodies/hashes remain unchanged. dsh-context remains
**108 files**, Apache-2.0, with its existing notices and modifications.

Seven selected public MIT runtime files retain the original Office provider,
bounded queue, output validator, errors, identity and branded primitives under
`packages/runtime/vendor/dsh-office`. Their source/adapted hashes and change
notices are recorded. NodeNext imports, a Pi lifecycle/authorized-byte-reader
seat and explicit limits replace Cordis, schema defaults and Typert decorators.
Original converter slots, deferred source admission, content-addressed reuse,
reader cancellation, classified errors and private scratch cleanup remain.
Queue/provider busy state exposes actual teardown for maintenance. The engine's
font disk cache is explicitly disabled. These helpers create no AgentSession,
tool call, model request, attachment receipt or saved conversation event.

## Authority, transport and lifetimes

Only an authenticated Harness operator in an eligible Desktop conversation can
read the renderer generation or request conversion. Browser-only, archived and
delegated conversations, and read-only inspectors, retain no Office authority.
Each source uses the same regular-file, no-follow, current-version and complete
byte reader as ordinary previews. A byte-access check and stat precede queue
admission and cached reuse; deferred full reads revalidate the expected version.
Workspace authority is checked again after conversion. Existing absolute read
namespace behavior is preserved rather than inventing a new filesystem grant.

The provider admits **one CPU conversion**, four waiting metadata-only jobs and
sixteen readers, with **20 MiB** source/reservation/output limits, eight retained
PDFs, **64 MiB** retained output and sixty-four source aliases. Speculative
background conversion is refused. The engine retains its **60-second** deadline,
192 DPI, ten-thousand archive-entry and 250 MiB declared uncompressed limits,
plus the original explicit font budgets. This changes no Qwen/Breeze/GPU,
context/concurrency/precision or ASR/VAD settings.

`GET /api/preview/office-generation` returns the provider lifetime.
`GET /api/preview/office` sends a four-byte big-endian metadata length, bounded
UTF-8 JSON metadata, then complete PDF bytes. Metadata is limited to **256 KiB**;
large font lists are never silently omitted or forced into HTTP headers. Current
source identity, rendering generation and missing-font declarations accompany
the bytes. The client validates the envelope, authority/epoch and exact length.
No-store responses, authenticated local transport and existing main-page/local
PDF worker security policies remain in use.

One reader cannot cancel another reader's shared conversion. Final-reader
cancellation retires shared work; engine capacity remains owned until actual
worker and scratch cleanup settle. `host.describe.activeOfficePreviews` reports
this retained lifetime, and `host.prepareShutdown` refuses it even after an HTTP
reader has left. Host close cancels and awaits the original provider. Tab close,
session/role/Host epoch changes and adapter disposal retire client viewing and
cache faces. Document bytes/PDFs are transient memory/private scratch, not native
history, drafts or model context.

## Engine and licence scope

Pinned **@deepseek-ai/libreoffice-kit 0.1.5** matches the public DSH lock. Its
Linux **0.1.5 Wasm** package uses LibreOffice **26.8.0.3**, source
**bce0998afefdbc355585ca324285661a2170ba77**, build identity
**81c24980c5de51d11e2e50d48ea2bd98f9830a97d35df551f4aed8b6ff5bfe2c**.
The package manifest, engine payload hashes, source/rebuild recipe and licence
paths are recorded in `release/office-engine-linux-wasm.json`. The local system
LibreOffice is neither invoked nor used as a fallback.

The [kit](https://github.com/deepseek-ai/dsh-libreoffice-kit) and LibreOffice
engine are **MPL-2.0**, with their separate bundled third-party terms, MIT Harness
portions and Apache notices. They are not relabelled MIT. The exact engine's
nested LICENSE/NOTICE/MIT texts are retained with hash-bound catalogue entries;
the collector rejects changed bytes, outside paths and links. MPL permission
is accepted only for these reviewed exact package versions, not globally.

The first ordinary staging attempt correctly rejects five missing npm licence
texts. Saxes' pinned source LICENSE and Koffi's same-version parent MIT notice
are recovered. Brotli, DFA and Fontkit omit root LICENSE files in their recorded
publisher commits too. Their explicit MIT package/README declarations and
author attribution are preserved separately from clearly labelled canonical
SPDX MIT terms; no copyright year or restored upstream LICENSE is invented.
Brotli's original Google Apache-2.0 decoder headers and standard Apache terms
are retained separately. **Public copyright/notice sufficiency for these three
declarations remains unqualified.** Ordinary notice collection is not that gate.

Public MPL engine/wrapper source, third-party notice/rebuild sufficiency and any
native dependency qualification remain separate from private MX testing, as do
the existing Sharp/libvips and Liberation-font gates. No public binary release
or all-MIT product licence claim follows from this source change.

## Linux packaging source review — October 13

Implementation **647dd1a9d60ea53c716929481a3c28e19aa80615** adds
`scripts/office_engine.py` to production staging and the Debian native inventory.
The reviewed record now pins all **49 engine-package files**, including **39
engine recipe/patch/source files**, and all **41 entry-package files**. It checks
the locked npm integrity, installed package identity, complete file inventory,
engine manifest/source/build identity and every hash. Missing, changed, linked
or extra content is rejected. No supplier payload, dependency version, Office
runtime, GUI, model or speech setting changes.

Staging exports five original licence/notice bodies, the original engine manifest,
the 39 source files and the reviewed build record into `licenses/office-engine`.
The component inventory records **46 source/notice references** and explicitly
marks public redistribution unqualified. Exported copies are verified against
the reviewed package inputs; rehashing a local BUILD.json or relabelling the
component cannot authorize changed bytes. This corrects the earlier broad
`sourcesShipped` field: `engineBuildSourcesShipped` covers the shipped engine
recipes, while the entry's preferred-source gate remains separately open.

The actual preceding Debian exporter rejects the real staged `soffice.wasm` as
an unreviewed filename. The new exporter first verifies its full source/notice
bundle, then deliberately refuses public packaging with an explicit corresponding
source/rebuild error. It does not whitelist Wasm globally or produce a public
package from a private-preview identity. Changing approval labels alone cannot
close the gate. Unknown native files remain rejected by the existing policy.

The public source review is recorded in
`release/office-engine-public-source-review.json`. At the October 13 inspection,
the only public branch is master, commit **b19bb73c74ed893b8a5d1716d32df32a113ed31b**,
whose entry package identifies itself as **0.1.3**. Both pinned npm **0.1.5**
metadata records omit gitHead. Of the shipped 39 engine source files, **34 match**
this public checkout, **two differ** (`engine/ui-resource-policy.mjs` and
`docs/ui-resources.md`), and **three generated build/source files** have no same
path there. The archive and differing files have exact recorded hashes. The npm
entry package contains compiled JavaScript/declarations, without preferred
TypeScript source. A version difference alone does not prove a compiled-code
difference, and this snapshot comparison does not prove no other source exists;
it does not establish corresponding source for the exact 0.1.5 entry either.

The supplier describes the source/build materials carried with its engines in
[the public repository](https://github.com/deepseek-ai/dsh-libreoffice-kit).
[Mozilla's MPL guidance](https://www.mozilla.org/en-US/MPL/2.0/FAQ/)
explains informing recipients where to obtain covered source. The exported engine
recipes and licence texts establish identity; the exact entry source, engine
rebuild and full linked third-party obligations still need qualification.

Validation on MX/Linux: **nine new Office packaging cases**, four existing Codex
packaging cases, eight QuickJS packaging cases and three nested-notice cases pass.
Fresh `stage-production.py` completes with **151 npm instances**; its four actual
staged WebSocket security cases pass. All **eight native dependency files** match
the preceding ordinary navigation candidate before Node is added. Private-source
boundary and version checks pass. These **28 focused cases** and fresh staging
are packaging evidence, not another full GUI cohort or a new installed artifact.

The selected appearance runtime **97897cf** and unselected navigation runtime
**dfcdfb9 / 20261013-190500-3bf1e21f** remain as previously qualified. No activation,
shutdown, public binary release or DSH retirement occurs. Public Debian packaging,
Sharp/libvips/font and declaration-notice obligations, owner/plugin/live acceptance
and the full migration remain open. Further OS work awaits owner MX feedback.

## Qualification and remaining work

Actual pinned Linux Wasm converts independently authored two-page OOXML, reports
the unavailable authored font and preserves source bytes. Cached requests still
reauthorize current byte access/stat; changed and removed sources cannot return
old PDFs. Controlled original-queue checks verify metadata-only waiting,
admission bounds, shared reader independence, caller-owned bytes and cancellation
capacity through delayed real cleanup. Forbidden surfaces never obtain a
converter, and maintenance refuses retained conversion teardown.

Public SDK/HTTP/Chromium acceptance selects a real @file chip, displays both
converted PDF pages, opens/closes the original font warning, chooses original
100% zoom, reloads changed bytes, reports a malformed document, recovers through
Retry and closes the original narrow fullscreen tab. One deterministic tool-free
SDK seed creates real native history; subsequent preview actions preserve that
history, native bytes and the provider request log. Inspector/Browser denial,
zero remaining HTTP/file/conversion work and no external browser requests pass.
The test documents contain no private or copied upstream fixture material.

Source check/build and **300/300 across 57 files** pass with Node **24.19.0**,
prepared QtTest, two workers and unchanged fixture deadlines. The five focused
Office cases pass alongside existing file/PDF checks. Three nested-notice and
two workspace-packaging cases pass separately. The wider recipe is the
[55-file PDF cohort](HARNESS-PDF-PREVIEWS.md#installed-mx-qualification--october-12)
plus `tests/harness-office-preview.test.mjs` and
`tests/harness-office-chromium.test.mjs`.

The first build exposes a missing selected original document hook contract;
that verbatim file is added. The first focused run exposes an incomplete Host
fixture and a synchronous input-validation assertion; both are corrected without
changing product behavior or weakening the assertions. Final source tests have
zero failures/skips/cancellations. The ordinary and installed qualifications
below supersede the preceding PDF selection. Runtime implementation and its
subsequent documentation-only qualification publication remain distinct.

## Installed MX qualification — October 12

Runtime **d0642d58f3edfbf9211e61ef60ffbe636141e301** is selected and running as
private MX **20261012-084425-89e511a9**, product **0.2.13**, artifact SHA-256
**731357a72f03ac54deb57973b9d51b3c140f9f5ada6c29f0c0220d153165e983**.
Fresh ordinary bundled Node **24.19.0** repeats **300/300 across 57 files**, zero
failures/skips/cancellations, with prepared QtTest, two workers and unchanged
deadlines. Three nested-notice and two workspace-packaging cases pass in the
ordinary tree too. The failed first staging attempt remains a failed checkpoint;
a distinct fresh dependency stage passes after the reviewed notice additions.

The ordinary assembly has **629 compiled files**, **20,801 dependency files**,
**151 npm instances**, **780 licence files**, **nine native/Wasm executables**
and **100 browser supplier notice records**. All **133 inherited npm instances**,
their paths/bytes, and existing Node/native bytes are preserved. The eighteen
new instances supply the kit, Linux Wasm engine and parsing/font/FFI support.
The three added executable bodies are the pinned LibreOffice Wasm and the two
Koffi glibc/musl carriers; Linux rendering does not invoke the Windows native
pipe/FFI path. Their exact hashes/notices and the unchanged inherited native
records are verified separately. Browser npm supplier records remain identical
to the qualified PDF artifact. A post-assembly npm audit agrees byte-for-byte
with the staged report and licence texts. Public MPL/native, three MIT declaration
notice-sufficiency, Sharp/libvips and font source/rebuild gates remain open.

Guarded adoption stages a separate immutable artifact with the explicit
candidate Node, closes the idle Native through maintenance, completes one Host
shutdown, activates the candidate and launches the stable Host. Exact selected
Host executable/root are verified before stable Native startup. All **23,764
installed inventory entries**, stable-launcher status and exact Native root pass
before and after the GUI acceptance; no selected release is patched.

The installed Office GUI acceptance uses a separate disposable profile with the
actual selected Host and Node. One deterministic tool-free SDK seed creates real
native history. The original @file completion/chip opens an independently authored
two-page DOCX; actual GUI inspection verifies both pages, original missing-font
warning/details, 100% zoom and **Read the file again** against changed bytes.
Native originals, history and provider request log remain identical during
these actions, with **zero subsequent provider requests**, file reads, Office
work and Harness requests. The temporary browser tab is closed; the verified
fixture producer and Host finish terminally. The saved local screenshot shows
the actual installed original viewer and font warning. Source/ordinary malformed
file/Retry and narrow-fullscreen evidence remain separate from this manual check.

An initial manual idle probe used HTTP and counted its own request. The supported
native IPC probe verifies zero outstanding requests without changing the
expectation. Initial preservation reads before GUI connection correctly observed
only close appends; opening the original owner GUI supplies its explicit
load/title receipt. No process is restarted or expectation relaxed to satisfy
these observations.

The owner GUI reads both retained Qwen request bodies in the original Context
trend/browser/file-activity widgets and leaves **Context Insights** open. No
owner prompt/model/tool, Office file read, draft edit or preference write occurs.
All **eleven histories and queue identities** remain intact, with no new owner
conversations/admissions. Of **243** saved files, **233** are identical and four
journals retain exact old prefixes with two title/session_info, two close and
two load appends, plus six associated index/counter changes. Draft/attachment
object sets and bytes, profile values **and revision**, Qwen/Breeze/GPU/context/
concurrency/precision and ASR/VAD settings, production selection and router are
preserved. Native is online/model-ready; no active owner turn, compaction,
upload, Harness request, dirty draft, file lookup/preview or Office work remains.

One read-only pre-promotion capture inadvertently reused the PDF baseline filename.
Its completed before/after-GUI proof files remain retained. Office uses a separate
snapshot of the selected PDF state; an additional comparison against the retained
earlier prompt-wrapping baseline verifies unchanged histories/queues/drafts/
attachments/profile/production and all old original prefixes. This is not a
reconstruction or rerun of the overwritten PDF comparison snapshot.

Real DOC/PPT/PPTX samples, complex OOXML/layout/font cases, password handling and
full converter format coverage remain separate evidence gaps. The original
spreadsheet grid, rendered HTML, native open/download, sidebar shortcuts and
every remaining Harness/P0/P1 migration gate stay open. DSH remains available.
Windows, macOS and other Linux implementation stay deferred for owner MX feedback;
this shared Host/browser change adds no OS adapter.
