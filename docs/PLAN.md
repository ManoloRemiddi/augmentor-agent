<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Implementation plan

This is a dated plan/ledger, not the current source map. Read the
[agent handoff](AGENT-HANDOFF.md) and [current architecture](ARCHITECTURE.md)
for the present implementation, Git ref and qualification.

Order: organize both repositories → implement and verify Linux → implement the browser extension. Linux implementation is now present. The checklist and acceptance evidence are recorded in VERIFICATION.md; browser work remains a separate next task.

## L0 — Repository organization

- [x] Inspect the existing Linux app and identify the browser source repository.
- [x] Define two independent successor repositories and record source revisions.
- [x] Assign shared runtime/protocol ownership to the Linux repository.
- [x] Record architecture, migration boundaries and acceptance gates.
- [ ] GitHub publication, if requested; local development does not depend on it.

## L1 — Pi integration · implemented

1. Resolve the exact Pi release, record its package metadata, install a locked compatible set, and add Node/TypeScript build and check commands. `0.85.1` under `@earendil-works` is the installed and tested dependency set.
2. Run a minimal coding-agent SDK host with separate state/resource directories and an explicit model. Use Pi's existing session manager, provider layer and resource loader; verify that agent-core is supplied through that stack.
3. Exercise a real local model, streamed output, one harmless tool, Stop, persistence/resume, and a missing-model failure. Record model identity and actual versions. No cloud-provider charges are needed for this milestone.
4. Confirm how supported SDK hooks carry questions, approvals and package loading outside Pi's TUI. Compare subprocess RPC only if needed, then record the integration decision.
5. Define the client contract and representative fixtures from working behavior: session/turn identity, errors, recovery, interactions, capability/version handshake and cancellation of queued work.

**Exit:** a small reproducible host demonstration and contract checks pass with DSH disconnected from the demonstration. No UI port depends on speculative APIs.

## L2 — Native Linux conversation slice · implemented

1. Port reusable Qt presentation, composer, preferences, icons, shortcuts and window/workspace behavior from the recorded baseline, retaining source attribution and relevant tests.
2. Replace `dsh.py` with a Pi-host client. Adapt the controller and transcript renderer to the new contract; update DSH-specific UI wording and settings actions.
3. Implement explicit model selection, new chat, streaming, Stop, error display and restoration of the last Pi session.
4. Keep the host alive when the app hides. Distinguish UI disconnect, host failure and model failure; do not replay a prompt on reconnect.

**Exit:** on MX/KDE, launch → choose the local model → chat → stream → Stop → hide/show → restart UI and resume. The extension is closed and the app has no dependency on the DSH endpoint.

## L3 — Linux feature parity and tools · implemented

1. Port the system-profile, visible-browser-open and AT-SPI observation helpers; register them through a Pi extension package. Carry forward target validation, bounded output and cancellation.
2. Restore session list/history pagination, rename and saved-chat behavior using Pi sessions plus Augmentor metadata. DSH-wide history browsing remains a legacy-only feature initially.
3. Replace the DSH prompt-library backend with Pi-compatible prompt resources plus the minimum shared editing/catalog layer needed by Augmentor. Preserve slash insertion without auto-send. Provide an explicit, repeatable import of reusable prompt content; preserve the original store.
4. Restore model pins and appearance preferences through an explicit migration step. Configure the local model from known endpoint/model metadata without copying the DSH credentials database wholesale.
5. Implement the execution policy and Qt question/approval handling. Cover allow, deny, timeout, Stop and disconnect; avoid hanging tools when an interaction cannot be displayed.
6. Replace the DSH versions/settings panel with actual Augmentor/Pi versions and supported configuration controls. Preserve compact view, transparency, pinning and shortcut behavior.

**Exit:** the [migration inventory](SOURCES.md) has an implemented or explicitly deferred outcome for every item, supported by automated checks and the required live desktop evidence.

## L4 — Linux release and browser unlock gate · implemented

1. Package the Qt app and separately launchable runtime. Add install, upgrade, uninstall and diagnostics for the supported MX environment, including dependency checks and non-conflicting desktop identity.
2. Test a clean installation using isolated application state. Exercise model outage, host crash/restart, socket loss, pending interaction, cancellation and concurrent client attachment. Ensure a single conversation has one active execution owner.
3. Verify the user-visible desktop flow: shortcut, expanded/compact view, pin/unpin, selected-model chat, safe filesystem tool, OS profile/observation, visible browser dispatch, prompt insertion/editing, history and session restoration.
4. Prove no DSH runtime calls or DSH configuration dependencies remain in normal Pi operation. Do not stop or modify the user's running DSH merely to perform this check; isolate the test environment instead.
5. Record release compatibility and remaining limitations. Distribute the runtime and protocol as versioned artifacts so the browser repo can consume them without importing the Linux checkout.

