<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Original DSH GUI on Pi

The owner's October 11 correction is to use the actual open-source DSH GUI before redesigning it. The standalone Harness default now bundles the original public React components and CSS. The previous custom interface is a supplementary **Full Pi record inspector** at `/inspection`, available from Settings. The native desktop and existing browser extension retain their approved interfaces.

## Selected public source

The selected baseline is public DeepSeek Harness **0.2.1-alpha.2**, commit [d743267388641bc76f17c45ce8b4c231aed1d32c](https://github.com/deepseek-ai/deepseek-harness/tree/d743267388641bc76f17c45ce8b4c231aed1d32c). [The selection record](../apps/harness/vendor/dsh/SOURCE.md) and machine-readable SOURCE.json identify **340 files**, their original public paths and SHA-256 hashes. This is public upstream source, not a historical private checkout or its Git history.

Copied components include AppFrame, SidebarRoot, conversation layout and composer, model chooser, chat renderers, the complete Trajectory table/timeline/detail presentation, workspace picker and directory browser, queue dock, goal bar, approval panel, question composer, shared controls, typography and themes. Their visual source and CSS remain upstream. InputBar has one nonvisual image-predicate import substitution; that predicate is selected verbatim from its public upstream service. The directory browser dictionary in the adapter derives from the same public English locale. The favicon is the original public asset. Augmentor branding and existing extension views occupy the original component slots.

The original DeepSeek MIT copyright/license, selected CosmoKit/Schemastery licenses and all bundled npm notices are retained. The browser bundle includes **95 npm package notice records**. These packages have their own licenses, including compatible non-MIT licenses; they are not all relabeled MIT. Separately authored glue retains Augmentor's own source license. The build verifies every selected source hash and rejects DSH client-runtime, Cordis owner, account/analytics modules, PostHog and Sentry from the compiled dependency graph.

The longer Augmentor name uses DSH's existing fallback-brand text class so it fits the fixed-height identity row. Composer labels omit the unconnected file-mention/slash hints. No original supplier styles are changed. All eight DSH contract/browser cases pass again after this binding-only adjustment.

UI build dependencies are exact locked workspace development dependencies. The pre-existing **126 production npm instances** retain their versions and integrities; production dependency files and their 709 existing license files remain unchanged in the ordinary assembly. The selected public Pi SDK remains **1.1.0**.

## Execution and data ownership

The copied GUI talks only to the existing local authenticated Harness HTTP API. DshPiController translates Host state into the public component props; DshPiProjection translates retained events and observations into DSH render data. It starts no DSH service, additional AgentSession or model loop. Each conversation continues to have one public-SDK Pi owner. Existing model routing, policy, execution, resources, memory, queue, approvals, questions and cancellation remain Host responsibilities.

The existing loopback authentication, origin check and conversation-scoped read-only links remain authoritative. A new private link arriving as same-document hash navigation reinitializes the browser controller, so an existing operator tab does not retain its prior scope. Read-only composers and model/actions are disabled; backend mutation denial remains independently enforced. The browser CSP permits inline **styles** for original DSH dynamic layout; scripts, connections and fonts stay local/self, and frames remain disabled. The synthetic browser test observes only its local Host origin and data URLs. That is scoped evidence, not a blanket claim about every optional provider/integration's network traffic.

The directory browser enumerates actual folders and directory symlinks, with bounded scanning and safe single-name folder creation. These are operator APIs and are excluded from read-only access; they are not model tools or a filesystem sandbox.

## Connected controls

| Original DSH presentation | Pi binding |
| --- | --- |
| Sidebar and workspaces | Existing conversation list, workspace grouping, search, new conversation, title rename and actual directory picker |
| Chat and composer | Retained/streaming Pi text, reasoning and tool output; identified Send, queue/steer and Stop |
| Model chooser | Exact configured provider/model and supported reasoning effort; no silent substitution |
| Trajectory | User/assistant/tool rows, timing, table/timeline and original tool detail pane with arguments, result and schema |
| Context meter | Actual reported input/cache usage against the recorded model's declared capacity; unknown counts remain unavailable |
| Queue dock | Remove, steer and atomic waiting-message edit with revision checks, FIFO and durable original admission identity |
| Goal bar, approval and question controls | Existing scoped Host goal transitions and exact interaction replies |
| Original modal and menu slots | Prompt library, draft improvement/Undo, request capture setting, reasoning/MCP management and advanced inspector |

The existing Augmentor Context, Plan, Goal and Jobs extensions occupy DSH's view slots. They remain accessible before the first message. Explicit Refresh controls avoid periodic refresh overwriting an in-progress editor draft. Full current-message Edit and the advanced originals/search controls remain available in the supplementary inspector.

Trajectory joins new assistant records to provider requests by **explicit retained request identity**. Independent sequence counters are never joined by ordinal. Old records without this identity still display their chat/tool evidence and are inspectable through Context; no old provider association is invented. Request inspection reads all retained payload pages using their recorded whole-body identity. Only actual captured system/developer messages and tool declarations appear; enabling capture affects future requests and cannot reconstruct old bodies.

Unknown submission responses are retained as unconfirmed and never automatically resent. Queue edits preserve the original admission fingerprint and append a replacement identity atomically at the same position; edits cannot rewrite already-dispatching, delivered or goal-owned work. Reopen preserves partial output after Stop.

## Remaining compatibility gaps

This is an original-GUI integration preview, not complete DSH backend parity. File-upload receipts, @-mention chips/autocomplete and the full slash-command catalog are not connected; use files already in the chosen workspace by path. Workspace rename/delete/reorder/archive/pin behavior and the complete original global settings/provider configuration are not connected. Unsupported operations report their missing binding.

Final assistant branching uses the original DSH branch control; current-message Edit remains in the advanced inspector. The original question/approval components answer Host requests, but DSH's indefinite/take-time timing protocol is not implemented: the existing Host's finite timeout still applies. Transient request streaming is not fully projected into Trajectory, although final retained request/tool details are connected. Account/telemetry and backend-only DSH plugins are intentionally excluded.

Live voice, embedded browser workflows, full memory/data migration, all live MCP services, desktop-specialist/Home acceptance and complete platform/installed migration remain separate requirements of the active Harness goal. The shared GUI adapter is platform-neutral, but this increment is qualified on MX Linux; further Windows/macOS/distro implementation remains deferred for owner feedback.

## Qualification

The focused source cohort initially reports **111 cases/106 passes/five failures**, all four Qt child failures plus their parent arising from system Python lacking QtTest. With the existing isolated QtTest interpreter, the full 49-case Host file passes unchanged. All other 62 cases pass in the source cohort. This covers original DSH rendering and interactions, local public-SDK model/tool execution, request correlation/paging, directory validation, queue restart/CAS/no-replay and existing Harness/Host regression controls. The final added empty-session view check is also run with the copied GUI.

Earlier browser preparation failures are retained: old advanced-inspector tests initially targeted the new default GUI and were updated to their explicit /inspection surface; the Trajectory detail wrapping contract and asset whitelist were corrected; the read-only same-document navigation check led to the fresh-link scope fix. The corrected tests keep their original assertions/deadlines. Synthetic interaction tests qualify component/Host contracts; they do not certify live third-party tools or voice.

Build/type checks and source-hash/dependency-graph/notice audits pass. The ordinary unselected assembly, using bundled Node **24.19.0** and the isolated QtTest interpreter, passes **77 cases across seven files**, zero failures/skips/cancellations: Host lifecycle, Pi observations, prompt queue, Harness server and the three new DSH suites. All **422 compiled files** match the source build. All **19,088 production dependency files**, 709 existing license files and bundled Node remain unchanged; all 151 pre-existing production/optional lock entries retain their versions/integrities (126 installed production package instances). The browser notice/source inventory is added separately.

Prior broad 834-case results in the MX guide belong to the preceding implementation and are not presented as a rerun of this GUI increment.

## Installed MX preview — October 11

Tested implementation: **fe5edae3c44c1905692afc3f63fe3688f7fb249e**. Final ordinary bundled-stage run after the original-brand-style adjustment again passes **77/77 cases**, zero skips/failures/cancellations. The selected and running private preview is **20261011-125858-2e384fa5**, product **0.2.13**, artifact SHA-256 **d1943d2f1cbae906f06d3277d22f90dc560bfb04105843a4ebec75b811d32899**. Both the observed Node entry and the native online/model-ready window match its selected immutable root. Full inventory verification passes after startup and a fresh local-model request. The qualification documentation commit following this implementation changes no runtime or installed artifact.

The actual installed original GUI uses the existing local Qwen3.8 27B 262k route. A fresh clean conversation reads the synthetic preview note, returns **infinity**, and has exactly one user admission, a tool-use assistant step and a successful final answer. Original Trajectory shows both explicitly linked requests and the read tool's arguments, saved result, effective schema and **six-millisecond** timing. Context shows the effective provider request, tool declarations and composition snapshots including **afterProviderHooks**. Final public-SDK usage is input 39, cache read 7,533 and output 44, against declared capacity 262,144; these are one request's reported values, not independent token measurement or a benchmark. The GUI is inspected at the 1440×1000 desktop breakpoint and the ordinary narrow in-app viewport; the longer brand fits using the original DSH text class.

On the first copied-GUI artifact bcc024f, live Stop interrupts visible Qwen streaming/partial reasoning and retains stopReason **aborted**, restores controls and leaves waiting prompts paused. Reopen and final-artifact adoption preserve exactly two user admissions/three provider requests in that interruption conversation; nothing is resent. The final binding-only follow-up keeps the same controller/Host/Stop bytes. A separate clean final-artifact conversation is left for owner feedback.

During first adoption an extra preparatory shutdown call made the following shutdown request fail closed because the owner was already quiescing. The confirmed idle, same-user socket peer with the expected old preview entry is observed through a pidfd and finishes its normal SIGTERM handler; no selected artifact is patched. Final adoption uses the idle native maintenance close followed directly by guarded Host shutdown and succeeds normally. Previous releases remain available. Production selection SHA-256 **cb426b4a2daa960f66533f28fb2b164385c243c1ba53fc18e61ca33fb4256be7** and the existing model-router process remain unchanged; no model/speech/GPU configuration is changed.
