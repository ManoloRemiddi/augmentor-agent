<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

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
provider-management parity remain open. The older full-file `models.configure`/
guided setup path is separate from this minimal editor and requires further
lifecycle reconciliation. This does not qualify the full P0 model-setup
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
