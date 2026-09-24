<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Documentation index

Licensing and publication: [combined Augmentor license](LICENSING.md),
[public source and privacy review](PUBLIC-SOURCE.md),
[canonical repository, archives and preserved work](REPOSITORIES.md).

GitHub is the maintained source of truth. A new agent should begin with
[Start here: agent handoff](AGENT-HANDOFF.md), which identifies the development
branch, qualified commit, repositories and unfinished work. Current guides explain
behavior; dated plans/evidence explain decisions and what passed at that time.
A passed historical build is not qualification of a later source checkout.

Each area below has an owning guide. For a change, update that guide, the feature
matrix and relevant setup/data/test instructions together. Source and installed
state must remain distinct. Private logs, credentials and conversations stay out
of this repository; include reproducible commands and sanitized evidence summaries.

## Start and understand the product

- [Start here: agent handoff](AGENT-HANDOFF.md)
- [Current architecture](ARCHITECTURE.md)
- [Feature ownership and compatibility · Augmentor 0.2.9 development](FEATURE-MATRIX.md)
- [Desktop development snapshot · 19 September 2026](DESKTOP-UPDATE-2026-09-19.md)
- [Source baselines and migration inventory](SOURCES.md)

## Memory, prompts and conversation

- [Automatic relationship and project memory](DUAL-MEMORY.md)
- [Memory processing and energy review — 21 September 2026](MEMORY-ENERGY-DESIGN-REVIEW.md) (investigated; replacement lifecycle proposed)
- [Automatic memory: operations and developer contract](MEMORY-OPERATIONS.md)
- [Optional manual memory library](MEMORY.md)
- [Improve a draft](PROMPT-IMPROVEMENT.md)
- [Saved prompts and DSH commands](SLASH-COMMANDS.md)
- [Native DSH queue and steering](QUEUE-AND-STEERING.md)
- [Linux reply completion](REPLY-COMPLETION.md)
- [Bounded DSH execution recovery and response validity](BOUNDED-EXECUTION-RECOVERY.md)
- [Augmentor Pi client protocol v1](PROTOCOL.md)
- [Large chat recovery · Augmentor 0.2.7](HISTORY-RECOVERY.md)

## Voice and desktop experience

- [Resonant Voice single-button desktop interaction](VOICE-SINGLE-BUTTON.md)
- [Hands-free native implementation](HANDS-FREE-IMPLEMENTATION.md)
- [Desktop colors and skins](SKINS.md)
- [Independent second window](SECOND-WINDOW.md)
- [Linux window resizing](WINDOW-RESIZING.md)
- [Linux desktop control preview](DESKTOP-CONTROL.md)
- [Bounded desktop specialist](DESKTOP-SPECIALIST.md)
- [Browser Settings](BROWSER-SETTINGS.md)
- [Browser recovery review — 19 September 2026](BROWSER-RECOVERY-REVIEW.md)
- [Desktop offline recovery](DESKTOP-OFFLINE-RECOVERY.md)
- [Restart reliability incident and verified corrections — 20 September 2026](RESTART-RELIABILITY-2026-09-20.md)

## Setup, operations and distribution

[0.2.12 desktop flare correction](RELEASE-0.2.12.md).
[0.2.11 security release and upgrade guidance](RELEASE-0.2.11.md).

- [WebSocket security correction and release boundary — 24 September 2026](WS-SECURITY-2026-09-24.md)
- [Complete Linux 0.2.10 release and included plugins](LINUX-RELEASE-0.2.10.md)
- [0.2.10 artifact identity and completed qualification](RELEASE-QUALIFICATION-0.2.10.md)

- [Complete guided Desktop + Browser installation](COMPLETE-INSTALL.md)
- [Installed/GitHub/distribution audit — 20 September 2026](DISTRIBUTION-AUDIT-2026-09-20.md)

