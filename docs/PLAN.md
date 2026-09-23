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
