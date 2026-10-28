<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->
# Bounded desktop specialist

Current source integration, 2026-10-11; the September 9 qualification below is historical. This slice runs in Augmentor's Pi runtime
without Resonant CORE. It follows the user's decision to develop useful
standalone capabilities while CORE's design continues. No CORE code, service,
credential store or scheduler is required or modified.

## What runs now

Native Pi conversations expose two tools: `desktop_delegate` and
`desktop_evidence`. For a multi-step desktop task, it supplies a small brief with
`task`, `successCriteria` and `constraints`. The runtime creates an independent,
durable Pi SDK child session with the **currently selected model** and effective
parent thinking level. The awaited coordinator tool uses that model sequentially.
An explicitly started background job can overlap ordinary parent inference; no
provider concurrency or model/GPU configuration is changed.

The worker can connect, capture, click/type/send keys, inspect accessibility,
stop, and finish. It cannot use shell/file tools, recall memory, load the parent's
skills or project instructions, recursively delegate, or choose another model.
The coordinator must include all relevant user constraints in the brief. This
explicit handoff can omit important facts; context isolation alone cannot fix a
bad brief. Essential missing information should produce a blocked result.

Only one specialist runs per Pi host, and only one delegation is accepted per
coordinator turn. The coordinator's existing direct desktop tools remain for
simple operations. Pi desktop tool execution is sequential; direct capture/input
is refused while a specialist runs. The native broker continues to enforce
ownership across chats and harnesses.

```mermaid
flowchart TD
    A[Augmentor coordinator · existing Pi session] -->|bounded brief| B[Desktop specialist · separate Pi session]
    B --> C[Portable desktop tool vocabulary]
    C --> D[Native adapter · Linux or macOS]
    D -->|screenshots and observations| B
    B --> E[Private local evidence files]
    B -->|short result and run ID| A
    A -->|explicit evidence lookup| E
```

## Context and execution limits

| Bound | Default |
| --- | --- |
| Worker model requests | 24 |
| Worker tool attempts | 40 |
| Elapsed worker time, including consent/approvals | 180 seconds, plus bounded executor shutdown |
| Provider output request | At most 1,024 tokens, capped by the model's configured maximum |
| Input guard | Smaller of configured model context and 24,000 token budget, including output reserve |
| Images retained in each outgoing worker request | Two most recent |
| Metadata or accessibility observation | 8,192 UTF-8 bytes |
| Evidence per run | 16 MiB |
| Evidence store admission | Reserve space within 256 MiB; refuse new runs at capacity |
| Coordinator result text | Summary and verification, at most 600 characters each, plus bounded metadata |
| Evidence retrieval | At most five events and 10,000 event bytes per call |

The input guard conservatively counts serialized text bytes and reserves 4,096
tokens per retained image. It is **not an exact tokenizer or a verified image
token estimate for every provider**. It may stop early, and a provider may still
reject its context. Model capability data comes from the selected route's
configuration, not a successful visual capability probe. A text-only configured
model is refused before any worker request. There is no silent fallback.

Only old image payloads are replaced in outgoing requests. Tool call/result
pairs, observation metadata, constraints and errors remain. If that bounded
history no longer fits, the worker stops instead of silently dropping task
requirements. Automatic compaction and retries are disabled. The worker's
SDK owner is disposed at completion; native screenshots and tool pairs remain
under its private child history. Images are not automatically inserted into the
parent's session or display journal. This is context
separation, not a separate operating-system process or a security sandbox.

Limits have host defaults in `packages/computer-use/src/contracts.ts`. The
shared jobs API accepts explicit request/tool/time/total-output bounds within its
host maxima; context, image and per-request limits remain specialist-owned. Future qualification should tune image reserves and
context budgets for each actual provider. Total token savings and task success
relative to direct execution have not yet been measured.

## Permissions, results and recovery

Read-only chats cannot delegate desktop tasks. Workspace-write chats still
require approval for **each input action** through Augmentor's existing dialog.
Full-access chats use their existing policy. Delegation itself grants no extra
authority. OS screen-sharing consent remains mandatory and can be requested
only once per worker run.

