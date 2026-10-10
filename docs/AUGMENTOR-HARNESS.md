<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor Harness — implementation and qualification

The owner authorized building the accepted [Pi migration](AUGMENTOR-HARNESS-MIGRATION.md) on 10 October 2026. The implementation branch is `feat/augmentor-harness`, based on canonical main `79784a5687b73234b9524e7a48e91f01306f73c9`. The older dirty checkout and historical private repositories remain intact. This is an incremental source candidate. Existing installed applications, selected releases, model settings, speech services and conversations have not been migrated.

## Available in this candidate

`apps/harness` is an authenticated local web interface named **Augmentor Harness**. It connects to the existing `packages/runtime` Pi owner. It does not run another agent loop. Chat renders provider-supplied reasoning and answers. The Trajectory view shows ordered request/tool/turn observations, recorded timings, loaded-record search and interval focus. Context shows the effective structured provider input after registered payload transformations, including system/messages/tool declarations and retained inline images.

The timeline projection is selected public DSH MIT source at `d743267388641bc76f17c45ce8b4c231aed1d32c`. The [source record and original license](../packages/harness-ui/vendor/dsh/SOURCE.md) identify its adaptations. Compiled distributions carry that notice under `dist/harness-ui/vendor/dsh`. The surrounding interface and product adapters are Augmentor-authored and retain `LicenseRef-Augmentor-MIT-Resale-1.0`; their license must not be described as unrestricted MIT. No DSH session/backend loop is copied.

The three root Pi packages are pinned to published **1.1.0**. Their SDK session owns execution, native history, cancellation, compaction and exact branching. The desktop specialist now composes the supported `finishTurn` hook. Browser sessions retain their restricted tool policy. Shared prompts, memory bindings and other product integrations retain their existing owners.

## Open and inspect

First build the source with `npm ci --ignore-scripts` and `npm run build`. Development must use an isolated, explicitly configured profile. Set `AUGMENTOR_PI_CONFIG`, `AUGMENTOR_PI_STATE`, `AUGMENTOR_SHARED_DATA` and `AUGMENTOR_SHARED_STATE` to separate development folders; use the existing model setup contract to configure that profile. Do not point development at the owner's installed state or change local model context, GPU placement or speech settings.

Run `npm start` with that environment. In a second terminal using the same profile, run `npm run harness`. It asks the already-running owner for `harness.open` and opens its private link in the default browser. `--session ID` opens an existing conversation. `--print-url` explicitly prints the private link for manual opening. No launcher command submits a prompt or starts a second runtime. An older owner without this method must be stopped through its normal lifecycle before a tested replacement can own that profile.

For a synthetic demonstration, `npm run harness:proof` starts a temporary profile, a deterministic loopback provider and the real Pi runtime. Its stdout identifies an ephemeral fixture URL. The fixture model reads `note.txt` through the actual Pi tool loop and clearly labels its answer as a test. Ctrl+C removes this fixture's temporary state. This proof does not use private prompts, production providers, microphones or installed application state.

The interface exposes available configured models; a missing selection does not silently choose a provider. New conversations require a working folder. Narrow windows expose conversation/history controls through **Conversations**. The existing Native and Browser layouts remain available; wiring their inspection entry points is still required.

## Observation and privacy contract

See [the observation store](../packages/observation/README.md) and [client protocol](PROTOCOL.md). Metadata capture is on during managed operation. Full request/tool/message diagnostic copies are **off by default**. **Save context history** enables future payload copies for that Pi profile. This switch neither reconstructs earlier requests nor deletes previously retained copies. Pi's ordinary native conversation history remains a separate private record.

Diagnostics live under `<Pi state>/observations` with mode-0700 directories and mode-0600 files. Retention defaults to 14 days and 512 MiB. Payloads expire before metadata under size pressure. Counters survive clear/expiry; a crash can leave a sequence gap but cannot reuse an acknowledged position. Incomplete journal tails and owned atomic-write leftovers are removed without executing work. A response reports missing, disabled, invalid, oversized or expired coverage honestly. Diagnostic clearing leaves native Pi history unchanged.

