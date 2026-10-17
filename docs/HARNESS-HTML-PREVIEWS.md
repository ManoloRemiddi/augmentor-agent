<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

[Original main-document shortcuts](HARNESS-SHORTCUTS.md) adds the registry/reference/recorder separately from this HTML transport. The fixed opaque frame gets no keyboard/Host action bridge; its compiled transport, supplier bodies and isolation remain preserved.

# Original Harness HTML previews

## Original components and control — October 12

The public DSH HTML registration serves `.html` and `.htm` through the original
file/sidebar toolbar, with rendered HTML, Code and Text choices. Its HTML body,
static sanitizer, finite local-asset packer, UTF-8/base64 helpers, relative-reader
contract, locale and CSS remain in use. The original General settings switch
controls interactive previews; its Pi copy describes the available behavior as
**Interactive HTML previews**, without promising unbound preset/diff controls.
Context and Trajectory remain available independently.

The MIT supplier selection adds **fourteen files**, bringing **527 to 541**, at
**d743267388641bc76f17c45ce8b4c231aed1d32c**. Twelve are verbatim. Two carry
prominent modifications: `HtmlBody.tsx` accepts an optional opaque-frame transport
and its existing failure copy; `DeveloperToolsRow.tsx` accepts an optional disabled
gate for unsupported/read-only authority. Original default transport, component
structure, dictionaries and all CSS remain preserved. The previous 527 supplier
records and 108 Apache-2.0 dsh-context files remain unchanged.

The copied `DeveloperToolsPreference` consumes an authored Host configuration
seat. The private `ui-settings` namespace accepts one exact boolean `enabled`
operation at the current global revision, preserving unrelated settings and
committing atomically. The original enabled default is preserved for missing
values. Corrupt values and unconfirmed, missing, stale, revoked or disconnected
client state cannot enable execution. There is no optimistic enablement or
automatic mutation replay; explicit Refresh recovers an uncertain setting.
The Host explicitly advertises `capabilities.htmlPreviewSettings: true`. Older or unsupported Hosts send no preference RPC and leave the control disabled. Capability revocation retires outstanding replies. Restricted inspectors cannot read or change the global preference. This setting
does not change models, permissions, memory, prompts or the agent lifecycle.

## Static and interactive lifetimes

Static mode uses the verbatim DOMPurify preparation, its restrictive first-head
CSP and the original `srcDoc` iframe with an empty sandbox attribute. Scripts,
external resources, forms and nested frames cannot execute. Interactive mode
retains the original finite packer and document bootstrap, including local
classic `.js` scripts and `.css` stylesheets declared by the HTML. It retains
**64 assets**, **4 MiB per asset** and **32 MiB combined package** limits.
Root bytes retain the independent Host **20 MiB** complete-preview cap. Invalid
UTF-8 and rejected packages show the original failure text.

Related reads remain under the root HTML's session and file authority. URL
query/fragment removal, decoding, relative-path validation and failure-resource
membership use the original helper. A stat applies the existing four-MiB asset
limit before complete-byte IO; its exact version accompanies the authorized
HTTP read. The old default 256-KiB byte-RPC page never silently truncates a script.
Missing/oversize asset paths retain their original resource subscriptions so
restoring them can invalidate and reload the original document.

The UI-only metadata source now retains an ordinary read lease for each
subscriber, matching the copied ResourceGroup contract. Sources stay stable
while any tab/subscriber owns them; last release aborts reads, and old cleanup
cannot remove a newer source at the same address. The original three-second
polling, dependency invalidation, pause/reload and tab/session/role/Host-epoch
lifetimes remain in use. Changing assets, root bytes, mode or authority retires
the previous browsing context and its scripts. No AgentSession, model/tool
request, upload receipt or native history entry is created by viewing.

## Opaque frame transport and policy

The application keeps its script policy; main-page inline/eval permission is not
added. `frame-src 'self'` admits only local frame navigation and `font-src` admits
data fonts needed by the static document. The original interactive Blob transport
is replaced in the Pi seat by the fixed, compiled `/dsh-html-frame.html` asset.
The build embeds the authored trusted loader, validates its template and records
both hashes; no opaque-origin request to a protected external script is needed.