**Browser work begins only after this gate passes.** General GUI mouse/keyboard automation, portal screen capture, broad distro coverage, OS customization, automatic updating and ResonantOS integration are follow-on work, not implied parity requirements for the current Linux alpha.

## B1–B3 — Browser extension later

1. Port the existing MV3 side panel, work-tab tracking, page overlays and executor; preserve the native-messaging boundary. Replace the DSH pipe and plugin with a client for the proven Pi runtime and a Pi browser-tool package.
2. Restore browser chat/history/models/prompts, explicit browser session identity, tool results, cancellation and action verification. Reuse shared runtime services; keep browser UI/executor responsibilities in the browser repo.
3. Verify work-tab targeting, navigation/stale-target handling, service-worker suspension/reconnect, runtime restart, denied/expired interactions and unknown action outcomes. Test browser-only and combined Linux/browser use before packaging.

The browser repo's `docs/PLAN.md` carries the deferred checklist. Firefox and Safari are outside the initial Chromium migration.

## Verification policy

Use existing UI/helper regression tests where their behavior still applies. Add meaningful tests at the new boundaries: streaming/history consistency, model identity, persistence, cancellation, interaction resolution, protocol compatibility and reconnect without duplicate execution. Keep deterministic tests separate from live model and desktop checks, and record which were actually run. A scaffold-only verification is not an application test.

## Recorded decisions and future choices

- Exact package lock: 0.85.1; public SDK with private Unix-socket app transport.
- Core SDK and bundled Linux tools cover the initial scope. Additional Pi packages/skills are explicit resources.json opt-ins, with a tested local package-loading path.
- Pi owns agent conversations; Augmentor stores saved metadata and a durable display journal. Prompt Markdown files use revision hashes; imports preserve originals.
- A detached single runtime is started/recovered by safe health probes under a file lock; no systemd dependency. The KDE launcher uses its own desktop ID.
- Public/private GitHub visibility and release channel when publication is requested.

## October 27 repair integration

Owner authorizes tested repairs and deployment to Linux Desktop/Browser, personal Mac Mini and VZmore Windows, full application control without repeated action approvals, preserving models/sessions/drafts. Independent scope review actually ran successfully on `claude-opus-5-5` using the existing subscription. Lead accepts distinct reconciliation/repair/deployment gates, immutable staged artifacts, minimal SDK shell defaults and existing preview/jobs reuse. Explicit authorization covers both legacy and Harness and deliberate Chromium permission changes; no new OS/account access is inferred.

Integration starts from deployed tablet ancestry `7ea6a36b`, retains `ab7f1665`, and merges current main, macOS Wiki, research, deployed memory relevance and EDGE capture without rewriting history. Conflict resolution preserves tablet capabilities, Mac Search/Wiki and both memory test families. Dirty old primary is preserved independently. Unfinished unrelated draft PRs remain separate. Full-control browser/desktop adapters require a separate design/change review and actual target verification. Builds use DATA and the required 64 GiB reserve.

Reconciliation verification: strict source check/full build pass. The compiled pilot Host differs only in formatting at the two Ungrouped validation statements; compiled Wiki, search and installation defaults match the installed overlay byte-for-byte. Nineteen focused memory/Wiki/default/capability tests pass. Opus reconciliation review found no lost conflict behavior. Its possible large-receipt issue is bounded by the actual memory service query (`LIMIT 24`); no unrelated memory redesign is included. The broad suite subsequently completed with the failures recorded below.

The separate full-control design review ran successfully on Opus5.5. Useful recommendations: per-host authenticated IPC rather than a central broker, CDP trusted input with an extension-side method allowlist and exact-tab leases, selected portal stream identity, and Windows transport/UIPI/DPI checks. The response incorrectly claimed source inspection of nonexistent paths despite a tools-disabled review; those claims are rejected. Actual code already keeps its native port in the service worker and spawns the harness lazily. Lead will retain those working mechanisms and verify every design claim against source. Owner full-control authorization governs deliberate permission updates; target checks are correctness checks, not new per-action consent.

Full baseline suite was stopped after its first fixture failures and stalled test worker; logs retained. Isolated diagnosis confirmed the copied fixture lacked AUGMENTOR_PYTHON and fell back to a nonexistent source `.venv`. The managed build path also made temporary browser/IPC paths long. Correct the test environment to the declared bundled interpreter and a shorter DATA managed root; do not call these product test passes.

Actual browser code review completed on `claude-opus-5-5`. Lead accepts and fixes: macOS symlinked temp paths, oversized-response survival, trusted Enter/Space text, failed-attach cleanup, invalid shell environment fallback, stale executor records, multi-profile Stop, native compatibility forwarding, private-directory cleanup race and session generation. Review also exposed a remaining browser-surface tool denylist: remove it and retain shared execution-policy gates. Tool visibility stays consistent across hot permission changes; read-only/ask/full execution must be verified, rather than adding a second registration policy. Canvas centre input only focuses; guidance now requires deliberate caret positioning and independent readback. Pi1.1.0 actually supplies the PowerShell built-in; seconds timeout/mutable tool-call input are checked against the installed SDK. Native-helper and portal changes have their own actual-code review in progress. No target is promoted on advice alone.