- [Consistent desktop releases and update workflow](DESKTOP-DEPLOYMENTS.md)
- [Connect your model in the preview](FIRST-RUN.md)
- [Optional DSH connection](DSH-SETUP.md)
- [Debian packages: development preview](LINUX-PACKAGES.md)
- [Updating, migrating and removing the Debian preview](LIFECYCLE.md)
- [Data, permissions and support](DATA-AND-SUPPORT.md)
- [Browser private-preview distribution](BROWSER-DISTRIBUTION.md)
- [macOS development installation](MACOS-INSTALLATION.md)
- [Fedora 44 installation preview](FEDORA-PREVIEW.md)
- [Licensing and distribution decision](LICENSING.md)
- [Cross-platform implementation status](CROSS-PLATFORM-RELEASE-STATUS.md)
- [Augmentor Agent Desktop release plan — updated 2026-09-14](CROSS-PLATFORM-RELEASE-PLAN.md)
- [Linux DSH first release priority](LINUX-DSH-RELEASE-PRIORITY.md)
- [Linux DSH plugin acceptance](LINUX-DSH-PLUGIN-PARITY.md)
- [Independent private beta](PRIVATE-BETA.md)
- [Linux/macOS release acceptance checklist](RELEASE-ACCEPTANCE-CHECKLIST.md)
- [Private preview release review](RELEASE-REVIEW.md)

## Decisions, dated evidence and history

These records retain their original scope. Use the handoff and current architecture
for present behavior; uncompleted plan items are not feature claims.

- [One Augmentor: shared services, two surfaces, replaceable harnesses](COMPOSABLE-AUGMENTOR-PROPOSAL.md)
- [Composable Augmentor implementation](IMPLEMENTATION.md)
- [Reliable task execution harness — implementation plan](TASK-EXECUTION-HARNESS-PLAN.md) (proposed; not implemented)
- [Task execution harness — challenge review and first experiment](TASK-EXECUTION-DESIGN-REVIEW.md)
- [Implementation plan](PLAN.md)
- [Augmentor productization plan](PRODUCTIZATION-PLAN.md)
- [Productization execution ledger](PRODUCTIZATION-STATUS.md)
- [Local voice for Augmentor through DSH](VOICE-PLUGIN-PLAN.md)
- [Computer use for Augmentor through Resonant CORE](COMPUTER-USE-RESEARCH.md)
- [Installing and rolling back the shared implementation](MIGRATION-0.2.md)
- [Linux release 0.1.0 verification](VERIFICATION.md)
- [Local 0.2.8 preview verification — 2026-09-10](VERIFICATION-0.2.8.md)
- [Augmentor Agent Desktop 0.2.9 — Linux release candidate](LINUX-RELEASE-0.2.9.md)
- [Preview changes](CHANGELOG.md)
- [Augmentor Agent for Linux — powered by Pi · 0.1.0](HISTORICAL-PI-0.1.md)
- [Historical architecture · Pi 0.1](HISTORICAL-ARCHITECTURE-0.1.md)
- [Historical OpenCode harness · Augmentor 0.2.6](OPENCODE.md)

## Source-level entrypoints and external repository

- [Mobile remote Desktop](../apps/mobile/README.md), [Android internal host](../apps/mobile/android/README.md), [roadmap](MOBILE-REMOTE-PLAN.md), [validation](MOBILE-REMOTE-VALIDATION.md)
- [Native desktop](../apps/native/README.md)
- [Browser surface](../apps/browser/README.md) and its [agent conventions](../apps/browser/AGENTS.md)
- [Runtime](../packages/runtime/README.md), [protocol package](../packages/protocol/README.md), [Pi Linux tools](../packages/pi-linux/README.md)
- [Locked DSH test host](../release/dsh/README.md)
- [Test map](../tests/README.md) and [CI workflow](../.github/workflows/validate.yml)
- [Resonant Voice handoff and documentation index](https://github.com/ManoloRemiddi/resonant-voice/blob/main/docs/AGENT-HANDOFF.md)
- [Original imported browser architecture](../apps/browser/PROPOSAL-plugin-architecture.md), [DSH-only README](../apps/browser/HISTORICAL-DSH-README.md), [plugin](../apps/browser/plugin/README.md), [steering adapter](../adapters/dsh-steering/README.md)

Concurrent uncommitted features are not a GitHub handoff. Add their guides here
when their implementation and validation are published, rather than linking
files available only in a developer's working directory.

- [Controlled memory and selected context](CONTROLLED-MEMORY.md): current bounded inference, provenance, tests and operating limits.
