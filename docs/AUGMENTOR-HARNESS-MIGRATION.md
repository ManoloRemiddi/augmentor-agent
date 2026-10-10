<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor Harness migration to Pi

Status on 10 October 2026: the owner accepted the direction of moving Augmentor's primary conversational engine from DeepSeek Harness to Pi, retaining useful DSH features through supported Pi extensions and selected source reuse. The owner subsequently authorized implementation. This remains the full migration specification; [the implementation record](AUGMENTOR-HARNESS.md) tracks the isolated source candidate and outstanding gates. Installed applications and existing conversations have not been migrated.

Augmentor Harness will combine Pi's coding-agent session lifecycle, Augmentor's existing services, and an inspection interface adapted from useful MIT-licensed components. Desktop and Browser keep their established presentation and share that runtime. The central requirement is to preserve what makes DSH valuable: visible execution, inspectable effective context, original evidence, explicit model settings and reliable interruption and recovery.

The motivations are reduced dependence on a preview harness, preference for Pi's European roots, and control over telemetry across updates. These become release requirements rather than assumptions about an upstream brand or version number. DSH remains available until replacement workflows qualify. This extends the [accepted composable architecture](COMPOSABLE-AUGMENTOR-PROPOSAL.md); it does not create another application repository or conversational loop.

## Decisions and boundaries

| Decision | Direction |
| --- | --- |
| Conversational engine | Use the supported Pi coding-agent SDK and SessionManager as the sole owner of each Pi conversation. |
| Product | Keep one canonical Augmentor repository, native Qt surface, Chromium surface and shared services. Augmentor Harness is the product's harness and inspection interface. |
| DSH reuse | Extract selected public MIT source and adapt its presentation to an Augmentor observation contract. Keep original notices and record provenance. |
| GUI | Start with Trajectory and context inspection as shared views. A fuller DSH-derived web shell can follow if it earns its dependency and maintenance cost. |
| Privacy | Disable unsolicited analytics and install reporting in managed operation; maintain an explicit inventory of network destinations and private local records. |
| Existing history | Preserve original DSH sessions and their compatible reader. Do not claim that a copied visible transcript is an exact Pi resume. |
| Other integrations | Preserve Home, mobile, embedded application profiles, Handy, and other harness adapters. Their dependencies have independent cutover gates. |
| Delivery | Qualify isolated source and installed artifacts before activation. Reconcile this older dirty checkout with current canonical source before implementation. |

No application loop will be transplanted from DSH. Pi performs model execution, tool sequencing, cancellation, compaction and session branching. Augmentor supplies policy, tools, services and presentation through supported hooks. The initial design excludes Pi Durable because its documented experimental lifecycle would add another stability dependency.

