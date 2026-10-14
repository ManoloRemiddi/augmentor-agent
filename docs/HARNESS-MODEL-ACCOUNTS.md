<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Pi accounts in the original DSH Models page

The source candidate adds supported Pi OAuth sign-in to the original DSH sign-in
and sign-out dialogs. MX Linux remains the first owner-testing target. The current
running review and selected installation are preserved; this source change is not
an installed update. The initial strict check/build and focused **38/38 across
seven files** pass. Full source/ordinary qualification is pending at this checkpoint.

## User workflow and provider scope

Open Settings → Models, choose **Account provider**, then **Sign in**. Finish active
turns, jobs, compaction, prompt improvement and MCP management first; pause queued
prompts and goals. The original dialog runs the selected provider's Pi SDK flow.
It supports provider-method choices, text/password prompts, manual callback codes,
authorization links, device codes and progress. Links open only on an explicit
click or copy; the exact provider URL is retained without DSH theme parameters.
Secret/manual-code inputs use password fields and are cleared when their step ends.
The SDK owns browser callback servers, exchange, credential storage and refresh.

Only currently registered providers with a public OAuth login method appear.
Session-provided extensions follow the existing approved-resource/SDK-session
loading policy; a cold metadata read does not execute extensions to discover more
providers. The current conversation's normal reasoning inspector can load its
existing SDK owner and register those providers. Account status does not imply
provider availability, a particular individual, subscription eligibility or token
validity. Successful sign-in replaces the credential currently stored for that
provider. Profile/environment keys remain and can still take precedence in request
authentication. No conversation/provider/model selection is silently changed.

