<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Original DSH Models settings on Pi

The Harness Models section now reuses the original DSH provider rows, editors,
custom-provider card, model-list/row/input controls, confirmation modal and CSS.
The existing conversation model chooser and reasoning control keep their owners.
This is a source candidate; the selected MX preview remains shortcut
runtime **95e0fb240bb000653ff5b122ac737b59c05ee2b8**, release
**20261012-222001-6b609cae**, product **0.2.13**. These forms are not installed yet.

Seventeen files are copied byte for byte from public MIT DSH
[d743267388641bc76f17c45ce8b4c231aed1d32c](https://github.com/deepseek-ai/deepseek-harness/tree/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/client/ui-settings-models).
Their public Git blob identities and SHA-256 records were verified. The
[GUI source manifest](../apps/harness/vendor/dsh/SOURCE.json) now contains **580**
files; all previous 563 records stay identical. Original MIT copyright and
license text remain in source and compiled notices. No supplier UI/CSS was
modified. The separate Apache-2.0 dsh-context selection remains **108** files.
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

The supplier model editor automatically reads installed defaults with a
provider-only request. This uses the current public SDK snapshot without network
or credential resolution. Its explicit endpoint-fetch action currently returns:
“Endpoint discovery is not connected yet. Enter models manually; no endpoint was
contacted.” It never substitutes installed defaults for endpoint discovery.

Endpoint discovery, OAuth sign-in/out dialogs, virtual/extension-provider editing,
advanced hidden profile controls, proactive cross-client invalidation and common
Native/Browser provider-management parity remain open. The older full-file
`models.configure`/guided setup path is separate from this minimal editor and
requires further lifecycle reconciliation. This slice does not qualify the full
P0 model-setup requirement, live providers, complete P0/P1 migration or DSH removal.
Further OS implementation still awaits owner MX feedback. Keep DSH available for
unqualified workflows.

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
