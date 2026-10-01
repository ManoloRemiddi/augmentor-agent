<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Codex ChatGPT accounts: internal implementation and acceptance

Status, October 1: OAuth transactions and protected account persistence are
implemented in development source. This is partial C4 work in the
[full C0–C9 plan](CODEX-INTEGRATION-PLAN.md), not a functioning user login or
permission to distribute subscription access. The classes are not wired into
the shared host's RPC, profile resolver, Desktop or Browser. Production login is
disabled by default; no real account or provider token was used in these proofs.

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
first exchange; it is not an active or verified account. The future host login
controller must durably own that provisional record. Explicit plan-permission
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
credential store; the account listing omits those references and all tokens.
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

## Evidence

```sh
npm run check
npm run build
node --test tests/codex-chatgpt-auth.test.mjs tests/codex-chatgpt-accounts.test.mjs
python3 scripts/proof-codex-secretservice.py
```

The focused tests use fresh cryptographic keys, signed synthetic identity tokens,
real loopback HTTP callbacks, a mocked OpenAI transport and a synthetic credential
store. They cover account isolation, returning identity, scope refusal, rotation,
crash-state recovery, unknown outcomes, persistence failures, locked logout and
revocation confirmation. They do not certify real OpenAI sign-in or inference.
All **55** focused cases pass on Linux. The complete Node suite passes **410 of
412** cases with two explicitly opt-in Docker memory proofs skipped; TypeScript
checking/build and six license-inventory tests pass. The full suite requires the
isolated Qt/QtTest environment documented by the existing test workflow.

The expanded actual Linux Secret Service proof passes in a disposable pinned
Debian container, using a separate D-Bus session/keyring and no network. It verifies
account save/rotation/reopen/logout and cleanup through the real Node/Python OS
store. Renewal and revocation remain synthetic in this proof. The same expanded
script is required by existing Mac build/Desktop/Browser Keychain CI steps;
fresh Mac results must be recorded separately. The owner's wallet was untouched.

## Remaining C4 requirements

- Confirm the distribution's eligibility for each subscription route.
- Wire one host-owned login controller, provisional registration recovery,
  cancellation/status and existing Desktop/Browser settings without exposing secrets.
- Bind selected accounts/models to connection profiles and fence worker/account
  switching, logout and token renewal. Renew an idle app-server process and resume
  its saved thread; never retry unknown prompt/tool outcomes.
- Implement the separately permitted Codex-managed login route and account-specific
  model/usage behavior, with explicit billing selection and no silent fallback.
- Qualify real consent, expiry/revocation, completed inference, worker restart and
  both user interfaces on Linux and macOS. Complete C0–C3 and C5–C9 acceptance too.

The behavior follows official OpenAI documentation inspected October 1:
[registration](https://developers.openai.com/siwc/token-sharing-open-source/sign-in),
[accounts and sessions](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions),
[recovery](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery)
and [Codex app-server renewal](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server).
