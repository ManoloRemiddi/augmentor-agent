<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

[Stored Pi account sign-out](#stored-pi-account-sign-out--october-14) adds the original MIT DSH confirmation dialog and separate OAuth credential management. This source candidate is not installed in the owner review build; sign-in remains open.

[Installed MX Models qualification](#ordinary-and-installed-mx-qualification--october-13): runtime **340327d6a554094d9ce9d54dcdd0810c08e5b245**, release **20261013-002217-5b1307b9**, product **0.2.13**, artifact **91c9df4354d38dca589be0a231b0c6dd2e4b9559af5c7c923eff0268eedced05**, selected and running. Source and ordinary each pass **334/334** across 65 files, plus five notice/workspace cases. Guarded immutable adoption, actual installed GUI acceptance and all **23,880** entries pass, preserving all twelve histories/queues and owner profile/model/router state. Full migration/live/OAuth/virtual/advanced/privacy/public distribution/platform gates remain open; earlier source-only selection statements below are historical checkpoints.

Current discovery implementation: **340327d6a554094d9ce9d54dcdd0810c08e5b245**. Strict check/build and the exact 65-file MX cohort pass **334/334**, with five separate notice/workspace cases. Ordinary and installed qualification remain open.

Historical initial-forms implementation: **efc0dd564dd2ae2b68c86f50ad83fa53a8eea4a0**. Fresh strict check/build and the exact 64-file MX cohort pass **323/323**, with five separate notice/workspace cases. This is source-only qualification; ordinary and installed acceptance remain open.

# Original DSH Models settings on Pi

The Harness Models section now reuses the original DSH provider rows, editors,
custom-provider card, model-list/row/input controls, confirmation modal and CSS.
The existing conversation model chooser and reasoning control keep their owners.
This is a source candidate; the selected MX preview remains shortcut
runtime **95e0fb240bb000653ff5b122ac737b59c05ee2b8**, release
**20261012-222001-6b609cae**, product **0.2.13**. These forms are not installed yet.

Seventeen files were initially copied byte for byte from public MIT DSH
[d743267388641bc76f17c45ce8b4c231aed1d32c](https://github.com/deepseek-ai/deepseek-harness/tree/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/client/ui-settings-models).
Their public Git blob identities and SHA-256 records were verified. The
[GUI source manifest](../apps/harness/vendor/dsh/SOURCE.json) now contains **580**
files; all previous 563 records stay identical. Original MIT copyright and
license text remain in source and compiled notices. No supplier UI/CSS was modified in that initial checkpoint. The discovery
follow-up below marks three UI/type/locale files for scoped coverage and truthful
Pi default hints; original layout, CSS and selection behavior stay unchanged. The separate Apache-2.0 dsh-context selection remains **108** files.
The surrounding Pi transport/storage adapters retain Augmentor's authored license.

## Private profile and lifecycle

Only operator credentials can call the six `models.settings*` and
`models.credential*` methods. Conversation inspection cannot read provider
profiles, credential metadata or these revisions, and cannot mutate, discover or
refresh them. The page requires the advertised `modelSettings` capability and a
current operator epoch. Revocation/closure clears its descriptor; late responses
cannot restore it. Unconfirmed writes retire editing authority. An explicit fresh
read is required before another edit; no write is replayed automatically.

The original namespace/form contract is seated on private Pi `agent/models.json`.
Curated provider fields map `displayName` to `name` and `baseURL` to `baseUrl`.
The descriptor excludes API keys, authorization/other headers, shell/environment
expressions, compatibility options, costs and unknown fields. Stored provider
fields outside the form are preserved. Model rows carry opaque identities bound
to the provider, row and exact profile revision; editing or reordering preserves
hidden metadata. Forged, reused, foreign and stale identities are refused.
Optional visible fields cleared in the form are removed deliberately.

A per-Host numeric revision advances on changed configuration bytes, including
external edits. A stale form refuses before writing. The Host serializes accepted
edits; the profile fingerprint is checked again after validation and immediately
before persistence. This is not an operating-system lock against arbitrary external
writers. Close/reopen a card after external changes; use **Refresh model settings**
to apply a manually changed profile. Other open clients are checked at save time.
No background model-profile invalidation feed is added in this slice.

A bounded, credential-blind temporary **ModelRuntime** validates the entire
candidate with public Pi 1.1.0 APIs and in-memory credentials. It creates no
AgentSession, reads no owner auth file, runs no tools and does not refresh a
network catalog. Profiles are limited to 4 MiB, 128 configured providers, 512
models per provider and 4,096 configured model rows overall; mutations are
limited to 64 operations and 512 KiB. New/editable endpoints require HTTPS or
loopback HTTP, without URL credentials, queries or fragments. Existing endpoint
fields failing these rules stay out of descriptors and remain untouched unless
explicitly replaced. Unsupported hidden settings require the private Pi profile.

Typed keys are write-only literals in the provider's Pi profile. Literal `!` and
`$` characters are escaped using Pi's supported configuration syntax. Leaving
that input blank preserves the key. The conventional DSH credential reference
maps to one unambiguous provider; it is not persisted as an environment-variable
reference. Command/environment key expressions and active OAuth accounts cannot
be replaced through this input. Removing a provider removes its profile and any
key inside that profile; stored Pi account credentials are retained. The original
confirmation's adapter copy states this distinction.

Changing providers requires chats, jobs, compactions, improvement, MCP management
and runtime maintenance to be idle. A loaded selected model cannot be removed,
and its current thinking level must remain supported. Changed effective models
are applied through **the existing AgentSession.setModel**. It records its normal
model-change boundary without switching provider/model IDs, creating another
conversation owner or submitting inference. Unchanged model definitions do not
append a new boundary. A persistence/application failure is reported as
unconfirmed; the Host blocks new work and automatic queue/goal dispatch until an
explicit refresh reconciles runtime configuration. It does not silently roll
back a stored profile or retry an unknown outcome. Explicit application/refresh
uses Pi's supported availability/auth checks with network catalog refresh off;
those checks may resolve configured authentication, including account refresh.
Cold opening and installed-catalog reads do not do so.

## Discovery and remaining configuration work

The current endpoint implementation and its source qualification are recorded in
[the discovery follow-up](#endpoint-discovery-source--october-13). Installed-catalog
reads stay local. OpenAI Chat Completions/Responses and Anthropic endpoint listings
now use the original bounded parser and the original candidate picker.

OAuth sign-in/out dialogs, virtual/extension-provider editing, advanced hidden
profile controls, proactive cross-client invalidation and common Native/Browser
provider-management parity remain open. The complete-file `models.configure`,
guided setup and manual reload now share the session reconciliation described in
[the lifecycle follow-up](#model-configuration-lifecycle--october-13).
This does not qualify the full P0 model-setup
requirement, live providers, complete P0/P1 migration or DSH removal. Further OS
implementation awaits owner MX feedback. Keep DSH for unqualified workflows.

## Source qualification — October 12

The focused original Models/storage and existing Settings checks pass **9/9**.
They use the actual Pi SDK, isolated HTTP owner and two browser tabs in one
Chromium instance, with a deterministic provider. The browser test exercises the
copied provider/card/row forms, minimal editing, stale-peer refusal and explicit
read recovery, creation/key storage, endpoint-discovery refusal, reload, delete
confirmation and restricted-inspector rejection. A 64K capacity edit becomes
64,000 tokens according to DSH's original decimal capacity parser. It appends
exactly one model-change boundary in the same native history. Prior native bytes,
selection, ordinary profile values, parent display history and the one seed
request are preserved; no subsequent inference is sent.

The final browser case also corrupts only its disposable model profile, confirms
that runtime refresh refuses without echoing the invalid value, verifies new
work is blocked before queue admission, then restores it and explicitly refreshes.
It preserves the same native ancestry and request count. Storage tests cover
hidden-secret exclusion, nonexecution of a command-key marker, opaque-row
preservation, literal credential resolution through public SDK auth, bounded and
invalid edits, busy/external changes, lost replies and late scope revocation.

Failed preparation/test attempts remain separate evidence: an SDK assertion used
`auth.apiKey` instead of `auth.auth.apiKey`; test selectors found mounted hidden
supplier drafts; a CDP Ctrl+A event did not perform native select-all; a capacity
assertion ran before the confirmed Apply closed; and a new limit reducer needed
an explicit TypeScript accumulator type. The first full-cohort attempt ran after
failed prechecks and overlapped a rebuild, producing a missing spreadsheet chunk.
That run is discarded. Final qualification requires successful strict check/build
followed by the unchanged exact 64-file MX cohort, Node **24.19.0**, two workers,
matching QtTest and the original deadlines. No assertion, timeout or concurrency
limit was weakened. Source, ordinary artifact, selected/running and manual owner
acceptance remain separate evidence.

The final strict check/build succeeds. The unchanged **64-file** MX cohort passes
**323/323**, zero failures, cancellations or skips, with Node 24.19.0, two workers
and matching QtTest. The five separate notice/workspace Python cases also pass.
All previous regression cases remain in the cohort. Ordinary artifact assembly,
ordinary qualification, guarded immutable installation and manual installed owner
acceptance remain required before these Models forms are selected. The current
selected shortcut release was read back unchanged; no owner runtime was restarted
or profile/model/speech/GPU/context/concurrency/precision setting changed.

Current process readback: the selected Host **PID 429069** still runs from the
selected immutable root. The previously qualified Native **PID 429553** is now
absent, and no Native process matches that root. Its reason for exit was not
determined; no restart was performed. This is not a new Native-window acceptance
claim. The previous installed/manual shortcut qualification remains dated evidence.

## Endpoint discovery source — October 13

The original **Fetch available models** action now opens the original candidate
picker against the Pi operator owner. Fetching and choosing candidates changes
only the open draft; **Apply** is the separate profile mutation. An existing
model's tuned values win over an endpoint listing. The interface preserves the
original checkbox defaults, toggles, dialog/focus, keyboard and layout/CSS.

Three public MIT runtime files are selected at the same DSH ref in
[`dsh-model-discovery`](../packages/runtime/vendor/dsh-model-discovery/SOURCE.json):
the original API-key validator and coded error helpers are verbatim; the
endpoint/body/parser module is marked for local pure dependencies/types, Pi-owned
catalog lookup, injected request lifetime, omitted DSH attribution, refused
redirects and reported page coverage. Original and adapted hashes and the exact
MIT text are retained and checked during build. No DSH service, telemetry module,
registry refresh or additional AgentSession is mounted. No npm/native dependency
is added. Explicit listings send no DSH product-attribution header.

The MIT GUI stays at **580 files**. Of the seventeen initially copied Models
files, fourteen stay verbatim; three now carry marked MIT adaptations:
`operations.ts` carries optional coverage, `ModelListEditor.tsx` binds it to its
own fetched candidates and uses translated model-default hints, and `locales.ts`
adds English/Chinese page/omitted-ID copy. This avoids another mounted form
changing a dialog's coverage message. DSH's numeric fallback hints are not used
as Pi limits: Pi defaults vary by model/route. All other 577 GUI records and the
108-file Apache-2.0 dsh-context selection stay identical to the preceding source
checkpoint. Browser dependency, PDF/Office/spreadsheet/HTML and shortcut records
remain separate and preserved.

A provider-only automatic read uses the current public Pi snapshot. Known native
catalog providers also retain DSH's installed-catalog behavior for explicit fetch:
that catalog is returned without contacting a draft endpoint or resolving its
key. Custom endpoint discovery supports **openai-completions**, **openai-responses**
and **anthropic-messages**. The original path recipe preserves deployment prefixes:
OpenAI uses `{base}/models`; Anthropic normalizes one trailing `/v1` and uses
`{root}/v1/models?limit=1000`, with its API-version and x-api-key headers. Standard
`data` arrays and enriched `models` alias maps use the original parser and
advertised capacity fields. Unknown capacities are not invented. Other APIs keep
installed-catalog/manual entry rather than guessing an incompatible endpoint.

At most **two** listings run per Host, with a **12-second** admission/auth/fetch/body
signal and the original **4 MiB** actual-response limit. Declared and streaming
oversize bodies refuse. Redirects are blocked. One response/page is read; a
provider `has_more` marker is shown in that exact picker, and malformed/duplicate
IDs omitted by the adapter are identified there. Candidate lists are bounded at
4,096 entries; adopting still uses the existing 512-model profile limit. Reply
bodies, credentials and internal errors never enter a refusal diagnostic. Fetch
failure, timeout, cancellation or a changed profile returns a refusal; nothing is
saved or retried. Endpoint HTTP is outside the Host's state-changing serial queue,
so the operator can read settings and use cancellation while a listing waits.

Stored authentication is used only for an applied, unchanged same-origin profile.
A draft targeting another origin needs an explicit one-shot key; it receives no
old deployment headers. A typed key overrides the stored key through supported
Pi auth without reading, refreshing or replacing a stored credential. Same-origin
literal deployment headers remain available, including header-only relays. Their
literal dollar/exclamation escapes follow Pi's configuration syntax.
Environment-backed keys/headers resolve only on explicit same-origin fetch through
public Pi auth; their inputs remain read-only. Missing/unresolvable authentication
refuses. Shell-command values are not executed for listing. Stored OAuth metadata,
including expired accounts that the availability snapshot does not recognize,
keeps the form key read-only and refuses implicit account refresh. One-shot API
requests do not log in, log out or mutate account credentials. OAuth UI and
command-authenticated discovery remain explicit gaps.

HTTP disconnect propagates cancellation to the exact request; page refresh,
closure and operator revocation abort the frontend transport. Host shutdown and
accepted profile writes abort current listings. Active counts are exposed for
maintenance. Late/revoked replies cannot publish candidates. Inspection tokens
cannot call these profile/discovery operations.

Strict source check/build and the exact **65-file** Node **24.19.0** MX cohort pass
**334/334**, zero failures/skips/cancellations, with two workers, matching QtTest
and unchanged deadlines. Five notice/workspace cases pass separately. New tests
use actual loopback HTTP and the public SDK for paths, headers, alias/capacity
parsing, partial coverage, literal/environment keys, header-only routes, expired
OAuth, redirects, non-JSON/auth/declared/streaming failures, two-request capacity,
caller revocation, stale profiles and the real twelve-second deadline.

Actual two-tab Chromium/SDK/HTTP qualification extends the existing Models case:
the original picker stages one newly discovered model without modifying the
profile until Apply; old values stay intact. One existing native model boundary,
prior native bytes, provider/model selection, display history, ordinary settings
and the single seed request remain preserved, with **zero subsequent inference**.
A separately admitted stalled GET does not block operator reads, and actual HTTP
abort releases its slot and closes its server request. Disposable broken-profile
blocking and explicit repair still pass. These are synthetic source proofs, not
live provider or physical/installed owner acceptance.

Initial failed checks remain distinct: the aggregate DSH error export required
its local coded base alias; public discovery types needed named exports for
TypeScript declarations; a picker selector guessed the display name instead of
its original visible ID; and the test deselected an already-default-picked new
model. Corrected tests retain actual pointer/checkbox/Apply actions and readiness.
Coverage was subsequently seated on each picker and default hints aligned with Pi;
the full cohort reran. No check, assertion, deadline or concurrency was weakened.

Ordinary production assembly/qualification, immutable MX adoption, installed
manual acceptance, live endpoints, OAuth/virtual/advanced/shared provider controls
and all remaining P0/P1/privacy/public distribution/platform gates remain open.
The selected MX release and running Host remain the preceding shortcut build;
the previously qualified Native PID was absent at the preceding readback. This
source turn performs no installed update, restart, owner prompt or model/speech/
GPU/context/concurrency/precision change.

## Ordinary and installed MX qualification — October 13

The locked production dependency stage is fresh and separate from the selected
release. The ordinary artifact uses runtime source
**340327d6a554094d9ce9d54dcdd0810c08e5b245**, with documentation/source snapshot
**9aba945a63023931729ae03af6fd84febb807bb5**. Its actual bundled Node **24.19.0**
and exact **65-file** MX cohort pass **334/334**, zero failures/skips/cancellations,
with matching QtTest **6.8.2.1**, two workers and unchanged deadlines. Five
notice/workspace Python cases pass separately. No source check or fixture result
is relabelled as ordinary evidence.

Assembly contains **657 compiled files**, **20,801 production dependency files**,
**151 npm instances**, **783 licence files**, **nine native/Wasm executables** and
**127 browser notice records for 126 supplier name/version pairs**. All inherited
production paths/bytes, Node/native binaries and engine/PDF/Office payloads and
notices are preserved. Existing spreadsheet/HTML/shortcut and Apache dsh-context
records are identical. The Models selection stays 580 GUI files, with its marked
coverage/default-hint adaptations and three separately noticed runtime helpers.
No npm/native dependency is added. Post-test notices/reports remain byte-exact.

The stable updater stages a new immutable candidate and activates it only after
an idle owner audit and guarded Host shutdown. The initial baseline read found a
stale Native socket refusing connections. The known prior Native PID was absent,
no preview Native process existed and no listener owned that endpoint. The audit
therefore records Native as already stopped without unlinking a selected artifact
or interrupting production windows. A separate fresh comparator is saved; the
preceding shortcut/HTML comparators and proofs remain intact.

The selected/running private MX release is **20261013-002217-5b1307b9**, product
**0.2.13**, artifact SHA-256
**91c9df4354d38dca589be0a231b0c6dd2e4b9559af5c7c923eff0268eedced05**.
The stable launcher's full inventory validation precedes sequential Host/Native
startup. Host **PID 762282** uses the selected Node executable and exact selected
runtime entry; Native **PID 764227** uses the matching selected root/PYTHONPATH and
reports online/model-ready/idle. All **23,880** inventoried entries match before
and after GUI use. Both prior and new immutable releases remain available.

Actual installed manual browser acceptance uses the selected Host/Node/assets in
a disposable, independently authored profile. One tool-free deterministic SDK
seed precedes UI use. The copied Settings/Models provider form applies one
non-secret display-name change. The original fetch action contacts the synthetic
loopback endpoint, opens the original picker, shows its own one-page notice and
uses the original checkbox defaults/toggles. Fetch and candidate adoption leave
the saved model catalog unchanged until the separate **Apply**. That second
explicit write saves the discovered ID/name/context/output metadata. A full
reload visibly restores the provider name and both model rows.

The disposable fixture retains exact prior native bytes, display history,
provider/model selection, selected-model capacity, ordinary profile values and
synthetic API key, with **zero subsequent inference** after its one seed. Manual
acceptance does not type or replace a credential. The two GUI writes affect only
the disposable model profile. The fixture tab is closed; the producer's exec handle
is terminal with code 143 and both producer and fixture Host are absent. Its
synthetic state/proofs are retained; this is not a graceful-exit claim. Source/
ordinary tests for other creation/deletion/stale/credential/timeout/cancellation
paths remain distinct from these specific manual actions.

The owner profile is inspected without any configuration write or endpoint fetch:
all eleven configured models are exposed through the original editor, with the
selected Qwen route still showing **262,144** context tokens, **8,192** output
tokens, and text/image inputs. The editor is cancelled. Original Insights is left
open, with **eleven** non-archived metadata entries, **seven** eligible newest
contexts, **eight** cards and **zero** failed/partial reads or usage gaps. These
are existing retained records, not newly generated model activity.

After owner UI use, all **twelve** preceding histories and queue-item identities,
draft/attachment bytes, backend profile values/revision, production selection and
model-router executable/arguments remain preserved. Of **247** preceding saved
files, **243** are identical; one observation journal keeps its exact prefix and
adds one close plus one load, with three related counter/index derivatives. No
new conversation/placeholder or saved original is added/removed. The running
router, Qwen/Breeze GPU placement, context/concurrency/precision and CPU ASR/VAD
path are unchanged. Canonical main's 38 pre-existing edits remain preserved.

This private installed checkpoint qualifies the stated original Forms/discovery
scope on MX. Live endpoint/account/provider qualification, OAuth/command/virtual/
advanced configuration, shared provider-control parity, legacy whole-file
configuration lifecycle reconciliation and full P0/P1 migration remain open.
Other OS implementation awaits owner MX feedback. DSH remains available; no
public binary, complete migration, global privacy or physical voice/desktop
acceptance is claimed.


## Model configuration lifecycle — October 13

Complete-file `models.configure`, checked guided `setup.save`, manual
`models.reload` and the original form's explicit refresh now reconcile loaded
conversations through the same existing public Pi `AgentSession.setModel` path.
The previous configure/reload paths refreshed the catalog while loaded owners
could keep old model definitions, including context limits. Current writes and
reloads preserve provider/model identity and the existing execution owner;
changed definitions append Pi's ordinary model boundary. Configuration changes
start no conversation request. A later explicit request uses the refreshed
model. Whole-file changes do not rewrite conversation selection to setup's new
default connection. An unchanged profile is a no-op only when every loaded owner
also matches the current SDK catalog; explicit Apply still reconciles a model
re-registered by an extension without a JSON change.

Whole-file configuration retains SDK fields, headers, compatibility data and
model overrides, and is not reduced to the minimal editor's curated fields or
catalog limits. A 513-model authored catalog qualifies this distinction. Standard
providers validate through a temporary, credential-blind public `ModelRuntime`
with refresh/network catalog access disabled. Its validation never runs command
keys or reads the owner's credential store. Known extension/native providers
retain their actual registered defaults, custom API and authentication handlers:
their context-dependent validation occurs in the existing runtime after storage,
without registering handlers in a shadow validator. The public registered-ID list
is used only to distinguish that context. Unrelated edits preserve loaded virtual
models and their routers. This does not qualify complete virtual-provider editing
or all custom provider types.

The idle guard now also applies to manual reload, including active chats,
background jobs, compaction, prompt improvement and MCP management/reload. A
configuration write or explicit reload cancels in-flight listings. Provider
refresh errors, aborted refreshes and a profile changing during reconciliation
leave application unconfirmed and block new work, automatic queue/goal dispatch
and discovery. There is no automatic rollback or replay after possible storage
or SDK effects. Repair the complete profile or explicitly refresh to confirm it.
A successful refresh attests the exact file fingerprint used by that refresh;
persistence alone cannot authorize discovery's stored credentials. Complete
valid configuration can repair malformed JSON. Standard loaded-model removal
and unsupported thinking are refused before storage; context-dependent
registered-provider failures are checked during actual runtime reconciliation.
Public auth/availability checks during explicit application may resolve configured
expressions or refresh accounts; cold UI/catalog reads remain distinct.

The focused checks exercise the actual isolated Host/SDK with independently
authored loopback providers: complete-file changes, two SDK model boundaries,
next-request capacity, original-prefix preservation, one session-start before
restart, no automatic inference, malformed reload/explicit repair, unrelated
virtual routes, actual registered-provider overrides, and guided connection
check/save/discovery with its existing consumed-token protection. Separate fault
injection covers aborts, provider errors and concurrent file replacement. These
are synthetic source checks, not owner/provider/installed acceptance. The first
four lifecycle tests tried to read Pi's unpersisted empty transcript; each now
performs one explicitly counted authored exchange before its baseline. The first
full 341-case run caught a discovery test reading its remote-close log before the
fixture's close callback; it now waits for that exact event with the unchanged
deadline. An intermediate complete 341-case run passes; final qualification adds
the registered-provider regression separately.

Supplier GUI/CSS, the 580 MIT GUI records, 108 Apache-2.0 Context records, runtime
supplier helpers, dependency pins, native/Office/PDF payloads and notices are
unchanged. Shared runtime code applies across platforms; this increment qualifies
MX first. Source, ordinary assembly and installed scope are recorded separately.
The selected preview remains runtime 340327d / release 20261013-002217-5b1307b9
until guarded immutable adoption; this source work changes no owner model profile,
production model/router, GPU/speech setting or canonical main edit. Live provider,
OAuth, advanced GUI, common Native/Browser model management, full P0/P1 migration,
privacy/public distribution and physical/platform gates remain open. Further OS
implementation awaits owner MX feedback; DSH remains available.


### Lifecycle source qualification

Final strict check/build and the exact 66-file MX cohort pass **342/342**, zero failures/skips/cancellations, with Node **24.19.0**, two workers, unchanged deadlines and the prepared matching PySide6/QtTest **6.8.2.1** interpreter. The initial focused checks pass **16/16**; the final two-owner registration regression passes after reproducing the missing boundary on the prior artifact. Five notice/workspace Python cases pass. All preceding cohort files stay included. The eight added cases comprise two complete-configuration unit checks and six Host lifecycle/registered-provider/fault checks. Ordinary and installed adoption remain separate from this source result.


The registered-provider follow-up includes two existing SDK owners. Pi's public extension API refreshes the registering conversation itself, so the first single-owner expectation of an extra boundary was incorrect. The final regression explicitly seeds a second owner before a gated re-registration: identical-file Apply must leave the registering owner's native bytes unchanged and append one ordinary model boundary to the stale peer, preserving both original prefixes and all six authored requests. It fails against the preceding ordinary artifact **7f44288f5522ad3bc41f818f68b0964496e37623** at that exact missing-peer assertion and passes against the corrected source. Final broad requalification follows this correction; prior source/ordinary 342-case evidence describes its earlier checkpoint.


After the shared-registration correction, strict check/build and the complete 66-file source cohort again pass **342/342**, zero failures/skips/cancellations, using the same Node/QtTest/two-worker/deadline contract. This is the final source baseline for ordinary reassembly; the prior ordinary artifact is retained as the failing regression comparator.


## Ordinary and installed lifecycle qualification — October 13

Corrected runtime **79ee4ff4c3b7e205833f20f936843ce37886b1cd** is selected and running in private MX
**20261013-013249-f43fa0d0**, product **0.2.13**, artifact
**ac0a3fad21de2808a9cb37a7ec7748668234991335aea08b436fb37810144663**. Final source and ordinary bundled Node **24.19.0** each pass
**342/342 across 66 files**, zero failures/skips/cancellations, two workers,
unchanged deadlines and matching prepared PySide6/QtTest **6.8.2.1**. Five
notice/workspace Python cases pass in each scope. The ordinary artifact contains
**657 compiled files, 20,801 production dependency files, 151 npm instances,
nine native/Wasm executables and 783 licence files**, with **127 browser notice
records / 126 versions**. No dependency or native package is added. MIT GUI
selection stays **580** files; Apache-2.0 dsh-context stays **108**. All supplier
records/CSS and inherited production dependency/Node/native bytes remain unchanged.

The initial 7f44288 ordinary artifact passes its original 342 cases but fails the
new shared-registration assertion. It remains the explicit regression comparator.
The corrected second assembly reuses the exact freshly staged dependency tree.
Its initial seed omitted **82 Photon and 23 QuickJS** notice files; before staging,
all 105 are restored and the complete 783-file notice inventory is verified byte
for byte against the preceding release. First immutable adoption
**20261013-012223-1e5fd4a4** passes runtime checks, but its later full path comparison
exposes three missing generated distribution records: exclusions, overrides and
prerequisites. That immutable release is preserved. The records are restored in
the separate ordinary tree and normal staging/activation creates the final release
above; no selected release is patched. Always preserve the entire notice set and
these generated records when reusing a production dependency seed. The final
inventory inherits every preceding path except the qualified generated Excel
entry chunk replacement (YIFN2U4S → GI2BPDBV); its parser-worker/provenance records
and original UI remain preserved.

Six lifecycle cases run using the first immutable candidate's bundled Node and
actual staged Host in isolated authored profiles, including the two SDK owners
and the unchanged-file registration regression. The fault-injected Host module
also matches the staged compiled bytes. Final immutable **dist, Node,
node_modules and all licence bodies** are verified identical to that tested
candidate; only the three restored distribution records distinguish its relevant
packaging closure. This is synthetic immutable SDK/Host qualification, not an
owner model/configuration test or broad live-provider acceptance.

After each guarded idle close, activation finishes before stable Host startup;
its exact bundled Node and entry are checked before the stable Native launcher.
Final Host **958987** and Native **963077** are online/model-ready/idle at the
same selected root. The complete **23,880-entry** immutable inventory verifies
after actual browser use. The original Insights view is reopened at the owner's
normal viewport, with **11 nonarchived metadata entries, seven newest contexts,
eight cards and zero failed/partial/usage-gap reads**, and left open. Read-only
Models description is confirmed and still contains **eleven** owner models.
No owner model prompt, endpoint listing, credential entry or configuration write
is performed. Existing original form/discovery manual acceptance remains its
separate earlier evidence; this increment changes runtime lifecycle only.

Both the intermediate baseline and original pre-adoption baseline verify. All
**twelve** histories and queue-item identities, draft/attachment bytes, profile
values/revision, explicit **models.json/auth.json** presence and bytes, production
selection and model-router executable/arguments remain preserved. Of **247**
preceding saved files, **243** are identical; one observation journal retains its
exact prefix and adds one close plus one load, with three related index/counter
derivatives. No conversation/placeholder or saved original is added/removed. Qwen
and Breeze placement, context/concurrency/precision and CPU ASR/VAD remain
unchanged. Canonical main retains its **38** pre-existing changed paths.

This qualifies the stated Linux configuration/reload/shared-registration
lifecycle. Complete OAuth/virtual/advanced GUI and Native/Browser model management,
full P0/P1 migration, real provider/physical/privacy/public distribution and
other-platform gates remain open. DSH remains available; further OS implementation
awaits owner MX feedback. No public binary is published.


### CI publication checkpoint and platform gaps

At documentation head **336d3afe5c351577c1373e9b62437f3ff1ae1687** (runtime
79ee4ff unchanged), Linux contracts, Mac contracts, source-boundary, Home,
shared Qt candidate and the reported desktop/component checks pass. CI is not
fully green. Windows contracts, x64 native runtime and command-job workflows
stop during GUI build: the spreadsheet overlay's Fortune Sheet import cannot
find Immer's default export. [Exact Windows build failure](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38324030995/job/115058463967).
Mac 14/26 runtime packaging reaches notice collection and refuses the unreviewed
platform packages **@deepseek-ai/libreoffice-kit-darwin-arm64@0.1.5 (MPL-2.0)**
and **@img/sharp-libvips-darwin-arm64@1.3.4 (LGPL-3.0-or-later)**.
[Mac 14 packaging failure](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38324031299/job/115058700904),
[Mac 26 packaging failure](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38324031299/job/115058700913).
The runtime/contract tests reaching those failures do not qualify the platform
artifacts. Debian and ARM workflow completion was still pending in the inspected
snapshot. These are explicit unresolved build/licensing gates; no broad license
allowlist, platform artifact adoption or further OS implementation is performed.
The verified private MX selection and local 342-case source/ordinary evidence
remain as recorded above. Further platform implementation awaits owner feedback.

## Stored Pi account sign-out — October 14

The original Models footer now lists stored OAuth provider routes and opens
DSH's original sign-out confirmation. The two newly selected public files,
`SignOutDialog.tsx` and `SignInDialog.module.css`, match the exact Git blobs at
[the pinned MIT baseline](https://github.com/deepseek-ai/deepseek-harness/tree/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/client/ui-settings-account).
The public licence was rechecked against the retained licence. The source
manifest grows from 580 to **582** entries; the previous records stay identical.
Existing Models card CSS is reused. The browser graph allows only these two
account presentation files; other DSH account controllers, sign-in transport,
backend and analytics remain excluded. No new npm dependency is introduced.

`models.settingsDescribe.accounts` contains only provider route IDs and a
registered-provider boolean. “OAuth stored” reports local credential metadata,
not account identity, token validity or a successful provider connection. Account
identity, tokens, API keys and SDK error bodies are not returned. API-key
credentials are not listed. An unregistered provider stays visible with an
unavailable control; register it in Pi before managing its account.

The separate operator-only `models.accountLogout` removes the OAuth credential
currently stored for the selected provider through supported
**ModelRuntime.logout**. Removing a provider profile still retains account
credentials. Sign-out retains provider settings, profile API keys and environment
credentials, so other configured authentication can remain available. It is a
local operation and does not revoke access at the remote provider.

Admission requires an applied model configuration, current profile revision,
stored OAuth metadata and registered provider. Active work must settle and
queued prompts/goals must be paused. The Host serial owner stays held through
actual SDK settlement, with a ten-second abort signal; it never retries or
releases ownership merely because cancellation was requested. After SDK success,
loaded AgentSessions keep their owners and reconcile effective model definitions.
The profile fingerprint and fresh credential metadata must agree before new work
is enabled. A storage, synchronization or reconciliation failure is unconfirmed:
new work stays blocked until explicit model refresh. A committed deletion is not
silently rolled back. Raw SDK errors and credentials are not propagated.

The browser scope checks operator epoch/capability and descriptor shape. A lost,
invalid or revoked write reply retires its editor/account authority and clears the
list. No automatic write replay occurs. An explicit fresh read is required before
another attempt, and fresh stored metadata prevents a second deletion of an
already removed OAuth credential. Cancel in the original confirmation submits no
mutation. Provider route identity is the scope of this action; the GUI does not
claim to identify an individual account or detect a same-type credential replaced
by another Pi process between metadata checks and the SDK's serialized deletion.

Focused strict check/build and **22/22 across four files** pass: the new public-
SDK/account failure tests, existing model settings/configuration tests and original
Models Chromium workflow. The authored provider/store qualifies actual deletion
followed by SDK synchronization failure, stale/type/unregistered/busy/queue/goal
refusals, held settlement, lost reply and late role revocation. The real isolated
Host/browser uses synthetic valid-future Anthropic-shaped credentials, never a
personal login: original pointer Cancel/confirm, unavailable orphan, inspector
refusal, cold reload, unrelated credential retention, unchanged parent history/
model selection and no new inference pass. This is fixture evidence, not a live
provider or account-service acceptance claim. Wider source/ordinary qualification
is pending at this implementation checkpoint.

OAuth sign-in and interactive auth/callback cancellation, remote revocation,
unregistered-account removal, proactive cross-client invalidation, common Native/
Browser controls and broader model/provider/live/migration acceptance remain open.
The owner review release/selected installation, drafts, production Qwen/speech
settings and independent Office build are not replaced by this source change.
