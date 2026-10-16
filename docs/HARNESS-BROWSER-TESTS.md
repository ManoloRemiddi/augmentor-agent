<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Browser observation lifetimes in Harness tests

Hosted `f073d195` Debian retained one failure among 1,601 Node cases: HTML
preview's changed-related-script observation timed out in CDP `Runtime.evaluate`
(`tests/harness-html-chromium.test.mjs:26`). Local source, ordinary and exact sealed
cohorts passed that case. The hosted log lacked iframe/session/context lifecycle
receipts, so its exact cause remains unproven. Later green runs alone cannot
establish a product or driver cause.

A separate actual Chromium control reproduces a missing-lifecycle case: an
awaited evaluation in an opaque sandbox iframe receives no reply after removal,
although its parent/browser remain live. The preceding helper waits for its
unchanged ten-second command timer. The corrected opt-in observation settles on
the actual detached-session event, with an unknown result and no replacement
command. This addresses a demonstrated failure class and adds receipts needed to
investigate another hosted failure.

## Test-only changes

`tests/fixtures/harness-cdp.mjs` provides an explicit `read` API for four methods:
`Runtime.evaluate`, `Page.getFrameTree`, `Page.createIsolatedWorld` and
`Target.getTargets`. Callers must use it only for observations; it is not an
expression sandbox or production permission grant. The generic `call` path can
act and retains its original behavior. Its unknown action outcomes are never
retried, converted to success, or retired by this observation logic. No agent,
GUI, HTML transport, sandbox/CSP, network policy, model setting, installed app
or running review changes.

Context loss retires only pending observations with matching session/context
identity. Cleared contexts, frame removal, detached sessions and transport close
have explicit scopes. Missing identities do not mean all contexts. Retired
sessions/closed transports refuse another observation before sending it. Retired
request IDs are removed; late replies cannot settle a fresh read. Only small
identity fields are snapshotted, independent of later caller-argument mutation.

The HTML test uses the observed unique execution-context ID paired with its
actual frame/session, and discards detached cached session mappings. It never
falls back to the parent or a guessed context. The
[official CDP Runtime schema](https://github.com/ChromeDevTools/devtools-protocol/blob/master/json/js_protocol.json)
documents that numeric IDs can be reused across processes and supplies unique
IDs and context lifecycle events. The current-context map keeps at most **256**
entries; unavailable/evicted identity requires a fresh observation. The last
**128** diagnostic rows retain method/session/context/frame identifiers and read
disposition, without expressions, model payloads, headers, tokens or document
bodies. Page exceptions, console errors and failed HTTP responses remain
collected without filtering.

The existing ten-second command timer, twelve-second observation loop, sixty-
second HTML case, worker count and original assertions remain unchanged. The
original caller polls observations after scope loss. Pointer dispatches, browser
restarts, model requests and application actions are not replayed by this helper.

## Focused evidence

Seven focused cases pass: five authored WebSocket/CDP contracts, a real cross-
process iframe case and the complete original HTML-preview test. They cover
exact cancellation scope, generic action uncertainty, changed caller arguments,
late replies, unrelated/root frames, malformed identities, pre-send refusal,
transport close, reused numeric IDs with distinct unique IDs, bounded receipts
and preservation of actual page errors.

The real browser proof reloads the same iframe and removes/recreates it during
an old read. It accepts only explicit lifecycle retirement or Chromium's observed
native `Inspected target navigated or closed` rejection, within the same one-
second assertion. New document markers are observed and their read counter stays
zero: the old command was not replayed. An initial assertion demanded only the
helper-specific code even when Chromium already rejected the context; that
failed driver/diagnostic log remains retained. Two exploratory probe failures
used incomplete OOPIF target/frame lookup; those logs also remain retained.

The original HTML case retains static/interactive preference, full 300 KiB
asset, dependency/root reload, malformed/oversized recovery, parent/storage/RTC/
worker/network restrictions, real pointer input, narrow viewport and joined
cleanup assertions. Broader cohorts and hosted acceptance follow their own
qualification; focused results do not certify all CI or product parity.

Run `node --test --test-concurrency=2 tests/harness-cdp-lifecycle.test.mjs tests/harness-cdp-lifecycle-chromium.test.mjs tests/harness-html-chromium.test.mjs`
with the documented prepared Python/Qt prerequisite for the real Host fixture.
All peers/profiles/documents are independently authored; only exact owned actors
are stopped. The owner's MX review/data are never test fixtures. Full Harness
migration, physical feedback and distribution gates remain.
