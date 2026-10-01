<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Codex ChatGPT accounts: internal implementation and acceptance

Status, October 1: OAuth transactions, protected account persistence and one
shared host login controller are implemented in development source. Desktop and
Browser settings use that controller for account status, login/cancellation,
explicit plan-permission requests and logout. Saved plan profiles now bind one
account, model and fixed OpenAI destination, and queued turn admission renews an
idle worker before dispatch when its credential revision changes. This remains
partial C4 work in the [full C0–C9 plan](CODEX-INTEGRATION-PLAN.md): the separate
Codex-managed account route, eligibility and actual subscription inference remain open.
The shipped host keeps login disabled pending distribution eligibility; neither
RPC nor environment variables can turn that gate on. No real account or provider
token was used in these proofs. Installed apps remain unchanged.

## OAuth transaction

`packages/codex-runtime/src/chatgpt-auth.ts` binds an ephemeral loopback listener,
random state/nonce and PKCE to one attempt. It uses fixed OpenAI discovery and
authorization/token origins, rejects redirects, bounds response bodies and
verifies ID-token signatures/issuer/audience/expiration/nonce using pinned
`jose` 6.2.12. Returning authorization must match the saved subject and issued
client ID. A callback, including errors, must have the expected state and cannot
consume the code twice. Cancellation prevents late credentials from succeeding.

The installation host ID is a private persisted UUID URI. Initial registration
uses `dynamic_agent_client`; subsequent authorization and exchange use the
issued client ID. A provisional issued ID can be retained after an incomplete
first exchange; it is not an active or verified account. The shared host controller
durably owns that provisional record and clears it after verified activation.
Restart reconciles a provisional client already committed as a saved registration.
Explicit plan-permission
requests use supported `prompt=consent`; ordinary login does not force consent.

Granted scopes, rather than callback assertions, determine plan permission.
Identity-only consent cannot authorize inference or an automatic API-key fallback.
Only the internal browser-opening adapter may receive an authorization URL with
an ID-token hint. Do not expose hinted URLs, codes or tokens over surface RPC,
diagnostics, support records or browser storage.

## Protected account lifecycle

`chatgpt-accounts.ts` belongs to one exclusively owned shared host. Its private
index stores stable labels, issuer/subject/client mappings, revisions, status and
opaque OS-store references. Access, refresh and ID tokens remain in the native
credential store; the public listing omits references, tokens, subject and issued
client ID. It reports only account labels/email, state, selection, revision,
verified plan-permission status and the remote-revocation receipt.
Email does not identify a workspace: two registrations with the same email
remain separate. New credentials become active only after verification and a
durable protected-store/index commit.

Near expiry, access serializes renewal and commits a write-ahead `renewing` state
before dispatch. A successful replacement is saved under a new OS-store reference
before replacing the index; retired entries have durable cleanup ownership.
An interrupted or unconfirmed rotation requires new authorization and cannot
replay the old refresh. Its old credentials remain quarantined in protected
storage for reauthorization/logout, without inference access. Terminal invalid
refresh grants clear unusable credentials; explicit infrastructure/client errors
preserve credentials and report recovery without automatic retries.

Logout fences account access before attempting discovered-endpoint revocation,
then retires local credentials while retaining the registration and host ID.
Revocation has at most one retry for network/server failures. The result reports
remote confirmation and local cleanup independently: a locked store or remote
outage cannot be reported as successful credential removal. Cleanup reservations
survive restart. The host must close admission and stop account-owned workers
before invoking logout; this store alone does not stop native Codex processes.

## Shared host and existing setup controls

`chatgpt-login.ts` owns one pending attempt, with a public UUID and opening,
waiting, saving, signed-in, cancelled or failed status. Starting returns before
network discovery or OS browser launch, so cancellation and Close remain usable.
Only the internal OS adapter receives authorization URLs; it launches `xdg-open`
on Linux or `/usr/bin/open` on macOS using an argument vector with ignored child
output and a bounded timeout. Browser-launch failures expose no hinted URL.

The factory in `main.ts` is lazy: account-index recovery and registration writes
happen after the shared IPC host owns its socket. A fresh Desktop call or Browser
bridge connection can read/cancel the same attempt; socket disconnect alone does
not cancel it. `accounts.status`, `accounts.start`, `accounts.cancel`,
`accounts.select` and `accounts.signOut` have explicit, secret-free request
shapes. The Browser bridge maps only these reviewed setup operations.