Known credential field names are redacted from retained structured bodies. Authorization headers are never observed by this adapter. Arbitrary user/tool content can contain secrets; the capture switch is not a guarantee of automatic content scrubbing. Payload chunks use UTF-8 byte cursors and complete characters. Large payload reads are bounded and do not reload the whole body for each chunk. Files cap at the smaller of 32 MiB and half the retention budget.

The request boundary is **provider payload after hooks**, verified against a synthetic provider's received object after two extension transformations. It is structured input, not a claim about exact HTTP bytes or every transport retry. Timings use monotonic differences within the producer process. SDK-normalized usage may contain zero defaults for unavailable provider fields; those fields are not independently verified measurements. Parsed raw provider events, exact context-source provenance, routed-policy explanation and separate retry-attempt capture remain gaps.

Managed Pi settings explicitly disable install reporting and analytics. Model-network discovery is disabled. The runtime contract blocks external TCP attempts before imports and exercises configured loopback inference. This qualifies the pinned core in that synthetic environment; installed live services and separately approved extensions require their own destination inventory and network proof. European project roots do not establish data residence.

## Transport and ownership

The HTTP server listens on `127.0.0.1`, with an ephemeral port and a random bearer token. Its private descriptor is `<Pi state>/harness.json`. The browser receives the token in a URL fragment, stores it only in that tab's session storage and removes the fragment from visible history. Never publish this descriptor or a real profile's link.

API requests require the bearer token and the expected Host and browser Origin. Static paths are fixed. CSP permits local scripts/styles and retained data images, forbids external connections and framing, and responses disable caching/referrers. This is a trusted local operator interface for its Pi profile. Its RPC allowlist excludes direct model configuration and shutdown. Browser/embedded scoped bridges do not receive this operator token.

A browser watch is tied to its conversation and client identity. Approvals/questions must match that watch. Concurrent `harness.open` calls reuse one server. The runtime binds its owned IPC socket before opening journals, so simultaneous fresh launches cannot both recover a profile. Ordinary IPC disconnect does not cancel a pending approval while a Harness watch still owns that conversation.

The live ring caps at 4,096 frames and 16 MiB, and each response stays within the 1 MiB transport limit. Loss is identified for the affected conversation; clients refresh durable history and recent observations without replaying actions. Stable display sequences suppress overlap between snapshots and live frames. The chat projection retains partial text and reasoning after Stop/restart, reports missing tool outcomes honestly, and periodically reconciles active status. Idle runtime shutdown has its own observation rather than impersonating a user Stop. The ledger renders a bounded visible row range and pairs tools by request/tool identity. Metadata paging still scans the retained journal; a large-history index, full-history search, owner-restart connection discovery and longer performance qualification remain required.

## Delivery gates

| Migration area | Candidate state | Remaining before its DSH workflow can move |
| --- | --- | --- |
| Chat, reasoning, Stop, native session history | Real SDK fixture contracts | Native/Browser rendering and representative live providers; complete interrupted/partial output behavior |
| Trajectory and effective context | First shared inspection client; post-hook payload, tool and cold-read proof | Source provenance, raw-provider coverage, usage/configuration detail, indexed history/search, native entry points |
| Explicit model selection | Existing runtime validation retained | Thinking/adaptive policy port, settings UI and visible effective routing |
| Exact branch/edit | Existing native Pi context tests retained | Harness controls, Native/Browser end-to-end and memory cutoff acceptance |
| Shared prompts | Existing service preserved | Harness library/editor and complete instruction composition provenance |
| Queue and responsive steering | Concurrent prompts still rejected | Product queue, steering cancellation boundary and uncertain-action rules |
| Tool budgets and originals | Existing DSH behavior preserved on DSH | Pi context edits, retained originals, excerpt tool and action-aware recovery port |
| Memory | Existing Pi binding retained | Live banks, restart/branch scope, outage and capture controls across all intended surfaces |
| Voice/hands-free, MCP, wiki/web/metafolder, plans/jobs | DSH paths retained | Supported Pi extension binding and lifecycle/authorization qualification |
| Home, embedded profiles, mobile, multiple windows | Existing integrations preserved | Pi-specific negotiated capabilities and surface/platform parity |
| Packaging | Locked production inventory, staged runtime contracts and strict Linux native inventory | Complete release artifact, both OS package checks, installed qualification and promotion |