The frame keeps `sandbox="allow-scripts"`, with the equivalent HTTP CSP sandbox,
and no same-origin privilege. Its scoped CSP permits inline/Blob scripts and
styles plus data/Blob media/fonts; connections, workers, nested frames, forms
and base changes are denied. Referrers and DNS prefetch are disabled. Camera,
microphone, geolocation, display capture, payments, USB/serial and clipboard
features are denied. WebRTC peer constructors are sealed off because their ICE
transport is outside ordinary connect-src enforcement. Browser sandbox origin
separation also prevents access to a fresh nested frame's constructors.

Exactly one document transfer follows a ready message from that iframe's actual
WindowProxy, opaque origin and current random channel. The fixed loader accepts
one transfer from its actual parent/app origin. No bearer, storage, Host callback,
filesystem request or model/action bridge enters the frame. Repeated ready
messages cannot obtain another payload. A five-second bootstrap failure shows
the existing HTML failure text and retires the listener; original reload can
recover. Application CORP protection remains unchanged.

This is isolation within the browser, not a claim of CPU/process containment.
The original packer does not traverse module imports, CSS dependencies or runtime
fetches. External network sources, nested documents and additional device/worker
capabilities are unavailable in this preview; opening an authorized external
application remains separate. Broader samples, browser/accessibility acceptance
and complete privacy qualification remain open.

## Dependencies and provenance

Build-only **DOMPurify 3.4.16** matches the public DSH lock and tarball integrity.
Its offered licence expression is **MPL-2.0 OR Apache-2.0**; the reviewed exact
browser version selects **Apache-2.0**. Its complete original LICENSE and Cure53/
contributors attribution remain in compiled notices and legal comments. The
collector rejects an unreviewed version/expression or changed attribution. No
production package or native executable is added. Source and selected binary,
prior Office/PDF/font terms and public distribution gates remain distinct.

## Focused qualification and retained failures

Independently authored SDK/HTTP/Chromium cases use real static and interactive
frames, a 300-KiB local script, Blob CSS, actual pointer clicks, changed dependency
and root bytes, mode retirement, malformed UTF-8, a paused real frame bootstrap,
oversize asset failure/recovery and narrow fullscreen/tab close. Parent/storage/
WebRTC/nested-realm/worker denial and repeated-payload checks run in the document;
a separate controlled HTTP origin observes zero probe requests. Viewing preserves
the seeded native history and provider log. Only the fixture's explicit preference
writes affect its global revision; unrelated settings remain preserved.

The first expanded 60-file cohort passes 305/306; its existing interaction simulator correctly rejects two unsupported preference RPCs. Explicit Host capability negotiation corrects the connection without ignoring console errors or loosening that test.

Initial test failures are recorded: expression quoting and closing-button selectors;
the browser isolating sandbox frames into separate targets; a protected external
bootstrap script being refused by CORP; and Worker construction returning a shell
before asynchronous execution denial. A first profile comparison removed only the
final copy's explicit false setting. Per-target Network blocking did not pause a
new isolated target; the real debugger-paused bootstrap now exercises the timeout.
Corrections preserve the scope, original UI and existing two-worker/deadline recipe.
The trusted loader is embedded, application CORP is retained, and the Worker check
observes real execution/error settlement. Failed attempts are not passing evidence.

Source, fresh ordinary packaging and installed/manual results are recorded
separately below when complete. The full [migration requirements](AUGMENTOR-HARNESS-MIGRATION.md)
remain binding. DSH stays available and further OS implementation awaits MX feedback.

## Qualified source checkpoint — October 12

Fresh check/build and the exact [60-file MX cohort](../tests/cohorts/harness-mx.json)
pass **307/307**, with zero failures/skips/cancellations, Node **24.19.0**, matching
QtTest **6.8.2.1**, two workers and unchanged deadlines. Seven focused HTML/settings/
existing-interaction cases pass after explicit capability negotiation. Three
nested-notice and two workspace-packaging cases also pass. The cohort preserves
original Context/Insights/sidebar/Fleet/prompt wrapping, trajectory, draft/file/
PDF/Office/spreadsheet, native and Pi lifecycle coverage. Direct contract fixtures
remain source evidence; ordinary bundled and installed/manual qualification are
separate gates. The currently selected/running spreadsheet release is unchanged
at this source checkpoint.

Run from source or a separate ordinary assembly with the matching test Python:

```sh
AUGMENTOR_PYTHON=/path/to/prepared-test-environment/bin/python node --input-type=module <<'JS'
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
const {files,concurrency,nodeVersion}=JSON.parse(readFileSync('tests/cohorts/harness-mx.json','utf8'));
if(process.versions.node!==nodeVersion)throw Error('Unqualified Node');
const result=spawnSync(process.execPath,['--test','--test-concurrency='+concurrency,...files],{stdio:'inherit'});
process.exit(result.status??1);
JS
```

Preserve the virtual-environment executable path instead of resolving its Python
symlink. Installed releases deliberately exclude tests; source drivers select
ordinary runtime bytes through `AUGMENTOR_PI_TEST_ROOT`.

## Ordinary and installed MX qualification — October 12

Runtime **e4c8663b2a5e57a676837e0892505fbe8b237af7** is selected and running
in private MX **20261012-210709-6242b91f**, product **0.2.13**, artifact SHA-256
**c02dc8cfd35bf77b9d0741412a76c1bfdc4a06d6a9989bb9124237f14dd30335**.
A fresh ordinary bundled Node **24.19.0** repeats **307/307 across 60 files**,
zero failures/skips/cancellations, matching QtTest **6.8.2.1**, two workers and
unchanged deadlines. Three nested-notice and two workspace-packaging cases pass
in that tree. Its post-assembly production npm report and all 96 collected notice
files match staging byte-for-byte; compiled files match source after tests.

The assembly has **637 compiled files**, **20,801 production dependency files**,
**151 npm instances**, **781 licence files**, **nine native/Wasm executables** and
**127 browser notice records for 126 supplier name/version pairs**. Inherited
production package paths/bytes, Node/native bodies, Office/PDF assets/notices,
spreadsheet patches/worker provenance and all prior supplier records remain
preserved. The fourteen HTML/preference supplier additions bring the MIT GUI to
541; Apache-2.0 dsh-context stays 108. HTML adds no production npm/native payload.

A new comparator captures twelve current owner histories/queue identities and
247 existing saved original/observation files, independently of older spreadsheet
comparators. The updater stages a separate immutable candidate. Prior Native and
Host complete guarded idle/draft-free shutdown before activation; stable launch
verifies the selected Host executable/root before Native startup. All **23,813
installed inventory entries**, matching Native root and online/model-ready state
pass before and after actual GUI use. No selected release is patched.

A disposable profile executes the actual installed Host, Node and browser assets,
using the public independently authored HTML fixture from source because installed
releases exclude tests. One tool-free deterministic SDK seed precedes viewing.
Actual original @file completion/chip, static sanitization, General switch,
interactive 300-KiB local script/Blob CSS, frame button click, automatic dependency/
root replacement, original Read again, mode retirement and tab close pass. DOM
observations confirm parent/storage/RTC/nested-realm/worker denial and zero repeated
document transfers. The fixture returns to static mode with exactly two explicit
GUI preference writes and preserved unrelated profile values. Its history, native
original bytes and provider log remain identical: **zero subsequent inference**.
Final draft/read/Office/HTTP work is zero; the fixture tab closes and its exact
producer/Host finish terminally. Source/ordinary actual controlled-origin network,
malformed/oversize/bootstrap failure/recovery, narrower authority and fullscreen
checks stay distinct from this installed manual evidence.

The owner's original Insights reads eleven non-archived metadata entries, seven
newest eligible contexts and eight original cards, with zero failed/partial reads
or usage gaps. It is left open. No owner prompt, model/tool action, file preview,
draft edit or preference mutation is submitted. All twelve histories and saved
queue items remain preserved. Of the **247** preceding files, **239** remain
identical; **two** observation journals retain exact original prefixes with **two
close and one load** lifecycle appends, and **six** corresponding counter/index
derivatives update. No new session/placeholder or saved original is added/removed.
Draft/attachment bytes, backend profile values/revision, production selection and
model-router executable/arguments remain identical. Canonical main's 38 existing
changes stay preserved.

This qualifies the private MX HTML slice and retained original dashboard, not
complete Harness migration, CPU/process containment or every document format.
Broader real-world/browser/accessibility/live acceptance, native opening/downloads,
remaining P0/P1 workflows and privacy/public distribution gates remain open,
including prior MPL/native/Sharp/font source/rebuild and MIT-declaration notice
sufficiency. Further OS implementation waits for owner MX feedback; no public
binary release is published and DSH remains available. Subsequent documentation
commits record this proof without changing the selected runtime bytes.