Verified account activation, selection and logout freeze new connection work and
release idle native workers using the existing native activity/ledger checks.
Active, unresolved or unverified work refuses the mutation. Pending login blocks
maintenance. Host close cancels and drains its attempt. Cancellation during an OS
credential write leaves cleanup ownership but cannot replace the saved account;
cancellation after its durable activation cannot falsely report it as cancelled.

Both existing setup forms show eligibility status, saved accounts, sign-in,
explicit plan consent, cancellation and separate logout confirmations. Closing a
form cancels only the attempt it started, including a late start reply. Closing a
form observing the other surface's attempt leaves that attempt intact. Polling
stops on Close; replacing the native controller cancels its owned attempt.
Logout clears stale successful-login text and preserves an accurate receipt for
the other surface. Default account selection does not rebind saved connections.

## Evidence

```sh
npm run check
npm run build
node --test tests/codex-chatgpt-auth.test.mjs tests/codex-chatgpt-accounts.test.mjs
node --test tests/codex-chatgpt-login.test.mjs
python3 scripts/proof-codex-secretservice.py
```

The focused tests use fresh cryptographic keys, signed synthetic identity tokens,
real loopback HTTP callbacks, a mocked OpenAI transport and a synthetic credential
store. They cover account isolation, returning identity, scope refusal, rotation,
crash-state recovery, unknown outcomes, persistence failures, locked logout and
revocation confirmation. They do not certify real OpenAI sign-in or inference.
The current host/UI checkpoint passes **71** focused OAuth/account/controller
cases, including the actual native Python adapter and Browser native-messaging
bridge through one real IPC server. Controller/worker tests use synthetic grants,
an injected authorization adapter and scripted app-server replies. The underlying
OAuth tests use signed synthetic identities and real loopback callbacks.
The complete Node suite passes **426 of 428** cases with two explicitly opt-in
Docker memory proofs skipped. All **61** Browser tests and **584 of 586** native
tests pass, with two Mac-only skips; TypeScript checking/build and the private
source-boundary check pass. The native/Node suites use the existing isolated
Qt/QtTest environment. These are source/UI contract tests, not live account,
browser-launch, token-funded inference or installed-release acceptance.

The expanded actual Linux Secret Service proof passes in a disposable pinned
Debian container, using a separate D-Bus session/keyring and no network. It verifies
account save/rotation/reopen/logout and cleanup through the real Node/Python OS
store. Renewal and revocation remain synthetic in this proof. The same expanded
script is required by existing Mac build/Desktop/Browser Keychain CI steps;
[CI for `91db7aa`](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36861022280)
passes on macOS 14 and 26, with all three interpreters reporting positive account
save/rotation/restart/logout and cleanup. This preceding CI does not certify the
new host/UI source. For the new source checkpoint
`95229aaf0dfc979b895fb0ef06ed131aaf84c550`,
[Mac CI](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36866967195)
passes on Mac 14/26, including new controller/native setup contracts and all
three real Keychain interpreter proofs on each runner. All six confirm account
save/rotation/restart/logout and final cleanup. The isolated actual Linux store
proof passes again after the new metadata and cancellation changes. The owner's
wallet was untouched; all 30 original changed canonical files match their private
backup bytes. No actual OpenAI sign-in or browser-launch acceptance is claimed.

The public OpenAI discovery endpoint was independently read without credentials:
issuer, authorization/token/JWKS/revocation endpoints and RS256 match the adapter's
constraints. This is metadata compatibility, not completed live authorization.

[Debian CI for the same source](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36861022467)
passes application/Browser/credential checks, production npm notices and the Home
job. Debian packaging still fails its pre-existing unreviewed native Codex
executable gate; installed-package jobs therefore do not run. The green Mac jobs
do not clear native dependency review or qualify an installed Codex product.
[Linux/Home CI for `95229aa`](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36866967360)
has the same result: source-boundary/Home, application/UI/credential checks,
production npm notices and extension packaging pass. The native executable
notice gate still blocks Debian packages and skips installed-package checks.

## Bound connections and worker renewal — October 1

A `chatgpt-plan` profile stores an account ID and model, with the fixed destination
`https://api.openai.com/v1`. It contains neither an API credential reference nor
OAuth tokens. API/local profiles reject account inheritance; explicit conversion
retires the previous API key. Both setup forms restore a saved profile's pinned
account, require a ready account with plan consent, disable API-key controls and
send no credential field in the plan payload. The production eligibility gate
also disables the plan choice; injected test authorities cannot enable production.