This matrix does not redefine the accepted migration as the first interface. P0/P1 requirements in the specification remain binding. DSH cannot be removed or Pi made default for an affected workflow until its gate passes. Passing a source build alone does not qualify an installed cutover.

## Evidence record

Browser verification used the real Pi 1.1.0 session with a synthetic SSE provider and an isolated temporary profile. At 1440×900 and 640×900, New conversation, Chat, reasoning, actual read execution, Trajectory tool payloads, Context and metadata search were inspected. A slow fixture stream was stopped and its partial text/reasoning remained after reload. Status reconciliation corrects a stale busy snapshot during cleanup. No browser warning/error was observed. Fixture screenshots live in ignored `outputs/harness-proof`; they are development evidence rather than release certification. The private launcher also returned the same owner's link without inference. The temporary browser tab, viewport override and fixture runtime were cleaned up.

Qualification of the source candidate based on `79784a5`:

- Build, TypeScript, design/shader source checks, version consistency and diff whitespace pass.
- Full Node suite: **532 cases, 530 pass, 2 existing platform skips, 0 failures**. New contracts cover payload transformations, Unicode byte paging, retention/crash cleanup, session-specific event loss, private transport, stable display projection and simultaneous fresh owner startup.
- Full Python/Qt suite: **858 cases, 821 pass, 37 platform skips, 0 failures** using an isolated PySide6 Essentials/shiboken 6.8.2.1 test environment. Platform skips do not establish Windows/Mac physical acceptance.
- Staged production tree: **35 runtime/ownership/ws cases pass** with its own pinned Node 24.19.0, no development dependencies, terminal helpers or codemode native assets. The Host runs with staged files and working directory; test drivers remain in source. This is a staged runtime proof, not a complete installed bundle.
- Locked production license inventory: **126 package instances**. Strict Linux native scan records exactly Node 24.19.0, esbuild 0.28.2 and reviewed Photon 0.3.4.
- Private speech-source boundary passes for the available canonical branch history and tracked files. New files are independently authored or selected public DSH source.

Initial failures and repairs remain part of the evidence: the first broad run lacked QtTest; an obsolete display-argument assertion was replaced with separate payload/display-policy checks; the network recorder initially stored a port as text and now normalizes it; strict packaging exposed deduplicated dependency paths and unused Pi terminal binaries. The first Python run had one synthetic dictation failure because its interpreter shebang contained the workspace's spaces. Running the same isolated environment through a temporary path without spaces passed all 22 dictation cases and the complete suite; no dictation product code or installed speech state changed. Hosted Mac/Linux package qualification remains pending.

The production stage preserves the rebuilt Photon module and excludes unused standalone Pi bundles/examples. Dependency paths are resolved through the active SDK rather than assuming a nested or root copy; production and development npm layouts can differ. Esbuild 0.28.2 uses Go 1.26.5; exact license sources are recorded in `licenses/catalog.json`. Pi 1.1.0's terminal native keyboard/clipboard directory is excluded because Augmentor owns Qt/browser input and the upstream loader handles absence. The new `quickjs-wasi` 3.6.2 native assets are excluded because codemode execution is not registered and its full static dependency notices remain unqualified. Registry provenance names source `5a7a0eeda87c99542f8cf3095b6d61ecfa755977`; inspecting that record is not signature verification or a reproducible build. MCP/codemode release qualification must resolve this exclusion before enabling execution.