Desktop actual-code review also returned with Opus5.5 recorded (the CLI receipt additionally reports Opus4.8 usage). Lead accepts native Windows transport/lock proof and actual mixed-scale portal mapping as promotion gates. Its requested owner confirmations for persistent input and using the real desktop are already covered by the owner's explicit “total control, no limitation” instruction; no repeated approval is added. The pilot registry is a personal installed application, not a disposable test sandbox. Correct descriptions distinguish Windows' ordinary signed-in desktop access from macOS TCC and Linux portal grants. Existing OS account permissions remain real constraints. The unchanged Windows pipe/lock adapters will be supplied for review rather than assumed absent.

Follow-up actual Opus5.5 transport review accepted the unchanged Windows pipe/identity/lock implementation and asked for a real Qt Unicode round trip rather than creating an account on the owner PC. The actual round trip passes with paced per-character batches, including emoji; do not replace that verified evidence with an untested surrogate-order hypothesis. A bounded client recipe preserves the exact three inspected native-host baselines and old client dependency/product versions. Separate markers require an independent candidate; actual OS sealing and activation remain mandatory. Windows has no local build tools: prefer its existing native GitHub build/installer workflow over installing Visual Studio on the owner PC or bypassing update/recovery leases. Final actual-diff/deployment review is running before promotion.

The broad Python run completed 1,391 cases with 89 errors, 10 failures and 46 skips; most errors were deterministic Unix-socket path overflow caused by long fixture prefixes under the required DATA workspace, and six cases lacked the separately built browser plugin. Shorten only those authored fixture prefixes and build that declared plugin before rerunning. Product path validation and storage reserve remain unchanged. Remaining older GUI expectations need explicit classification. Focused repair source tests currently pass 41 new contracts, 87 policy/session/recovery cases, six executor cases and 14 launcher cases. These are source evidence, not installed adoption.

Final actual-diff Opus5.5 review permits draft publication but blocks promotion pending concrete corrections and candidate smoke tests. Lead accepts: never use os.kill(pid,0) on Windows; probe the authenticated endpoint, decode streaming UTF-8 correctly and pass Python -Xutf8, isolate Desktop and panel work-tab contexts, include capabilities/tabs for one or many executors, include/import-check all compatibility dependencies and actually exercise the locked0.85.1 deadline. Also accept a real Windows tool→service test and installed adoption gates. New readback supports bounded HTML ZIP decoding and paged output with an export hash; no live Docs success is inferred. Existing fresh AH default predates this repair; only legacy implicit DSH selection is preserved. The global queue selector alias is being narrowed to the visible owner-restored control contract. No target is promoted yet.

Post-correction review actually ran on Opus5.5 alone. Lead accepts surrogate-safe readback pages and ASCII-escaped internal JSON, complete compatibility baseline hashes, precomputing transforms before writes, non-object executor errors, forwarded import diagnostics, sealed import checks, cold-panel rendezvous and headful Chromium qualification. Desktop tool timeout is actually 105 seconds and client 115, so the review's 25-second Windows concern refers to another adapter; still run the maximum 256-character case. A real registered-tool→Windows service→Qt round trip passed Unicode, chord, extended Home, consumed-token rejection, Stop and 256 mixed characters in 29.16 seconds; repeat to investigate an earlier intermittent ordering failure. The 100 ms pacing is a tested heuristic, not universal text-entry proof. Service status now includes its actual root and source hash.

A separate deployment-binding opinion actually ran on Opus5.5 alone. Lead accepts independent Desktop/Pi deployment after an old-extension/new-host compatibility test, leaving Browser adoption pending when the owner Chrome surface cannot be reached. The actual Linux extension is unpacked at its separate version directory; the existing managed native launcher follows Desktop selection. Stage the extension outside that registered path, preserve its key/local storage, and never edit Chrome permission preferences. Version comparison alone cannot prove adoption. The two maintained DSH product presets pin an older desktop adapter; use a bounded, additive, hash-checked migration under the existing cold configuration lifecycle, preserving their other entries and ownership receipts. Preserve custom and archived preset pins. The selected inference models and saved transcripts must remain unchanged. The docs skill requires the new capability tool; its old unsupported workflow needs a backed-up replacement, not a return to browser-only policy.

The pre-repair integration already returned AH for a completely fresh Browser profile (`1cc4943c:state.mjs`); this repair only preserves implicit old DSH session/model keys. Reject the review's claim of a new fresh default. CI exposed a real Home image dependency omission introduced by the shared browser adapter; include that module/declaration closure in both image build and runtime stages. The Mac fixture also uses a long system temporary path; verify its actual error before changing a product path. Do not classify any failing check as passed.