Configuration revisions and protected-account credential revisions are separate.
Changing model/account/destination invalidates old chats and connection checks;
rotating a token preserves the profile revision and existing image/tool checks.
Changing the default selected account never redirects a saved profile or chat.
A missing, identity-only, signed-out or quarantined account refuses inference,
without choosing another account or API billing.

Every root turn, including the scheduled queue pump, runs account preflight while
its operation is still queued, before `ledger.dispatch` and `turn/start`. It first
verifies native idleness and a stable activity snapshot, resolves the exact saved
account/profile, and rechecks the binding and activity. Only a changed credential
revision causes renewal. `CodexRpc.renew` retires the owned process, initializes
its replacement and resumes the exact bound thread; it sends no turn. Destination,
model, runtime arguments, workspace and isolated state remain fixed. Captured
child handlers ignore retired output and suppress retirement exit events, while
the existing observer object remains attached. Pending calls/interactions refuse
renewal. Stop/Close cannot resurrect a replacement. Failed renewal retires the
worker and leaves the unsent operation queued/paused for explicit recovery.
Unknown acknowledged or unconfirmed work blocks renewal and cannot be replayed.
Steering continues within the already admitted active turn; it never restarts an
active worker. Further account-specific model/limit and auxiliary funding
acceptance remains required.

New focused evidence comprises nine profile cases, eight host admission/recovery
cases, seven transport renewal cases and an actual pinned Codex renewal proof.
The host peer is independently authored and scripted, uses synthetic grants and
never calls a provider. Its cases cover queued renewal, native child activity,
uncertain refresh, Stop during rotation, default-account isolation, explicit
rebinding, unknown turn outcomes and failed resume with explicit recovery.
The actual Codex 0.159.2 proof uses a disposable loopback Responses provider and
synthetic API bearers: initialize/resume makes no inference request, the second
turn uses the new bearer, and native history preserves both distinct client IDs.
It proves native renewal transport, not live OpenAI subscription inference.
The complete suites pass 453 root cases (451 pass, two opt-in memory proofs
skipped), all 63 Browser cases and 588 native cases (586 pass, two Mac-only
skips). Type/build, 40 focused profile/host/transport/native-renewal cases and
the private-source boundary pass. All 30 original changed canonical files
still match their private backup bytes. Publishing and platform CI source
identity follow below; earlier CI above covers only its stated source.

Reproduce the new contracts after building:

```sh
node --test tests/codex-plan-profiles.test.mjs tests/codex-plan-host.test.mjs
node --test tests/codex-rpc.test.mjs tests/codex-native-renewal.test.mjs
```

## Current account model choices — October 1

`chatgpt-models.ts` reads the selected consented account's catalog using its
protected current bearer at the fixed `GET https://api.openai.com/v1/models`
destination. It does not call Codex's bundled/cached `model/list`, perform
inference, redirect, retry, cache across accounts or choose another funding route.
Responses are bounded to 1 MiB/1,000 records and ten seconds. Only visible model
slugs/display names are returned, in server order. Invalid/duplicate records,
provider diagnostics and reflected credentials cannot enter the public response.
Identity-only/signed-out accounts refuse access before the request; changed
permission/revision or a late cancelled reply invalidates the result. Credential
reads capture the grant and its own revision inside the serialized store: a
later queued authorization cannot label an old bearer with a newer revision.
Profile resolution and catalog loading refuse that race before admission/network.

The shared `accounts.models` RPC accepts only an account ID. Both the actual
Python native adapter and Browser messaging bridge exercise it through one IPC
host, including logout and secret-field refusal. Host shutdown cancels catalog
requests; maintenance refuses new model loads because protected access can renew
credentials. Existing connection setup adds a plan-only model chooser: native lists
server display names with their model IDs, Browser supplies input suggestions.
Selecting an option edits the draft; it neither saves nor starts inference.
Provider/account changes clear suggestions, and late replies cannot fill a
changed connection. Model availability still requires a completed connection
check. Production eligibility remains false.

