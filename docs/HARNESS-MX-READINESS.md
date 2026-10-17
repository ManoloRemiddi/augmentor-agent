<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor Harness: current MX readiness

This is the current acceptance map, checked on October 17. It preserves the full
[P0/P1 migration scope](AUGMENTOR-HARNESS-MIGRATION.md#required-feature-parity),
including work that is not finished. Older dated matrices are historical evidence.
The owner's immediate priority is a useful MX Linux app; voice, other Linux
distributions, Windows and macOS rollout are deferred, not completed.

## Use the installed review

Open **Augmentor Harness (MX)** or **Augmentor Harness - Migration Pilot** from
the application menu. The stable opener obtains a fresh private browser link;
an old tab's token can expire after a restart. The equivalent commands are
`augmentor-harness-review open main` and `augmentor-harness-review open pilot`.
Both reviews remain **97d95d58 / 20261017-095821-fb78d6df**, with the existing
pinned Office engine. [Installed checks and preservation](HARNESS-MX-FEEDBACK.md#current-mx-review--october-17).

The newer optional managed Office candidate is separately staged and unselected.
Its tests do not update the installed reviews. Public packaging, production
Desktop cutover and DSH retirement are separate from using this private MX review.

## Requirements and evidence

“Installed” identifies the current review's available behavior. Recorded fixture,
local-model and installed-owner evidence qualify different claims; no total test
count proves every workflow or owner acceptance.

| Requirement | Current evidence | Remaining acceptance |
| --- | --- | --- |
| Original GUI, branding, themes and layout | Original DSH presentation; Augmentor motion in sidebar, welcome and running seats; Working wording; theme/contrast/responsive corrections. [Brand](HARNESS-BRAND.md), [appearance](HARNESS-APPEARANCE.md). | Owner physical feedback; deeper diagnostics remain incomplete. The requested original GUI takes priority over the proposal's earlier P2 shell scheduling. |
| P0 Models and reasoning | Installed configured catalogue, effective pin/hidden order and top-of-list opening. Exact local-model identity guard; explicit reasoning controls. [Configured models](HARNESS-CONFIGURED-MODELS.md), [route checks](HARNESS-LOCAL-MODEL-ROUTES.md). | All external providers/OAuth/virtual routes and representative thinking mappings; catalogue presence does not prove endpoint health. |
| P0 Chat, reasoning, Stop and progress | Pi owns conversations; streamed reasoning, observed progress and interrupted output have original-GUI and local-Qwen evidence. [Live checks](AUGMENTOR-HARNESS.md#live-qwen-queue-steering-and-stop--october-17). | Wider provider and physical-use acceptance; a model's prose is not evidence that an interrupted action never ran. |
| P0 Trajectory and Context | Installed original Trajectory and adopted Apache-2.0 Context/Insights/Fleet; effective request bodies, original tool data, coverage labels and cold reads. [Interface](DSH-GUI-ON-PI.md), [Fleet](CONTEXT-FLEET.md). | Complete causal attribution across every resource/provider transformation and wider long-history/search/performance acceptance. Unknown coverage remains explicit. |
| P0 Prompt Library, templates and instructions | Harness pair shares twelve prompts and one service; original editor, conflicts, submitted/prepared inputs and Improve/Undo have source/live evidence. [Writing tools](HARNESS-PLUGINS.md#prompt-library-and-improve-prompt). | **Installed Agent still has a separate store.** Actual cross-product service adoption and representative rewrite meaning/timing remain open; see the rehearsal below. |
| P0 History, Edit and Branch | Native Pi boundaries, unchanged parents and imported historical cuts; original v1/v2 Branch cold recovery and explicit Send pass against the installed artifact. [History](HARNESS-DSH-HISTORICAL-IMPORT.md), [Branch](HARNESS-BRANCH-CONTROLS.md). | Owner pilot feedback before more transfers; supported captured families are not every possible DSH history/context. |
| P0 Queue, follow-up and steering | Installed durable queues, cold Resume and local-Qwen running-tool Stop/Steer evidence. [Queue contract](QUEUE-AND-STEERING.md). | Wider model/tool outcomes and owner feedback; unknown actions are not automatically replayed. |
| P0 Tool budgets and originals | SDK context bounds, retained original results, images/excerpts and cold inspection. [Budgets](CONTEXT-BUDGET.md), [implementation evidence](AUGMENTOR-HARNESS.md). | Broader live payload/integration coverage; original access and actual next-request context must be checked separately. |
| P0 Action-aware execution and recovery | Bounded recovery and known/unknown action guards have actual SDK tests. [Recovery](AUGMENTOR-HARNESS.md#bounded-recovery-and-startup-cancellation). | Semantic task success and authoritative third-party job receipts are not inferred from a completed test/tool. |
| P0 Browser and consented desktop work | Scoped browser/native executors and bounded specialist tests; original integrations remain available. [Specialists](AUGMENTOR-HARNESS.md#desktop-specialists-in-durable-jobs--october-11). | Actual required desktop/browser workflows and installed-surface adoption; browser-only sessions receive no general desktop authority. |
| P0 Privacy, reconnect and state | Managed reporting opt-outs, authenticated private transport, scoped inspectors and traced fresh/cold/update/rollback workflows. [Privacy](PI-PRIVACY.md). | Real external-account/extension/service destination breadth, future pins and public installation; bounded observations are not a firewall. |
| P1 Relationship/project memory | Actual isolated Pi/Hindsight/Qwen recall, historical cutoff, pause, restart and outage proof; review journal/settings retained. [Live memory](PI-MEMORY-LIVE.md). | Production identities/banks and companion versions are not yet aligned with Harness. Default-mode timing/quality limits are retained; no silent mode change. |
| P1 Voice and hands-free | Existing DSH/product paths preserved. | Explicitly deferred for this MX-first phase; typed contracts do not qualify physical audio. |
| P1 Wiki and Metafolder | Installed vault query and nine approved skills; selected live ingest with disclosed refused-edit/write fallback; original folder controls. [Plugin evidence](HARNESS-PLUGIN-PARITY.md). | Other skills, owner mutation, companion CLI/transport and physical folder moves remain separate. |
| P1 Search and existing MCP | Accepted MIT Search alternatives; installed Search/Wiki choices and five stored connections, two On/three Off. [Plugins](HARNESS-PLUGINS.md), [MCP](MCP-TRANSPORT.md). | Representative service operations/outages/authentication. Disabled or unavailable Comfy/Unreal connections must not be silently enabled. |
| P1 Plans, todos, goals, jobs and delegation | Original controls, durable Pi ownership/status and archived DSH inspector views. [Fleet](CONTEXT-FLEET.md), [runtime evidence](AUGMENTOR-HARNESS.md). | Broader live integrations/usage and unknown outcomes; archived DSH children do not become resumed Pi jobs. |
| P1 Home and embedded profiles | Scoped adapters and Home runtime CI; existing DSH integrations preserved. [Home](HOME.md). | Required live devices/embedded roles, memory/operation ownership and installed-surface adoption. DSH stays available. |
| P1 Packaging, updates, windows and mobile | Verified immutable MX reviews, stable external-browser opener, private backups and guarded lifecycle. [Deployments](DESKTOP-DEPLOYMENTS.md). | Production Agent alignment, public Office/source distribution, broader window/mobile workflows and later OS releases; version equality alone is not compatibility. |

The [source comparison, ratings and reuse decisions](AUGMENTOR-HARNESS-MIGRATION.md#comparison-for-the-augmentor-use-case)
remain the analysis baseline. MIT DSH/Pi notices, Apache Context and other supplier
obligations retain their identities; the project is not an all-dependencies-MIT
redistribution. [Exact licensing decision](AUGMENTOR-HARNESS-MIGRATION.md#licensing-and-attribution).

## Installed Agent alignment rehearsal

Read-only inspection confirms that the two Harness reviews share a store, while
the default Agent's prompt/memory companions use another; observed native clients
use that legacy store. All twelve prompt
names/texts currently match, but future edits are not live-synchronised. The
production memory store is populated and uses another person identity. Its old
companions lack the new shared-data ownership guard. Their sources do not match
the current Harness companions or the selected Desktop artifact. Selected and
running component identities must therefore be checked separately. No live paths, contents or identifiers are published.

The production shared databases also sit beside application data. Passing that
whole directory to the dedicated-store importer would be refused; replacing it
as though it contained only memory/prompts would be wrong. A new synthetic test
verifies that the existing guard preserves the application and databases.

An **offline rehearsal on private snapshots** successfully uses the unchanged
importer in the correct direction: retain production as the person/engine/settings
authority and merge the unprocessed review data into a clean dedicated clone.
All existing production prompt records, improvement instructions, memory records,
banks/caches/outbox, jobs/charges, settings and original projections stay exact.
The review's nineteen captured records remain, and only its two derived work
scopes add projections. Seventeen pending admissions and the old activity window
are archived rather than activated. No engine/model/service starts or observed
IPv4/IPv6 network syscall occurs. No real project transfer or live data merge occurs.

These are independently consistent **online SQLite snapshots**, not one globally
cold backup and not an adoptable release. The first postflight incorrectly expected
no additional projection rows; read-only verification confirms every original
row and only the two expected additions without repeating the merge. All three
copies are frozen under reserved archive paths; current companion and Node
startup guards refuse them. The old production companions are not qualified by
those guard tests. [Aggregate evidence and limits](../release/harness-mx-readiness-agent-alignment-20261017.json).

Fourteen focused checks pass in source and against the exact installed MX artifact,
including processed-target preservation, mixed-root refusal, actual companion
ownership, Native/Node prompt peers, two real SDK owners, interruption fencing
and historical Branch v1/v2. The shared importer/helper/guard bytes match the
installed artifact. This is not a production adoption or new full-suite claim.

The concrete adoption path still requires:

1. The matched writing editors now pass the authored-data qualification below.
   Finish actual installed-surface deployment and existing-bank memory recall,
   outage and restart checks; old auto-start helpers are not eligible for adoption.
2. Prepare a dedicated shared-data layout and paired launcher settings. Preserve
   production identity, engine configuration/volumes, prompt identities, budgets
   and capture/processing choices. Do not point either app at an evidence copy or
   transactionally replace the mixed application directory.
3. At a guarded quiet cutover, stop all callers/companions and verify fresh full
   cold backups. Retake and inspect the real stores; the rehearsal is not that backup.
   Install a qualified immutable artifact through the existing deployment lifecycle.
4. Verify one common service, actual cross-surface edits and existing memory banks,
   native histories, busy-work veto and rollback before declaring alignment complete.

The [dedicated legacy export](HARNESS-SHARED-PROFILES.md#dedicated-legacy-store-preparation--october-17)
now prepares a new store from the stopped mixed application layout without
replacing application files, identities, engine settings or processing choices.
Source/ordinary authored qualification covers exact export, races, interrupted
publication and populated-cache Native recall through search outage/restart.
It has not exported the real Agent store, changed launchers or updated the
installed reviews. The unsealed ordinary assembly is not deployment evidence.

## Actual writing clients: isolated qualification

The new [writing-client record](../release/harness-writing-client-qualification-20261017.json)
uses the real Qt editor/task dispatcher, a genuinely loaded Browser extension,
the Native Messaging host and the original Harness page against one real prompt
service. All records are independently authored; no private source is copied into
the repository. No owner window, profile or model is used.

| Client set | Observed result | Qualification boundary |
| --- | --- | --- |
| Current source Native/Browser/Harness | Prompt edits in all three directions, rename with stable ID, improvement instructions, stale-save refusal, explicit reload, unchanged composer/history and managed cold reopening pass. | Authored data, no inference; this does not connect the installed Agent. |
| Exact installed MX artifact | The same two checks pass against 97d95d58, including its Browser and companions. | Isolated execution of sealed files; selected/running owner reviews are unchanged. |
| Actual older Native artifact with matched MX Browser/Harness/companions | Its real editor passes the same three-surface writing and managed-restart sequence. | A prestarted current companion is required. Warm compatibility does not qualify its own helper. |
| Older Native cold auto-start | Traced actual client starts its own older helper; another current helper can own the same authored data through a different socket. | Explicit negative control: **unsafe for shared-store adoption**. Current cold startup refuses that duplicate. Both controls observe the local connection and zero IP network syscalls. |
| Browser extension shipped beside that older Native artifact | The real extension stays at Connecting; its Prompt Library does not mount, including after supported Pi selection. | Unresolved compatibility failure. This is that artifact's extension, not proof of which extension the owner has loaded. No version/manifest is spoofed. |

The fixtures use real inactive Native task dispatch, without starting chat
monitoring or voice. Browser controls bring their actual page to the foreground
before pointer preparation. The earlier timeout occurred inside frame-based
preparation after switching tabs; explicit foreground selection passes. Extension storage/runtime readiness is observed before
one supported harness selection. No timed-out mutation is repeated or error hidden.

These results close the matched writing-editor fixture gap, not existing-bank
memory recall/outage or live adoption. Deploy matching Browser, Native and companion
builds, stop older callers at cutover, and retain the dedicated-layout/cold-backup
and rollback requirements above. Voice and later-platform qualification stay deferred.

## Required scenario ledger

The original specification's ten scenarios remain acceptance requirements:

| Scenario | Evidence / open boundary |
| --- | --- |
| 1 Real provider/model/effort/reasoning | Selected local-Qwen proofs and exact-ID guard; wider providers/effort mappings remain open. |
| 2 Text/error/JSON/image tool context and cold reopen | SDK/original-inspection contracts; complete causal attribution is separate. |
| 3 Oversize/binary/browser results and originals | Budget/excerpt contracts; wider live integration payloads remain open. |
| 4 Stop/Steer across known boundaries | Typed/running-tool local proofs; voice playback explicitly deferred. |
| 5 Lost acknowledgment/disconnect/partial response | Native/GUI operation-identity and cold recovery proofs; no automatic unknown-action retry. |
| 6 Branch/Edit with memory and hidden tools | Live isolated memory cutoff plus native-history proofs; existing production-bank adoption remains open. |
| 7 Shared clients, memory pause/outage and spoken continuity | Shared-client and isolated memory proofs; Agent alignment pending, physical voice deferred. |
| 8 Search/MCP/desktop/browser and a bounded child | Selected live/fixture workflows; remaining services/integrations are explicit in the parity register. |
| 9 Long histories and stable inspection | Indexed/paged/context fixtures and original UI; representative breadth/performance remains open. |
| 10 Install/update/privacy/busy veto/recovery | Private installed MX/lifecycle proofs; public installer, broader services and later platforms remain open. |

## Next priorities

Finish the Agent shared-service qualification above while keeping the installed
reviews usable. Obtain the already-requested pilot feedback before transferring
more projects; explicitly excluded projects stay in DSH. Apply concrete reported
workflow fixes before optional backend expansion. The managed Office candidate
and public distribution have their own remaining gates.

Normal **bfe8dc94** CI has completed: Linux SDK passes; Debian ends with
**2,132 pass / one archived Fleet inspector failure / 53 skips**, before packaging.
The failed v2 case does not observe its nested child's pinned inspector. All three
Fleet cases pass in a focused local run without changes; that does not establish
the CI failure's cause or make the suite green. Mac SDK fails and Windows is
cancelled. No unchanged workflow was rerun or whole-workflow pass claimed. Physical
owner acceptance, full service parity and DSH retirement remain unproven; the
overall migration is active.
