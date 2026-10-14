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
or feedback is not inferred from that request. A separate real Chromium check
renders the original interface and both Augmentor marks with zero browser errors.
The initial QA predicate incorrectly required an editable composer before selecting
a session; its timeout is a preparation failure, not a runtime restart or a model
failure. The corrected check observes the legitimate disabled start-page composer.

## Artifact and qualification

- Product **0.2.13**, Pi SDK **1.1.0**; public source **f98424b0a240b4b0c9d5e475d6e77ee4d2706312**.
- Unselected review release **20261014-123717-b98af12b**, artifact
  **6ae1d969a68f48027fee1392a19b92a66bf3619707fca5871b2785249c125331**, **24,284 inventory entries**.
- Base **454db9d9915724b53998e187c30c2943a0d7d3b2**, artifact
  **964d1cdef122aab51fd46510f897a35d1bd391e97d4f7ae1f52983160569f3e5**. The candidate records this mixed provenance.
  Twenty-three newer public artifact files and the complete 905-file compiled tree
  are applied over the verified private base; bundled dependencies, Node,
  components and all 846 notice files retain their bytes. The later screenshot
  correction changes the external test driver, not application behavior.
- The candidate-selected executable/runtime cohort passes **120/120 across 43
  files**, two workers, unchanged deadlines, no skips. It includes all 41 Harness
  Chromium files plus Host lifecycle/input and durable queues. Static driver
  imports share the verified matching compiled/dependency bytes.
- The **full inventory verifies after the cohort and again after runtime/browser
  startup**. Live RPC checks confirm the exact PID/profile, product/SDK, local
  model selection, keyless settings, local capture, zero sessions and active turns,
  private file/socket modes and no inherited provider credentials. Runtime paths
  and operator URLs are retained only in private local state.

The earlier separately staged e2beaf5 candidate passed the same cohort but its
post-test inventory failed because the indexed-history test wrote one screenshot
inside the artifact. No code/dependency/component/notice bytes changed. That
artifact is retained as a failed qualification, never patched, activated or
relabelled successful. The [driver output fix](DSH-GUI-ON-PI.md#read-only-release-qualification-output--october-14)
keeps diagnostics in the test checkout; this replacement is a new managed stage.

## Remaining acceptance

The selected/running installed preview remains **97897cf**; no launcher or global
selection is changed. The new runtime is a separate browser review instance, not
an installed desktop cutover or a public binary. Production Qwen/speech/memory
configuration and placement remain unchanged. This profile does not activate the
[optional memory-only request mode](CONTROLLED-MEMORY.md#memory-only-llamacpp-request-mode--october-14).

Owner MX feedback, complete P0/P1/reference-plugin behavior, actual credentials/
services, full historical context fidelity, migration/privacy/recovery, physical
voice/desktop and broader Linux/macOS/Windows acceptance remain required. The
latest preceding e2beaf5 Validate **38549263115** passes locked-DSH SDK/core and all
subsequent Debian native/interaction/recovery/first-run checks, inventory and
extension notices, then refuses the existing Office exact-source/engine-rebuild
packaging gate. That run passes the previously failing viewport cases but does
not establish their root cause or all future scheduling. The controlled 780×437
Jobs probe also passes; viewport size alone does not reproduce its older failure.
New-head hosted acceptance and public Office/font/native licence/rebuild gates
remain separate. DSH is retained; the full Harness migration is still active.