European project roots support the ecosystem preference. They do not establish exclusive European ownership, legal jurisdiction or data residence. Model endpoints, memory infrastructure, speech services and optional web tools determine where data goes. Pi is now associated with Earendil; jurisdiction and provider placement must be assessed separately if European operation is a product requirement. See [Pi](https://pi.dev/) and [Earendil](https://earendil.com/).

## Source and compatibility baselines

The source checkout used for the initial analysis is `f353c52b060a5b762da70b862d88a6434329ab6b`, with pre-existing modifications. Its recorded `origin/main` is `79784a5687b73234b9524e7a48e91f01306f73c9`, 331 commits ahead. The newer architecture, feature matrix, context budget, task reliability and DSH compatibility records were inspected without resetting or merging the checkout. Neither ref establishes the owner's current running bytes.

| Component | Baseline | Meaning for this migration |
| --- | --- | --- |
| Augmentor Pi SDK | Coding-agent, agent-core and AI 0.85.1 | Existing locked integration, not the new extension compatibility target. |
| Pi candidate | Published 1.1.0; upstream main `42a3497d03ad17e308a2299fa824727894f2c0ec` | Candidate for isolated qualification. Main may contain changes beyond the published release. Do not replace current pins merely from inspection. |
| DSH installer | 0.1.5-rc.1 | Complete-install baseline retains its own qualification. |
| Newer Linux DSH integration | Locally patched 0.2.0-rc.2 | Current remote documentation records a history bridge and separate installed evidence. Preserve the matching reader and original history. |
| DSH source for GUI extraction | `d743267388641bc76f17c45ce8b4c231aed1d32c`, manifest 0.2.1-alpha.2 | Public MIT source inspected for reusable UI; not a qualified Augmentor runtime. |

The [source inventory](SOURCES.md), [feature matrix](FEATURE-MATRIX.md) and [deployment guide](DESKTOP-DEPLOYMENTS.md) govern existing evidence. The newer [DSH compatibility record](https://github.com/ManoloRemiddi/augmentor-agent/blob/79784a5687b73234b9524e7a48e91f01306f73c9/docs/DSH-0.2-COMPATIBILITY.md) distinguishes the patched Linux runtime from customer installer locks. Future implementation must select and record a reconciled canonical ref, exact published packages, full dependency locks and actual loaded components.

## Comparison for the Augmentor use case

Scores are architectural judgments from 1, weak or absent, to 5, strong fit. They measure fit for Augmentor, not model intelligence or benchmark performance. DSH includes its relevant plugins. Pi core means the upstream coding-agent experience; Pi expanded includes identified extension candidates and Augmentor bindings, which still require qualification. The expanded scores describe feasible coverage rather than installed parity. A score of 5 does not remove a release gate.

| Capability | DSH | Pi core | Pi expanded | Reason and remaining difference |
| --- | ---: | ---: | ---: | --- |
| Standard chat and coding tools | 5 | 5 | 5 | Both support model execution and tool work; Pi's small default tool surface is deliberate. |
| Desktop GUI | 5 | 1 | 4 | Pi's main interface is terminal based; reusable web interfaces exist, but Augmentor must own packaging and integration. |
| Browser GUI | 5 | 1 | 4 | Pi has SDK/RPC integration and community web UIs; neither automatically becomes our Chromium product. |
| Trajectory and timing inspection | 5 | 2 | 4 | DSH has an integrated ledger and timeline. Pi trajectory and inspector packages provide useful foundations with compatibility gaps. |
| Effective context inspection | 5 | 2 | 4 | DSH headers and Context views expose rich composition. Pi provider hooks can support equivalent inspection once final payload capture qualifies. |
| Raw tool arguments and results | 5 | 4 | 5 | Pi retains structured session information; our current display adapter omits some of it. |
| History and branching | 5 | 5 | 5 | Both have durable native histories; formats and exact resume semantics differ. |
| Compaction and retained originals | 5 | 5 | 5 | Pi supports compaction and context edits. Augmentor's early tool budgets and excerpt recovery need a Pi binding. |
| Prompt templates and skills | 5 | 5 | 5 | Pi supports these resources; our restricted resource loader must admit only the approved composition. |
| Model and provider choice | 5 | 5 | 5 | Pi supports broad providers and custom/virtual models. Preserve Augmentor curation and actual request settings. |
| Adaptive reasoning | 5 | 3 | 5 | Pi thinking levels and routing hooks are foundations; our Adaptive Reasoning policy needs a port and visible effective settings. |
| MCP tools and resources | 5 | 4 | 5 | Current Pi supports MCP, including OAuth. SDK hosts must load and bind the built-in extensions explicitly. |
| Planning, todos and goals | 5 | 2 | 4 | Pi examples/extensions can provide these; persistent Augmentor semantics need explicit ownership and evidence. |
| Subagents and background jobs | 5 | 2 | 4 | Pi extension options exist. Child ownership, Stop, uncertainty and usage accounting must qualify. |
| Automatic relationship and work memory | 4 | 1 | 4 | Both need our Hindsight lifecycle binding; long-term memory is not equivalent to session history. |
| Voice and hands-free interaction | 4 | 1 | 4 | Existing Resonant Voice is reusable, but Pi transport, lifecycle and physical audio parity are open. |
| Browser and desktop actions | 4 | 2 | 4 | Existing executors can be retained with scoped Pi registrations and OS-specific qualification. |
| Prompt queue and responsive steering | 5 | 4 | 4 | Pi offers steer/follow-up; our DSH adapter interrupts obsolete generation more promptly and requires separate parity work. |
| Bounded action-aware recovery | 4 | 2 | 4 | Pi retries alone do not preserve our duplicate-action and unknown-outcome rules. |
| Permission policy and isolation | 4 | 2 | 4 | Augmentor policy can be retained. Neither a plugin nor project trust supplies an OS sandbox. |
| Extension architecture | 5 | 5 | 5 | Both are extensible. Pi exposes host hooks well suited to retaining product-owned behavior. |
| Control over unsolicited telemetry | 2 | 3 | 5 | Pi also has default install reporting. A managed, tested policy is needed on either engine. |
| Release stability and upgrade burden | 2 | 4 | 3 | DSH remains preview. Pi's versioned core is a better candidate, but community extensions and a GUI fork add maintenance. |
| European ecosystem preference | 2 | 4 | 4 | Pi's European roots fit the preference; a score does not certify European jurisdiction or data sovereignty. |

Pi's missing first-party GUI is an integration opportunity, not a need to recreate its agent engine. Its extension architecture makes the migration feasible. DSH's integrated transparency and existing Augmentor behavior remain the baseline to beat; buying those back through extensions is a substantial part of the work.

## Where DSH transparency lives today

In the inspected upstream DSH source, the context occupancy ring is below the input card, after session statistics. Clicking it opens a token breakdown; it is hidden until usage and capacity are available. Trajectory is a conversation view; turning Coding Tools off hides it, and the view tab bar disappears when fewer than two views remain. These conditions can make an existing feature appear to have been removed. See the pinned [conversation shell documentation](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/client/ui-conversation/README.md).

The separate [dsh-context plugin](https://github.com/bowenliang123/dsh-context), inspected at 0.48.0, provides richer composition categories, request trends and full context browsing through its Context view and `/context` interface. It could explain the remembered richer interface; the exact historical installed view has not been identified. Its Apache-2.0 license differs from the requested MIT source-selection preference. The MIT DSH occupancy/Trajectory components remain the default reuse candidates; copying dsh-context requires a separate licensing decision.

## Required feature parity

P0 means required before making Pi the default for the affected existing workflow. P1 means required before removing that DSH dependency. P2 means an optional enhancement. A workflow can move individually; an unmet gate remains visible and keeps its matching DSH path available.

| Priority | Feature and current owner | Pi migration approach | Acceptance outcome |
| --- | --- | --- | --- |
| P0 | Model setup, picker and Adaptive Reasoning | Preserve provider settings and curated models; bind policy to supported Pi request/routing hooks. | Saved versus effective model, route and effort are visible; no silent fallback or reduction of local model settings. |
| P0 | Chat, reasoning, Stop and progress | Expand the current runtime event binding and both renderers. | Reasoning supplied by the provider streams visibly; Stop cancels generation and reports pending tool disposition; progress labels reflect observed events. |
| P0 | Trajectory and context | Adapt selected DSH views to the observation contract below. | A user can inspect each request, its effective input, tools, results, compaction, timings and interrupted output after reopening. |
| P0 | Prompt Library, templates and instruction composition | Retain the shared prompt service and compose selected Pi resources explicitly. | Native and Browser edit one library; revisions and historical submitted prompts remain stable. |
| P0 | History, edit and branch | Retain Pi SessionManager and the existing exact-context product contract. | Branches include real prior tool context without rerunning it; parents stay unchanged and newer memory is not injected into a historical boundary. |
| P0 | Queue, follow-up and responsive steering | Add product queue semantics around the Pi session lifecycle; qualify cancellation boundaries. | A correction does not wait through unnecessary obsolete generation; in-flight tools settle or cancel with an honest outcome. |
| P0 | Tool budgets and original evidence | Port shared deterministic policy through Pi context edits and a session-scoped excerpt tool. | Effective results are bounded, images remain usable, originals remain readable and cold history needs no action replay. |
| P0 | Action-aware execution and recovery | Port the current action ledger and bounded continuation policy through SDK hooks. | Duplicate changes, background and uncertain outcomes are guarded; empty replies produce a truthful incomplete status. |
| P0 | Browser and consented desktop execution | Keep existing executors and explicit surface capabilities. | Tools affect only authorized targets; browser-only sessions receive no general desktop authority. |
| P0 | Privacy, reconnect and private state | Keep managed settings, explicit extension composition and authenticated local transports. | No unsolicited reporting; reconnect reconciles recorded operations without replaying an unknown outcome. |
| P1 | Automatic relationship and project memory | Reuse Hindsight and the transcript journal; qualify Pi retrieval/insertion and durable capture. | Correct person/project banks, pause controls, budgets and provenance survive restart and branches. Memory outage does not prevent ordinary chat. |
| P1 | Resonant Voice and hands-free | Adapt the existing versioned speech protocol to the Pi owner. | Hold/release, lock, speech selection, interruption and typed/spoken continuity pass through the real interfaces and audio path. |
| P1 | Wiki Skills, Wiki Tools and Metafolder | Preserve useful catalog/file workflows using approved resources and registered tools. | The selected workflow works end to end; merely seeing a package or catalog entry is insufficient. |
| P1 | Free Web Search and existing MCP servers | Reuse or adapt search; explicitly configure Pi MCP/codemode/tool search. | Search returns inspectable sources; Playwright, Comfy, Blender and Unreal pass representative operations when their services are available. |
| P1 | Planning, todos, goals, jobs and delegation | Prefer official extension examples or MIT candidates; retain product policy and persistence. | Parent/child authority, limits, Stop, durable status and one-time usage totals qualify; absent capabilities remain unavailable. |
| P1 | Home and embedded application profiles | Add scoped Pi adapters only after their current contracts are inventoried. | Home Assistant remains device owner; role/tools/memory and app-operation identity stay isolated. DSH is not removed while these depend on it. |
| P1 | Packaging, updates, multi-window and mobile | Use existing product manifests, platform launch adapters and managed release selection. | Source, selected and running builds are identifiable; drafts and active work block unsafe activation; rollback preserves new Pi history. |
| P2 | Full DSH-derived web shell and deeper diagnostics | Grow the same inspection interface after core parity. | It remains a client of the single host, with measurable benefit over the existing views. |

The newer canonical source contains [tool context budgeting](https://github.com/ManoloRemiddi/augmentor-agent/blob/79784a5687b73234b9524e7a48e91f01306f73c9/docs/CONTEXT-BUDGET.md) and [task reliability corrections](https://github.com/ManoloRemiddi/augmentor-agent/blob/79784a5687b73234b9524e7a48e91f01306f73c9/docs/TASK-RELIABILITY.md). Preserve binary-result notices, session-scoped original-result recovery, advisory reassessment and bounded fresh browser observations. These policies are not proofs of semantic task completion. The [existing execution design review](TASK-EXECUTION-DESIGN-REVIEW.md) continues to govern any broader task-verification experiment.

## Runtime and interface ownership

| Layer | Owns | Does not own |
| --- | --- | --- |
| Pi coding-agent session | Actual conversation tree, model/tool lifecycle, compaction and branch state | Product windows, prompt database or relationship identity |
| Augmentor Pi adapter | Approved resource composition, tool registration, policy bindings, capability negotiation and observations | A second agent loop or an inferred substitute for Pi session state |
| Shared Augmentor services | Prompts, memory journals/banks, speech, browser/desktop execution, lifecycle and support | Independent conversational agents |
| Observation store | Private diagnostic events, payload snapshots and indexes referring to real session/operation identities | Authority to resume a model call or execute an action |
| Native, Browser and Harness views | User input, accessible chat rendering and inspection of read models | Credential storage, model execution or autonomous background installs |

`packages/runtime` and `packages/pi-linux` remain the Pi integration boundary. Existing source owners in [current architecture](ARCHITECTURE.md) remain authoritative. Shared diagnostic types and pure projections can be separated from Pi-specific translation; exact new package names should be chosen during implementation rather than imposing a second service for each concern.

The DSH Trajectory package is largely browser presentation, but it consumes DSH session bindings, projection definitions, conversation registries and slots. It cannot be switched to Pi by renaming an endpoint. Extract useful ledger, inspector, attachment and timeline components, then adapt their data boundary. Retaining limited MIT presentation utilities is acceptable; carrying the complete DSH session/backend runtime would keep the dependency this migration aims to remove. See the pinned [Trajectory source and contract](https://github.com/deepseek-ai/deepseek-harness/tree/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/client/ui-trajectory).

## Observation contract

The proposed contract is `augmentor-observation/1`. It supplements the existing [Pi client protocol](PROTOCOL.md) with inspectable records; it does not replace Pi's durable session state. Capability negotiation must distinguish metadata inspection, full text payload inspection, attachments, raw provider events and historical coverage. Unsupported or expired data is shown as unavailable rather than synthesized from the transcript.

### Required records

| Record | Required information |
| --- | --- |
| Identity and provenance | Product/adapter/package versions, session and branch IDs, parent branch, request/attempt/turn/tool/operation correlations, surface, role and authorized workspace/profile. |
| Ordering | Stable event ID, ordered journal position, producer identity and source position when available; wall time and monotonic durations where valid. Reconnect deduplicates by identity. |
| Request configuration | Selected model/effort, actual routed model/provider/effort, endpoint classification, reason for routing or recovery and relevant generation settings. |
| Effective context | Final system content, ordered messages and content blocks, effective tool schemas, attachments and exact transformation boundaries. Record both source provenance and what was omitted or replaced. |
| Model response | Available reasoning and answer blocks, interruption/finish/error state, provider usage, cache usage and latency observations. Reasoning means content exposed by the provider, not hidden internal reasoning. |
| Tool execution | Tool name, structured arguments, authorization decision, executor/target, start, result blocks, error classification, side-effect receipt and outcome uncertainty. |
| Context changes | Memory/skill/prompt contributions, pruning, binary omissions, compaction summaries, original evidence references and branch/context edits. |
| Queue and control | Submission acknowledgment, queue identity, steer/follow-up intent, claimed boundary, Stop request and resulting generation/tool state. |
| Delegation and jobs | Parent/child IDs, scope, job lifecycle, cancellation disposition and usage ownership; no duplicated child totals. |
| Coverage and retention | Source capability, missing/expired/truncated records, payload-capture mode, redactions and attachment availability. |

Local ordering represents recorded observations. It must not imply a global causal order across asynchronous child processes. A request completing is distinct from a tool completing, a turn completing and a user task being verified. Keep these states separate in both the ledger and UI labels.

### Capture boundaries

Pi's session subscription supplies lifecycle and message events. The inspected newer SDK also exposes context transformations, provider request/header hooks, response notifications and parsed provider-stream events. Parsed stream events are not necessarily HTTP bytes and are not automatically persisted. See the pinned [extension types](https://github.com/earendil-works/pi/blob/42a3497d03ad17e308a2299fa824727894f2c0ec/packages/coding-agent/src/core/extensions/types.ts) and [SDK request binding](https://github.com/earendil-works/pi/blob/42a3497d03ad17e308a2299fa824727894f2c0ec/packages/coding-agent/src/core/sdk.ts).

An ordinary early context hook is insufficient for the label “sent to the model”: another extension or provider serializer may still modify its contents. Qualification must establish a supported observation point after all permitted payload transformations, identify the final physical model, and compare the captured object with a synthetic provider's received request. If only a pre-serialization object is available, label its boundary accurately. Do not intercept authorization values or claim exact network bytes from a parsed event.

Transformations must preserve provenance without converting retrieved content into instructions with new authority. Capture which memory, skill, prompt and tool policy contributed to a request, with their versions and effective text. A resource discovered on disk is not evidence that the model received it.

### Current adapter changes required

Both the local and recorded remote [Pi host](../packages/runtime/src/host.ts) suppress reasoning-delta text in the display feed, omit tool arguments at tool start, and replace image results in that feed with a text notice. Session creation sets thinking to off, and resource discovery is deliberately restricted. These are Augmentor adapter boundaries; they do not establish that Pi's underlying session file discarded the original content.

The replacement must preserve available reasoning, arguments and authorized attachment references in the inspection path; expose effective thinking policy; and explicitly register approved extensions, skills and context resources. At the analysis baseline the host rejected concurrent submission. The [October 10 candidate](AUGMENTOR-HARNESS.md) now binds durable waiting inputs and identified responsive correction around the SDK session. Synthetic generation/preparation/tool/Stop/crash contracts and correction-specific public SDK input handlers, transformed images and approved skill/template expansion pass. Original submissions remain distinct from prepared SDK context. Its loaded Linux Chromium extension now passes real composer, Steer/Remove, reload, Stop/resume and branch/edit workflows with a synthetic provider. Representative live providers, other OS/browser installations, full prompt/command controls and installed/platform acceptance remain required; the complete queue/steering gate is open. Keep the display/recovery journal separate from Pi's true model context and test both after cold reopen.

The [Harness Branch/Edit source slice](AUGMENTOR-HARNESS.md#harness-branchedit-controls-and-steering-history) adds actual web controls, verifies native tool-context prefixes and unchanged parents, and aligns steered-input editing with earlier messages in the same host turn. Inherited display receipts preserve their originating conversation rather than confirming a child's new prompt. This qualifies the isolated Harness workflow, not Native end-to-end branching, live Hindsight cutoff, old-history migration or other OS/installed acceptance. Every accepted P0/P1 requirement above remains binding; DSH stays available for unqualified workflows.

### Inspection behavior

Trajectory must show turns, requests and attempts, tool inputs/results, partial interrupted answers, context changes and measured timing. It must support stable selection, raw/text inspection, copying original arguments, attachment inspection, search with a stated coverage scope, and large-history paging/virtualization. Loading older records must not reset the selected record or force the view to the live tail.

Context inspection must show the selected request's effective system prompt, messages, tool schemas and memory/skill contributions, plus before/after compaction or pruning. Token totals distinguish provider-reported usage from local estimates; capacity and usage must refer to the same selected model/request. Missing pricing, usage or timestamps remain unknown rather than zero. Diff views compare defined request boundaries and label provider-specific conversions.

The established Desktop and Browser layout stays the baseline. Implementing an inspection surface should not silently redesign their composer, shortcuts or voice controls. The new Augmentor Harness view can evolve separately while consuming the same host and honoring the profile's permissions.

## Privacy and network policy

DSH's inspected telemetry plugin defaults to feedback-only export, and its official desktop has a separate analytics path. Disabling one is insufficient. Pi also defaults to install reporting, while its separate experimental analytics setting defaults off. Our existing Pi host already disables install telemetry. A new Pi pin must preserve and verify that behavior. See [DSH telemetry](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/session/session-telemetry-otel/README.md) and [Pi settings](https://github.com/earendil-works/pi/blob/42a3497d03ad17e308a2299fa824727894f2c0ec/packages/coding-agent/docs/settings.md).

Managed operation must enforce these requirements:

- Disable install reporting, product analytics and telemetry exporters explicitly. Local diagnostic events are private observations, not permission to upload.
- Maintain a destination inventory separating selected model inference, configured memory/speech, requested web/MCP tools, update checks and optional diagnostics. Report unexpected destinations during qualification.
- Preserve opt-outs through every fresh install and upgrade. An updated package must not activate new network behavior through a changed default or newly loaded plugin.
- Load only reviewed, pinned extensions in managed profiles. Extensions run code with the host's OS privileges; project trust is resource-loading policy, not isolation. See [Pi's security boundaries](https://github.com/earendil-works/pi/blob/42a3497d03ad17e308a2299fa824727894f2c0ec/packages/coding-agent/docs/security.md).
- Serve inspection through authenticated, profile-scoped local transport. Loopback binding alone is insufficient; reject unrelated origins/clients and avoid loading third-party scripts or fonts in inspection pages.
- Keep credentials and authorization headers out of observation records. Payloads can still contain secrets supplied as content; show this retention consequence when enabling full payload history.
- Keep support exports explicit, scoped and previewable. Export metadata by default; including private prompts, tool content or images is a separate user choice.

Proposed local retention defaults are metadata inspection enabled, full diagnostic payload history opt-in, and a 14-day/512-MiB maximum for the additional observation store, whichever expires first. Original Pi conversation storage keeps its separate product retention policy. Payload inspection must say when historic payloads were not captured; enabling capture later cannot reconstruct earlier requests exactly. Current-session inspection can use available in-memory context, labeled by its capture boundary.

Attachment content should use authorized durable references with availability checks; avoid an unbounded second copy of screenshots. A missing or expired attachment must remain visibly missing. Turning diagnostic capture off or clearing its store does not delete Pi session history, shared memory journals or speech records. Deletion/export must name the affected stores and follow [data and support](DATA-AND-SUPPORT.md). Retention limits are initial design defaults to validate with large histories and actual attachment sizes.

Qualify cold start, ordinary chat, feedback, extension startup, update checks and upgrades with a synthetic model and recorded network observations. Required model/tool traffic is expected; unsolicited analytics/install export is a failure. An environment variable that suppresses startup traffic is not a general firewall. Optional community packages require the same audit regardless of their privacy claims.

## Reuse and extension shortlist

These packages are candidates, not an installation manifest. Exact release contents, transitive dependencies, peer ranges, lifecycle behavior and licenses must qualify before inclusion. Official Pi extension examples are a useful smaller starting point when a large third-party package would add a second host or broad authority.

| Candidate | Inspected version and license | Proposed use and qualification |
| --- | --- | --- |
| [Pi coding-agent](https://github.com/earendil-works/pi) | 1.1.0 candidate; MIT repository | Session owner. Pin a published compatible family, not arbitrary main or mixed package scopes. |
| [DSH Trajectory](https://github.com/deepseek-ai/deepseek-harness/tree/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/client/ui-trajectory) | Source revision above; MIT repository | Preferred ledger/inspector/timeline reuse. Enumerate its actual presentation dependency closure and replace DSH data bindings. |
| [DSH conversation UI](https://github.com/deepseek-ai/deepseek-harness/tree/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/client/ui-conversation) | Source revision above; MIT repository | Occupancy display, attachment and shell utilities where useful. Full shell is optional after the first views. |
| [UniPi trajectory](https://github.com/Neuron-Mr-White/unipi/tree/main/packages/trajectory) | `@pi-unipi/trajectory` 2.20.5; MIT | Useful context/timing capture reference. Its inspected Pi peer range is `^0.84.0`, outside 1.1.0; no drop-in compatibility claim. |
| [Pi session inspector](https://github.com/twKrash/pi-session-inspector) | 1.5.3; MIT | Metrics and session ledger reference. It excludes sensitive payload content from its metrics log, so it does not replace full context inspection. |
| [Pi web UI](https://github.com/xing-shuyin/pi-web-ui) | 0.101.0; MIT | Alternative UI/component source. Evaluate its server architecture before reusing it; do not add an independent owner for the same conversation. |
| [Pi subagents](https://github.com/nicobailon/pi-subagents) | 0.77.0; MIT | Candidate for children/jobs. Its inspected AI peer requires at least 0.86.1; it does not fit the existing 0.85.1 lock. |
| [Official Pi extension examples](https://github.com/earendil-works/pi/tree/42a3497d03ad17e308a2299fa824727894f2c0ec/packages/coding-agent/examples/extensions) | MIT repository | Planning, todos, permission and compaction foundations; select individual examples and audit their dependencies. |
| [DSH Context](https://github.com/bowenliang123/dsh-context) | 0.48.0; Apache-2.0 | Functional reference for a rich context explorer. Direct copying is outside the default MIT source-selection decision. |
| [Pi Durable](https://github.com/earendil-works/pi/tree/42a3497d03ad17e308a2299fa824727894f2c0ec/packages/durable) | Experimental upstream package | Defer. It is a distinct harness/lifecycle with documented API instability. |

Native MCP is now available in the candidate Pi SDK, but CLI defaults do not automatically apply to SDK sessions. The host must explicitly add the MCP, codemode and tool-search extension factories, configure their tool exposure and bind the session lifecycle. An upgrade alone leaves our restricted loader without those capabilities. See the pinned [SDK guidance](https://github.com/earendil-works/pi/blob/42a3497d03ad17e308a2299fa824727894f2c0ec/packages/coding-agent/docs/sdk.md).

Prefer the shared Prompt Library, Hindsight, Resonant Voice and existing browser/desktop services over replacing them with new community equivalents. Model Picker and Adaptive Reasoning need Pi-specific bindings, not duplicate stores. Plugin migration inventory must include active versus disabled status, owned configuration and a representative workflow; a failed Metafolder read or unavailable Comfy service is a qualification gap, not proof that an equivalent tool works.

## Licensing and attribution

The pinned [DSH MIT license](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/LICENSE) and [Pi MIT license](https://github.com/earendil-works/pi/blob/42a3497d03ad17e308a2299fa824727894f2c0ec/LICENSE) permit source reuse subject to their notice requirements. Copied files must retain copyright and license text; an attribution manifest should record source repository, exact commit, file paths, modifications and bundled dependencies. Audit assets, fonts, samples and dependencies individually. A root MIT license does not make every dependency MIT, confer trademark rights or grant publication permission for private project source.

“Augmentor Harness” is distinct product branding. Remove inherited upstream identity, telemetry endpoints and assumptions about DSH's official desktop distribution from copied presentation code. Preserve acknowledgments separately from product naming.

The current [Augmentor licensing decision](LICENSING.md) uses MIT with the Augmentor Resale Restriction for Augmentor-authored source; it is not unrestricted MIT or an OSI open-source license. This migration does not silently change that decision. Third-party MIT components retain their original rights and notices. If the intended deliverable must itself be entirely unrestricted MIT, resolve the Augmentor-authored license separately before publication. Qt and existing non-MIT dependencies also retain their obligations.

Apache-2.0 is permissive but distinct from MIT. Keep dsh-context as a reference unless the owner selects that license for a copied component. A literal all-dependencies-MIT rule would also require reviewing existing Qt and other dependency choices; the present proposal selects MIT upstream code for new reuse while preserving existing declared licenses. Legal distribution review must use the exact files and dependency closure actually selected.

## History migration and rollback

Existing DSH chats remain DSH-owned. Preserve their logs, attachments, model/provider settings and a matching read path, including the locally qualified 0.2 history bridge where required. Start new Pi chats separately. Shared prompt and memory services continue through stable person/project bindings without converting one harness's history into another's.

An optional later context handoff may create a new Pi conversation from explicitly selected DSH content. It must identify omissions, changed tool/model schemas, unavailable attachments and its origin. It cannot claim exact resume, replay completed tools or overwrite the original conversation. Exact historical conversion requires a separate compatibility design and evidence.

Rollout must be reversible per workflow. Retain the old installed release and configuration, block activation while drafts, tools, speech or shared-host work are active, and use the [managed deployment transaction](DESKTOP-DEPLOYMENTS.md). Keep new Pi sessions when rolling back the default engine; older DSH software must never reinterpret them. Selecting a prior desktop artifact does not automatically roll back externally mounted presets or speech/memory services, so the recorded component graph must include those owners.

## Delivery phases and acceptance gates

| Phase | Work | Exit gate |
| --- | --- | --- |
| 0 Source reconciliation and baseline | Preserve dirty source; reconcile selected public changes with current canonical main; inventory loaded product/harness/plugins and required workflows. | Reviewed canonical ref, exact component identities and explicit source/installed evidence; no private history or configuration in public fixtures. |
| 1 Pi lifecycle qualification | Test the published Pi candidate in isolated state, preserving explicit model settings and existing product protocols. | Chat, streaming, Stop, history, exact branch/edit, approvals and reconnect pass without replay. Record pin/lock and compatibility in SOURCES. |
| 2 Observation capture | Bind request, context, model, tool, compaction and cancellation events; implement private coverage/retention semantics. | Synthetic received requests match the claimed capture boundary; interrupted output, arguments, results and original evidence survive cold reopen. |
| 3 Trajectory and context views | Adapt selected MIT presentation components for shared read models and both product surfaces. | Real controls inspect current and historical requests; large sessions page reliably; copying, attachments and missing-data states are correct. |
| 4 Behavior and service parity | Port context budgets, execution recovery, responsive queues, memory, reasoning policy, tools and voice in small qualified slices. | All required workflows have fixture and applicable live evidence; no duplicate mutations, invisible effective settings or reduced context/model configuration. |
| 5 Platform and update qualification | Build matched artifacts from one reviewed ref; verify private transport, multi-window/mobile, packaging, upgrades and opt-out persistence. | Relevant Linux/macOS/Windows and Browser installed gates pass with selected/running identities and a preserved rollback path. |
| 6 Default transition | Make Pi the default only for qualified new conversations and roles. | Existing DSH history remains readable; active conversations/drafts survive; remaining DSH dependencies are explicit. |
| 7 DSH retirement | Remove runtime dependencies individually after Home, embedded profiles and remaining tools migrate. | No required workflow depends on DSH execution; archive reader/history and licensing notices remain; rollback/data policy is documented. |

Phases 2 and 3 form the first useful Augmentor Harness slice after SDK qualification: inspect a typed Pi conversation with a real model request, one tool result, cancellation and a reopened session. Voice or delegation is not needed to prove that slice, but it is needed before retiring the DSH workflows that use it. Do not combine the core upgrade, GUI extraction, every extension and the installed cutover into one change.

### Required qualification scenarios

1. Chat with the selected real provider; compare selected and effective model/effort and verify streamed reasoning when exposed. Keep Qwen/Breeze placement and context/concurrency/precision unchanged.
2. A synthetic tool returns text, an error, JSON and an image. Inspect original arguments/results and the actual next provider context, then reopen the same session in a fresh process.
3. Oversized, binary-like and fresh browser results exercise trimming/omission policies and session-scoped excerpts. Originals remain available without inference or replay.
4. Stop during generation, during a tool and during voice playback; then steer and follow up at known boundaries. Record whether actions completed, cancelled or became uncertain.
5. Disconnect after an action acknowledgment is lost and restart after a partial model response. Reconcile operation identities; never repeat an unknown mutation automatically.
6. Edit/branch after a completed tool turn with selected memory. Verify parent preservation, hidden tool context, no new memory at the historical boundary and unchanged tool execution counts.
7. Exercise both shared prompt clients, memory pause/outage and typed/spoken continuation. Qualify acoustic behavior separately from deterministic speech transport fixtures.
8. Run representative configured search/MCP/desktop/browser workflows and a bounded child job. Verify scopes, authorization, Stop propagation and usage counted once.
9. Inspect long histories with paging, scrolling and changing the selected request. Unknown usage/pricing and expired payloads stay visibly unknown.
10. Fresh install and staged upgrade exercise telemetry opt-outs, network destinations, dependency compatibility, busy-work veto and recovery. Verify the actual installed UI and recorded running build.

Record source ref, package hashes, OS, surface, harness, profile, selected model and evidence type for each gate. Synthetic provider/Qt/DOM tests establish contract behavior; live model, physical audio/display and installed lifecycle evidence establish different claims. Passing one does not imply the others. Run checks appropriate to each slice; do not use an unrelated passing test count as parity evidence.

## Risks and decisions still to qualify

| Risk | Response |
| --- | --- |
| Extension ecosystem lags the chosen Pi release | Select a small compatible set; pin exact versions; port selected MIT code when its maintenance cost is lower than carrying an incompatible package. |
| Full DSH frontend extraction pulls in its backend | Measure the component dependency closure during the first view port. Keep only required presentation contracts. |
| Early capture presents an inaccurate context | Verify final request ordering against a synthetic provider; label any remaining boundary limitations. |
| More transparent logs increase private data retention | Separate diagnostic capture from conversation storage, bound it, expose missing coverage and keep support exports explicit. |
| Steering/retry changes duplicate actions or alter expectations | Preserve operation identities and outcome classification; qualify interrupted generation and tool boundaries separately. |
| A newer checkout or installed overlay contains behavior missed by the initial analysis | Reconcile source before implementation and inventory actual mounted dependencies before cutover. |
| “European” is treated as an infrastructure guarantee | Record ownership/jurisdiction requirements and configure actual model/memory/speech regions explicitly. |
| License language promises unrestricted MIT incorrectly | Preserve current product license and original upstream notices; resolve any change of product license as its own decision. |

The remaining implementation choices are the exact qualified Pi release, the smallest reusable DSH UI dependency set, compatible extension releases, and whether an Apache-licensed context component or an unrestricted MIT product license is desired. They do not prevent the initial Pi observation/Trajectory slice. The migration is complete only when required workflows qualify and DSH execution dependencies are retired; documenting or installing candidate extensions is not completion.