The separate [stored-account sign-out](HARNESS-MODELS.md#stored-pi-account-sign-out--october-14)
removes only the selected route's stored OAuth credential. It is local sign-out,
not remote revocation. API-key profile forms remain separate.

## Supported SDK and action ownership

The Host calls public **ModelRuntime.login(provider, 'oauth', interaction, options)**.
There is one global account-login action, separate from conversation execution;
it creates no AgentSession or second agent loop. Each chat retains its owner.
Admission verifies the model profile revision/applied bytes, registered provider,
idle work and paused queue/goal state. Profile edits, new work and changes to
shared execution/session ownership are fenced while login is active. Status,
prompt response and cancellation stay responsive outside preparation serialization.

The provider receives `agentName: Augmentor Harness`. A private installation UUID
is generated only if its explicitly requested SDK login asks for `getDeviceId`;
it stays stable in that Pi profile. Existing provider OAuth client registrations
and callback protocols remain SDK-owned.

Prompts have fresh IDs. An answer must match the exact action, provider and current
prompt; a consumed or callback-aborted step cannot be answered again. The public
per-prompt abort signal supports callback/manual-code races without cancelling a
later step. HTTP disconnect/role revocation clears browser interaction data and
prevents late replies from restoring authority. Lost admission/answer/cancel replies
cause exact-receipt reads, never automatic mutation or answer replay. A fresh dialog
does not borrow an older completed receipt to report a new sign-in as successful.

Cancel requests the SDK abort and clears displayed interaction. The action remains
held until its SDK promise settles, including a credential mutation that has
already started and must finish. No stored credential is silently rolled back.
An action has a fifteen-minute overall deadline; expiry requests the same abort.
Closing/unmounting the browser scope retires its reads; a known action can be
inspected again, and no new login is started automatically. Closing the original
active dialog explicitly requests cancellation. Shutdown vetoes an active login;
actual runtime shutdown requests abort and awaits settlement.

After SDK success, the existing loaded AgentSessions reconcile effective models,
the profile fingerprint is rechecked and OAuth credential metadata must be present.
Only then does the receipt report completion. A storage/SDK/synchronization or
reconciliation failure is **unknown**, including cancellation that races a commit.
New work stays blocked until explicit **Refresh model settings** confirms the
current SDK/configuration state. Refresh retains the original uncertain receipt.
Corrupt/unwritable receipt storage requires repair; it is not silently deleted.

## Retention and transport

Private `model-account-logins.json` retains at most 256 metadata-only receipts in
one MiB, with action/provider IDs, state/result, timestamps and cancellation flag.
It never stores prompts, answers, authorization URLs, device/manual codes, tokens,
SDK errors or chat text. Full retention refuses new actions rather than evicting
unknown receipts. On cold startup, admitted unfinished receipts become
`interrupted / unknown`; no callback/link/prompt is restored or login replayed.

The active interaction is transient operator-only RPC data. Text, options, links
and answers are bounded; both server and client reject unsafe URL schemes and
inconsistent prompt/action identities. Public conversation inspectors cannot call
account management or inspect its metadata. No interaction enters chat history,
Trajectory payload retention or model context. The original sign-in popup gets
no Harness action bridge. Stored credentials remain in Pi's existing private
`agent/auth.json`, written through its supported runtime.

RPCs are `models.accountDescribe`, `models.accountStart {provider, revision,
requestId}`, `models.accountStatus {requestId?}`, `models.accountRespond {requestId,
promptId, value}` and `models.accountCancel {requestId}`. `host.describe` advertises
`modelAccountLogin` and `activeModelAccountLogins`. Existing sign-out/refresh
contracts are retained. A profile revision does not identify an individual account
or detect another Pi process replacing a credential of the same type at that route.

## Public source, platform and evidence

The MIT selection grows from 582 to **583 files** at public DSH
[d743267388641bc76f17c45ce8b4c231aed1d32c](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/client/ui-settings-account/src/client/SignInDialog.tsx).
The new sign-in source's exact upstream Git blob was verified; its marked
adaptation adds a transient prompt child, preserves exact provider URLs and
supports non-browser waiting copy. Original layout, CSS and actions remain.
All previous 582 manifest records stay identical. Exactly three account
presentation inputs enter the browser graph; DSH account controllers, transport,
backend and analytics stay excluded. Apache dsh-context and all other notices
remain separate. No new npm dependency is introduced.

Initial focused evidence uses a public authored OAuth provider and real Pi SDK,
FileAuthStorage, Host, original dialogs and actual Chromium pointer/keyboard input.
One chat seed request is followed by six explicit login attempts: manual success,
real loopback-page callback success, prompt cancellation, provider failure,
credential commit followed by refresh failure, and an admitted prompt interrupted
by a SIGKILL/restart. Current/stale prompt and read-only refusals, private receipts,
stable lazy device ID, no replay, unchanged selection/profile/displayed history
and no additional inference qualify. Parent native bytes stay exact through the
auth flows; cold SDK owner loading adds only its existing saved-title annotation,
with the exact prior prefix. The preceding published runtime independently
reproduces that annotation through its reasoning inspector; repeated model reads
add nothing. Cold model/credential status requires explicit reconciliation.

Nine runtime cases cover sequential prompts, committed/cancelled storage,
synchronization failure, callback races, cold metadata, unsafe/bounded input,
receipt failure and lazy identity. Six pure browser-scope cases cover lost writes,
current-step response, wrong action/provider, role revocation and unsafe/inconsistent
descriptors. Existing account/settings/model-configuration and original Models
Chromium tests remain in the 38-case cohort. An added common CI step runs the 21
account/runtime/scope cases on Linux, macOS and Windows; new-head hosted results
are not yet qualified. Shared TypeScript/browser behavior has no new OS adapter;
SDK callback/browser handoff, private storage and installed/physical acceptance
remain separate platform evidence.

Retained preparation failures include the direct-response seed assumption, original
error-dialog title changes, cold provider-picker selection and an overly strict
native whole-file assertion. The first cancelled-store test used Pi's abortable
in-memory store, which prevents a later commit; the irrevocable-write fixture now
holds a started mutation explicitly. An initial baseline used metadata-only model
inspection and produced no append; the actual preceding reasoning-inspector load
reproduces the saved-title annotation. These are bounded qualification corrections,
not claims of an older product regression. No existing test deadline is extended.

Real provider login/callback, account semantics and subscription acceptance,
registered-extension diversity, Native/Browser management parity, physical/cross-OS
rollout, complete migration/privacy/recovery and public distribution remain open.
Office exact-entry-source/actual engine rebuild and native/font notice gates are
not relaxed; the isolated engine compile is independent of account work. Production
Qwen/Breeze GPU placement, context/concurrency/precision and CPU ASR/VAD are preserved.