The worker inherits the parent chat's native desktop owner. Chat Stop aborts
worker inference, cancels pending interactions and closes the desktop connection.
The existing independent desktop Stop remains available. A denied/refused tool,
executor error, budget exhaustion or cancellation ends the worker. An intent
record is written before input is dispatched. Interrupted actions are never
resubmitted by this subsystem. A process crash leaves an `unknown` record;
restarting the runtime does not reopen or resume the worker.

`desktop_finish` must return `completed`, `blocked` or `unknown`, a short summary,
and the evidence the worker observed. The runtime additionally reports
`cancelled`, `budget_exceeded` or `failed` when appropriate. It requires a
screenshot after the last input before accepting a completed claim. For an
inspection-only task, at least one screenshot is required.

**A post-action screenshot is not proof that the requested effect succeeded.**
`verificationSource: worker_observation` identifies a model's interpretation,
not an independent verifier. File contents, successful saving or remote delivery
may need a separate check through the coordinator's appropriately authorized
tools. No claim of success is inferred from input dispatch or a worker's final
unstructured prose.

Evidence lives under `$AUGMENTOR_PI_STATE/desktop-runs/<run-id>/`, normally
`~/.local/state/augmentor-pi/desktop-runs/`. Directories are created private;
records and screenshot files use mode 0600. Records contain the brief, attempted
input, observation metadata and result. Screenshots may contain sensitive visible
desktop information. `desktop_evidence` accepts only a run ID belonging to the
current conversation and returns bounded metadata plus a local artifact
directory. It never automatically sends those images into the coordinator.
Ordinary authorized file access is not sandboxed by this tool's ownership check.

Evidence is retained until the user removes it; there is no automatic deletion.
Review and remove completed run directories when storage fills. Do not remove an
active run. This store is separate from ordinary chat deletion and support
exports. A local selected endpoint keeps this module's inference local; a remote
selected endpoint receives worker screenshots just as it receives other model
inputs. This module does not enforce network routing.

## Shared durable jobs lifecycle — October 11

