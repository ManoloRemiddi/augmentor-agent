<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Shared Augmentor persona on Pi

The Pi Host now explicitly supplies `config/agent-persona.md`, the same approved
application persona used by DSH and Codex. Previously Pi supplied browser recovery
and its other adapter guidance but omitted this shared file. It adds the persona
through the supported resource loader's appended system instructions, preserving
Pi's base prompt, tool schema/lifecycle and sole AgentSession ownership. This
changes instruction composition; it introduces no tool, permission or service.

The shared text remains unchanged. An additional capability boundary clarifies
that mentioning an optional tool or service does not register/connect it, permit
a consent bypass, or authorize invented results. In particular, the persona's
`response_metrics` guidance does not mean Pi has that optional tool. Current
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

Full source/fresh artifact and actual local-model qualification remain pending at
this implementation checkpoint. The currently running MX Edit review and selected
installation are unchanged. No new review activation, merge or public binary is
authorized by these tests. Full instruction/resource/causal provenance, optional
response-metrics tooling, other embedded roles, representative provider behavior,
physical MX feedback and wider migration/platform gates remain open.
