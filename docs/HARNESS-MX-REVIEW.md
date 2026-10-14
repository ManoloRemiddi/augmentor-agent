<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# MX Harness review build

A separate private Linux review instance is available for owner feedback. Its
operator link is supplied privately in the chat/browser panel, never in this
repository. The installed desktop preview, its draft and the earlier feedback
profile keep their own settings and history.

## Start testing

Open the review link and choose **New Session**. The original DSH start page
keeps its composer disabled until a workspace/session is selected. The fresh
profile uses the existing local Qwen route, starts in **read-only** mode and has
keyless Search enabled. No personal conversations, provider credentials, MCP
configuration or voice/memory-engine configuration were imported. Those services
and workflows still need their separate setup and acceptance.

Local chat history and provider-request inspection are enabled in this profile
so Trajectory and Context can be tested. These files remain local to the review
profile. Diagnostic capture/retention and native conversation originals have
[different erase boundaries](DATA-AND-SUPPORT.md#native-managed-memory-originals).
No real model request or tool action was submitted during the initial owner-profile
browser check; its history was empty when handed over.

The Codex browser opening was **queued for this chat**. Actual owner interaction
or feedback is not inferred from that request. A separate real Chromium check at
1440×1000 renders the original interface, sidebar and central Augmentor marks,
Settings and Connected state with zero browser errors or failed responses. It
observes the legitimate disabled start-page composer. A malformed selector in the
first external QA driver was corrected without restarting the owner runtime or
submitting any model/tool work; that preparation failure is retained separately.

## Artifact and qualification — October 14 refresh

- Product **0.2.13**, Pi SDK **1.1.0**; public source
  **9f5bc70a2aac9a974aa656cfadd53cca08737048**, tested application change
  **7987447efc56146e47f919322d514916b0cb69ef**.
- Unselected review release **20261014-145102-22cbe428**, artifact
  **f55e256e80c1c5345b17a65b24e3d01694fdbc99799e4325dd558173e3357e35**,
  **24,288 inventory entries**. It includes the [New Session input ownership
  fix](DSH-GUI-ON-PI.md#new-session-input-ownership--october-14),
  [runtime listener ownership](AUGMENTOR-HARNESS.md#runtime-listener-ownership--october-14)
  and [instruction links](AUGMENTOR-HARNESS.md#instruction-source-links--october-14).
- Immediate base: public **f98424b0a240b4b0c9d5e475d6e77ee4d2706312**, artifact
  **6ae1d969a68f48027fee1392a19b92a66bf3619707fca5871b2785249c125331**.
  Original base: **454db9d9915724b53998e187c30c2943a0d7d3b2**, artifact
  **964d1cdef122aab51fd46510f897a35d1bd391e97d4f7ae1f52983160569f3e5**.
  The candidate records this mixed provenance. Twelve changed public artifact
  files and the complete **908-file compiled tree** overlay the verified immediate
  base; **155 production npm instances**, bundled Node **24.19.0**, components
  and all **846 notice files** retain their bytes/link inventory.
- Source and fresh ordinary checks each pass **179/179 across 51 files**. The
  candidate-selected executable/runtime cohort also passes **179/179 across the
  same 51 files**, two workers, unchanged deadlines, no skips. It includes all
  **42 Harness Chromium files**, Host lifecycle/input, durable queues and affected
  pure contracts. Drivers/static imports run from the test checkout; selected
  Host/Harness/native targets use the sealed stage, with matching compiled and
  dependency bytes verified for direct static imports.
- The **full inventory verifies after the cohort and again after runtime/browser
  startup**. Live RPC/process checks confirm the exact executable, PID/profile,
  product/SDK, read-only local model selection, keyless settings, local capture,
  zero sessions/active turns/drafts and private descriptor/socket modes. Runtime
  paths and operator URLs remain private. No model request or tool work is sent
  during the owner-profile check.

The prior **20261014-123717-b98af12b** review remains running with its own profile;
its local receipt/link is preserved. Its earlier 120/120/43-file qualification
applies to that artifact, not this newer source. The still earlier e2beaf5 stage
whose indexed-history test added a screenshot remains a failed inventory
qualification. It was never patched/resealed; the [output fix](DSH-GUI-ON-PI.md#read-only-release-qualification-output--october-14)
keeps diagnostics outside staged artifacts. A new preparation check initially
inventoried a dependency subtree in isolation and falsely rejected its valid
internal workspace link. That mutable preparation was corrected before invoking
the managed stage; the sealed artifact was never repaired.

## Remaining acceptance

The selected/running installed preview remains **97897cf**; no launcher or global
selection is changed. The new runtime is a separate browser review instance, not
an installed desktop cutover or a public binary. Production Qwen/speech/memory
configuration and placement remain unchanged. This profile does not activate the
[optional memory-only request mode](CONTROLLED-MEMORY.md#memory-only-llamacpp-request-mode--october-14).

Owner MX feedback, complete P0/P1/reference-plugin behavior, actual credentials/
services, full historical context fidelity, migration/privacy/recovery, physical
voice/desktop and broader Linux/macOS/Windows acceptance remain required. This
review profile does not import the external Blender or Playwright configuration;
their [live workflow proofs](HARNESS-PLUGIN-PARITY.md) have separate exact refs,
fixtures, licensing and limits.

At this source, [SDK platform contracts 38566691857](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38566691857)
and [Windows desktop 38566691858](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38566691858)
pass. Validate **38566691854** and Windows qualification **38566691841** are still
running at this checkpoint. Windows command jobs **38566691869** fails, including
missing shared-companion state in x64 delegation and ARM64 Stop assertions; its
root cause remains unproven. macOS
**38566691882** refuses unreviewed Darwin LibreOffice MPL-2.0/libvips LGPL-3.0-or-later
packaging. The preceding 1d6c30f Validate has 1,157 pass, one narrow Insights/New
Session failure and 23 existing skips; the new ownership fix reproduces the failure
class independently, without claiming the exact hosted interleaving. Earlier Linux
validation reaches the Office exact preferred-source/full-engine-rebuild packaging
gate; that gate remains. New-head hosted results, Office/font/native licence/rebuild
and public distribution remain separate. DSH is retained; the full Harness migration
is still active.
