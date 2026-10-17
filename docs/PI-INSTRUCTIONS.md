<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Shared Augmentor persona on Pi

The [current unselected MX review](HARNESS-MX-REVIEW.md#shared-persona-and-response-metrics-review--october-16)
**20261016-083019-0c2b4855** includes this binding and response metrics. Exact-
sealed Qwen instruction/context/Edit and metrics checks pass; source/ordinary/
sealed each pass 793/two existing optional skips. Initial owner GUI QA uses an
empty profile; no owner acceptance or installed adoption is inferred.

The Pi Host now explicitly supplies `config/agent-persona.md`, the same approved
application persona used by DSH and Codex. Previously Pi supplied browser recovery
and its other adapter guidance but omitted this shared file. It adds the persona
through the supported resource loader's appended system instructions, preserving
Pi's base prompt, tool schema/lifecycle and sole AgentSession ownership. This
changes instruction composition; it introduces no tool, permission or service.

The shared text remains unchanged. An additional capability boundary clarifies
that mentioning an optional tool or service does not register/connect it, permit
a consent bypass, or authorize invented results. In particular, the persona's
`response_metrics` guidance does not by itself register a tool. The subsequent
[Pi response-metrics binding](PI-RESPONSE-METRICS.md) supplies that capability
with exact native matching and explicit measurement boundaries. Current
registered tools, permission mode, role/workspace and explicit user instructions
remain authoritative. No filesystem, shell or general desktop authority is
added to browser-only conversations. Bounded workers retain their existing
assigned role and do not gain the root assistant persona.

## Conversation selection and native history

`augmentor/application-instructions-v1` is an ordinary SDK custom entry, containing
the exact valid UTF-8 persona text/source SHA-256 and selected capability guidance/
SHA-256. The canonical source path is logical and portable. Only this explicitly
approved file is read: no project context discovery, skill-body scan, network call
or second composition service is added. Persona bytes are limited to **32 KiB**;
capability guidance to **4 KiB**. Empty, oversized, invalid-encoding or corrupt
snapshot data refuses loading without substituting a different source.

New root conversations select the shared source once. An existing root without
an instruction snapshot selects it when that root next loads under this version;
older native entries and messages are preserved. The selected snapshot is appended
through the public SDK before the next user message. Pi may buffer setup-only
entries before any conversation message, so a private metadata bootstrap is saved
first. Cold reopen reuses the native snapshot or that pre-message fallback, with
no current-file reread or automatic prompt. Conflicting native/bootstrap data
refuses loading; it is not repaired or overwritten automatically.

Branches reuse a snapshot in their selected native ancestry. First-input Edit
retains the earlier custom entry before the edited user message. A historical
branch with no such entry deliberately keeps the legacy composition rather than
inserting today's persona. Delegated workers skip root-persona selection. The
metadata fallback is not copied into branch metadata. Native snapshot identity,
parent history and previous tool context remain independent from optional logs.

Only these two selected application instruction bodies are frozen by this
snapshot. It is not a freeze of every tool/extension/policy implementation or a
claim of complete historical request reconstruction. The SDK still owns actual
system messages/patches; their received context is inspected separately.

## Context source evidence

The existing original Context → **Raw Pi context and saved entries** view exposes
an additive `applicationInstructions` snapshot with no layout/CSS/supplier changes.
It identifies the selected native entry and `/text` or `/capabilityGuidance` field,
logical source/hash, and ranges within the already captured before-agent appended
instructions. Source bodies are not duplicated in this annotation. Duplicate
literal matches stay ambiguous; ranges report UTF-16 code units and retain up to
sixteen candidates with the full count.

Separate comparisons report literal presence in the current canonical SDK system
and recognized fields of the effective provider request. User quotations and
unrelated metadata cannot establish system presence. An override may exclude a
selected source: selection alone is not evidence of effective delivery. Unknown
APIs, missing snapshots, redaction and budget exhaustion remain explicit. Loaded
resources, opaque handlers and server transformations do not gain inferred causal
attribution; global `sourceProvenance` stays false.

The annotation is optional, produced after primary provider capture, capped at
**128 KiB** inside the unchanged **8 MiB** aggregate diagnostic budget. Capture
opt-out prevents its body from being saved; disabling then re-enabling capture
cannot restore an earlier discarded preparation body. Core native instruction
selection persists independently of that diagnostic preference. Cold Context
reads do not send prompts, replay tools or reload source files.

## Qualification checkpoint — October 16

Build/type and twelve focused cases pass, including actual SDK/Host Native and
Browser requests, exact source/native IDs before the first user message, original
Context pointer controls in Light/Dark and cold reopen, parent/branch preservation,
legacy branch exclusion, no diagnostic capture, source corruption before dispatch,
UTF-8/size/link checks and optional annotation bounds. Authored providers and files
establish those contracts, separately from live model/installed/physical evidence.
The initial corrupt-source fixture checked an internal status on the public queue
projection instead of its `Not sent` label; the initial browser fixture stopped
its Host while leaving polling active. Those failed logs remain retained. Corrected
fixtures use the public receipt and retire their document before Host shutdown;
assertions, budgets, deadlines, workers and product behavior are not relaxed.

At application **4f4812cc**, full frozen source and fresh ordinary packaged copy
each pass **781 cases/two existing optional skips**, zero failures/cancellations,
across **138 files/all 57 Harness Chromium files**, two workers and unchanged
limits/deadlines. All **3,424 tracked/1,066 compiled/37,629 source dependency**
inputs verify; the ordinary compiled tree matches exactly and production Node/
npm/components retain baseline bytes. Nineteen licence/private-source Python
cases pass. The preceding sealed Edit build fails the new control at the actual
provider's missing shared persona, before GUI inspection, as intended.

The actual local **Qwen** proof on the fresh ordinary copy passes: four request
snapshots identify the selected persona's exact source digest and its presence
in both canonical SDK and effective provider system content. Its preceding native
read is retained through Edit, which makes zero model requests; explicit typed
replacement uses that earlier result with no additional tool call. Parent native
bytes and unsent draft stay exact. Existing 262,144 context/8,192 output declaration,
server, GPU and speech settings remain unchanged. This proves this binding and
workflow; it does not certify every behavioral instruction or all providers.

All Harness UI/app sources, 625 MIT DSH supplier records and CSS remain exact to
the prior review. Rebuilding the existing spreadsheet overlay changes temporary
paths, manifests and an Excel chunk filename; the main GUI is equal after only
that import name is normalized. This comparison explains generated-byte changes;
qualification still checks the new frozen compiled bytes exactly, without ignored
files or relaxed inventory checks.

At this source-only checkpoint the MX Edit review
**20261016-065534-c8cdf03c/application dfe855f3** does not
include this source increment. Thirteen seals/fourteen review owners plus existing
CPU recognition, selected installation, 38 canonical/four private local changes
and six model/speech configuration hashes verify preserved. No new review,
activation, merge, service restart or public binary follows. The preceding
**3aed0c64** hosted SDK passes Linux/macOS, while Windows is cancelled. Debian is
blocked at an existing loaded Codex Browser branch-selection assertion; its cause
is not established. Earlier Windows jobs/native and macOS packaging failures stay
retained. New-head hosted acceptance remains separate from local results.

Owner adoption/physical MX feedback, full instruction/resource/opaque-handler
provenance, representative response-metrics providers, other embedded roles, representative
behavior/provider/speech acceptance and all broader memory/plugin/Home/Office/data
migration/distribution/later-platform gates remain open. The Harness goal remains
active. [Portable evidence](../release/harness-pi-instructions-qualification-20261016.json).

Reproduce the authored contract/browser checks from a development checkout with
`node --test --test-concurrency=2 tests/pi-application-instructions.test.mjs tests/harness-application-instructions-chromium.test.mjs`.
Set the existing isolated `AUGMENTOR_PYTHON` prerequisite as described in the test
guide. Live acceptance additionally uses the owner's explicitly declared local
provider in a fresh private profile; no owner history, key or workspace is imported.