Eight catalog contracts and both expanded setup suites pass with synthetic
responses. The documented endpoint is verified against official
[account-specific models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference).
No real account catalog or inference is claimed. Type/build and 60 focused
account/catalog/controller/profile/host cases pass. All 65 Browser cases and
590 native cases pass (588 pass, two Mac-only skips). The isolated real Linux
Secret Service account save/rotate/restart/logout/cleanup proof passes again.
The final root suite passes 462 cases (460 pass, two opt-in Docker memory proofs
skipped). Platform source identity follows in the publishing checkpoint.

## Native managed account route: inspected constraints — October 1

The actual pinned Codex 0.159.2 generated schema includes managed browser/device
login, login cancellation, account read/logout and rate-limit read. Its external
`chatgptAuthTokens` input is explicitly marked **internal use only — do not use**;
this implementation does not import SIWC or native tokens through that route.
The [current app-server documentation](https://learn.chatgpt.com/docs/app-server#auth-endpoints)
excludes commercial/hosted use of legacy managed authentication and recommends
SIWC; this is not a commercial eligibility workaround.

Native managed login needs a separate reviewed authority/state design before
wiring: isolated Augmentor-owned `CODEX_HOME`, mandatory protected keyring mode
without `auto`/file fallback, one serialized refresh authority per account, and
stable account/thread/funding bindings across model workers and logout. Email
alone cannot identify a workspace. Never read the owner's global Codex cache,
extract its tokens or silently relocate existing native history to share auth.
The [official auth configuration](https://learn.chatgpt.com/docs/auth#credential-storage)
provides strict keyring storage; actual Linux/Mac store and live login acceptance
remain necessary. This inspection is a remaining design contract, not a built
native managed account route.

## Remaining C4 requirements

- Confirm distribution eligibility and qualify actual consent/browser launch on
  eligible Linux/Mac builds; production SIWC remains disabled.
- Implement the separately permitted Codex-managed login route and isolated state.
- Qualify the now-wired current account model choices against real OpenAI and
  complete known usage/limits, including exhaustion after partial streaming,
  with explicit funding and no silent fallback.
- Audit and qualify model checks, prompt improvement, branches/recovery and memory
  auxiliary work under the same account permission and funding policy.
- Qualify real consent, expiry/revocation, completed inference, worker restart and
  both user interfaces. Complete C0–C3 and C5–C9 acceptance too; the native package
  notice gate and pending owner-directed Qwen formatter activation remain open.

The behavior follows official OpenAI documentation inspected October 1:
[registration](https://developers.openai.com/siwc/token-sharing-open-source/sign-in),
[accounts and sessions](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions),
[recovery](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery)
and [Codex app-server renewal](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server).

## Published renewal source and platform checkpoint

Implementation `57ba17d64721ae79322a366ef0e87d8aafe34730` passes
[Mac 14/26 CI](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36875229525),
including actual pinned renewal contracts, native setup and all six real Keychain
account lifecycle proofs through build, packaged Desktop and Browser interpreters.
[Linux CI](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36875229544)
passes application/Browser/credential, Home, source boundary, production npm
notices and extension packaging; Debian still fails at the existing unreviewed
native Codex executable gate. Installed-package checks skip. This CI qualifies
the preceding renewal checkpoint, not the subsequent model catalog source.

## Eligibility request prepared for owner review

The following is a draft for OpenAI, not a submitted request or evidence of approval:

> Augmentor Agent is a local personal-agent application for Linux and macOS,
> with a Chromium interface sharing the same local host. Its public repository
> is https://github.com/ManoloRemiddi/augmentor-agent. Augmentor-authored code
> uses MIT with Augmentor Resale Restriction, rather than unmodified MIT.
>
> We are adding Codex app-server as a replaceable local execution harness.
> Users may explicitly choose their own Responses-compatible API/local provider,
> or authorize ChatGPT plan usage through Sign in with ChatGPT. The latter would
> use the documented public Responses endpoint, protected per-account credentials
> and explicit usage consent, without shared accounts or an Augmentor inference proxy.
>
> Please confirm which subscription route is permitted for this license and for
> free local versus any future paid distribution, and whether commercial partner
> registration is required. Please also clarify whether newly integrated local
> applications may use the legacy managed Codex login route. We will preserve
> the current license and keep affected production login disabled until confirmed.

The owner must confirm launch/business details and authorize any external
submission. Do not attach source archives, credentials, private transcripts or
local configuration. The API/local implementation and native notice review can
continue independently; this eligibility question blocks live subscription
acceptance and its affected distribution, not those engineering tasks.