The [Pi jobs contract](PI-JOBS.md#desktop-specialist-jobs) now owns admission,
parent/child IDs, bounds, cancellation, durable outcomes and one-time normalized
usage attribution for the specialist. `desktop_delegate` remains an awaited,
once-per-turn tool; `job_start kind:desktop` and `session.startJob` use the same
producer in the background. The standalone Jobs form accepts task, observed
success criteria and constraints, then offers child-native and provider-payload
inspection without changing Native/Browser control placement.

The specialist keeps its fixed six tools and isolated context. Its native owner
is `job-<jobId>`; OS/evidence ownership remains the parent so existing consent and
independent Stop work. Both evidence intent and the durable job checkpoint are
saved before input. An unconfirmed release stays unknown after Stop; restart
never reconnects or repeats an input. The job outcome must be read alongside its
partial desktop checkpoint. Child SDK files are private and survive disposal;
standalone direct specialist runs also save their native history inside the run.

Normalized child usage is attributed once through the parent's public native
usage entry, confirmed against saved originals. Explicit reads/waits have no
result-usage field, so they do not add usage again. Interrupted provider usage
may remain unavailable. Native screenshot history, optional provider captures
and desktop evidence have separate retention; the existing 256 MiB evidence
admission counts direct evidence files, not the new nested standalone native
history. Removing an inactive run removes that nested history too. General job
history lives separately and is retained when its job receipt is removed.

`pi-desktop-jobs.test.mjs` invokes the actual Host, public SDK and desktop Python
client against an independently authored private wire peer. It covers awaited
and operator runs, saved screenshots/tool pairs, exact-parent inspection, limits,
consent refusal, disconnected input, failed release, Stop during inference/input
approval, crash recovery and usage. Actual Chromium verifies the form, literal
HTML rendering, 640-pixel viewport, Stop and scoped cold reads. These qualify
source/staged contracts, not live model perception, physical consent or installed
Linux/Mac/Windows acceptance. Exact counts/ref and failures belong to the handoff.

## Future Resonant integration boundary

`packages/computer-use` owns Augmentor's versioned brief/result, limits, evidence
records and common desktop tool vocabulary. Its contracts contain no Pi SDK
types. `packages/runtime/src/desktop-specialist.ts` owns the Pi SDK lifecycle,
tool registration and context handling. `packages/pi-linux/src/desktop-executor.ts`
binds the native executor and its Linux knowledge. Changing platforms should
replace the executor implementation and domain instructions; native permission,
focus, input and capture behavior still needs qualification on each platform.
The common executor now selects Linux KDE/portal or macOS native capture and
accessibility support. This lifecycle checkpoint is qualified on Linux with a
synthetic desktop peer; physical Mac consent/input and installed parity remain
separate gates. Windows desktop control remains unavailable.

`augmentor-computer-use/1` is a private Augmentor component contract, **not a
claimed Resonant API**. Once CORE's actual contracts are ready, a reviewed
integration should put CORE at the authority boundary:

| Concern today | Future integration responsibility |
| --- | --- |
| Augmentor chat owner and permission callback | CORE-issued identity, scoped authority and cancellation; do not retain a competing authority source |
| Explicit selected Pi model and SDK worker session | Reviewed inference/agent-loop adapters and capability qualification |
| Host-local one-worker admission and bounded execution | CORE worker admission/lifecycle; replace local policy where CORE becomes authoritative |
| Native Linux control/observation adapter | Tool adapter that validates current CORE authority before effects |
| Local scoped evidence records | Reviewed artifact storage, access, retention and provenance contracts |
| Structured brief/result and outcome uncertainty | Translate to the final CORE task and recovery semantics |

Those are intended seams, not a guarantee of a drop-in connection or just a few
line changes. Existing local implementations can sit behind adapters where the
final contracts permit. CORE identity/custody, scheduling, shared domains and
distributed recovery are intentionally not reimplemented here. The current
native token expires after 30 seconds and remains authoritative for a desktop
target; CORE integration must preserve that protection.

## Use and validation

Build this checkout with `npm run build`, then run its Pi host using the existing
development configuration. No installed service was restarted or replaced by
this change. Existing already-loaded runtime processes must load the new build
before these tools are present.

In a Linux **Pi** conversation with the intended image-capable model selected,
open a harmless target application and give a bounded instruction such as:

> Use the desktop specialist to inspect the open Kate window and report the
> document title. Do not edit anything or open another application.

Choose OS sharing consent yourself. For a subsequent editing workflow, include
the exact text, target file and expected result, then independently inspect the
saved file. Unsupported non-ASCII text, multiple monitors or other desktops
remain outside the current executor's scope. Browser conversations, DSH and
OpenCode do not expose this new specialist; their existing tools are unchanged.

`tests/desktop-specialist.test.mjs` currently uses pinned public Pi 1.1.0 sessions and an HTTP SSE
model fixture with a simulated executor. It covers parent/worker context
isolation, image routing, selected-model preservation, scoped evidence,
pre-dispatch intent, permissions, unknown outcomes, post-action observation,
batched calls, no second delegation in a turn, budgets and cancellation. These
are contract/lifecycle checks, **not live GUI reasoning or CORE tests**.

The next empirical step is a small set of harmless real desktop tasks on the
selected local model. Record independently checked outcomes, coordinator and
worker input sizes, total inference, time and blockers. Do this before adding
more models or parallel workers. Stronger perception, deterministic routines,
exact token accounting and model capability qualification remain later work.

Historical September 9 validation on Node 24.19.0: `npm run build` passed and `npm test` passed all
73 tests, including 14 specialist tests and the host eligibility integration
check. No live desktop, local-model quality or CORE test was run for this slice.

October 11 specialist implementation `f3a3d4ac476f71c86ea0f2c9ffe3fcfb218cbb91`: final source **820 cases/818 passes/two existing optional skips**; ordinary unselected stage 20, Node 24.19.0, **212 passes across 47 files with four test workers**, no failures/skips and unchanged timeouts. The [current handoff](AGENT-HANDOFF.md#october-11-pi-desktop-specialist-jobs-checkpoint) records scope, retained fixture/timeout failures and all remaining migration/platform/installed gates.
