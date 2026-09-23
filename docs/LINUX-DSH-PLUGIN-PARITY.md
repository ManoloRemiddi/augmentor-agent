<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Linux DSH plugin acceptance

The first release must preserve the capabilities of the working DSH installation.
The reference is the observed active inventory, not every installed dependency.
Evidence: `outputs/cross-platform/linux-dsh-required-host-plugins.json` and
`linux-live-dsh-plugin-inventory.json`. These snapshots contain identifiers and
versions, not credentials. Active status does not prove a workflow works.

| Reference integration | Current evidence | Remaining acceptance |
| --- | --- | --- |
| Model Picker Augmented 1.1.2 | Candidate 11 installed DSH and Qt selection/pinning fixture passes | Preserve the existing user's choices during migration |
| Prompt Library 0.2.9 | Candidate 12 installed fixture with an existing active library passes the 12-request DSH/Qt checks | Native edit/conflict workflow |
| Context 0.48.0 | Source desktop-created session retains nonempty Context headers/timeline projections | Final installed reference-host qualification |
| Wiki Skills 0.2.1 and Wiki Tools 0.14.0 | Frozen CI package code passes temporary-vault query/skill loading, write, rename with inbound-link update, and raw-source archive with preserved bytes and cleared manifest | Final live reference-host qualification |
| Adaptive Reasoning 0.2.0 | Source desktop session decision matches stored request effort and actual model request | Final installed reference-host qualification |
| Metafolder 1.2.1 | Active on reference host; live host load API returns 404 | Verify existing web-side behavior; no native control existed in the original desktop |
| Free Web Search 0.1.0 | Source desktop tool returns live Debian documentation results to the model | Final installed reference-host qualification |
| MCP Comfy, Playwright, Blender and Unreal | Read-only MCP catalogs: Playwright 24, Blender 26, Unreal 3 tools; Comfy refuses TCP connection | Comfy must become available; remaining representative tool workflows and desktop-session exposure |

The desktop preset now includes the reference's filesystem search, jobs, skills,
goals, planning, compaction, delegation, todo and web tools. A deterministic DSH
fixture verifies their model-facing tool catalog. Catalog presence does not
qualify every tool workflow or establish third-party host-plugin compatibility.
The native Linux profile, visible Chromium launch and accessibility helpers have
separate live-host evidence in the release status ledger.

## Existing installation migration

The user's `augmentor-linux-product` preset contains custom compaction settings.
The installer correctly refuses to overwrite this customized preset. A reviewed,
backed-up merge preserving those settings is still needed before qualifying the
replacement against the user's running configuration. A separate candidate is
prepared at `outputs/cross-platform/linux-dsh-preset-migration/agent.cordis.yml`,
with source/candidate hashes in `review.json`. It preserves all six existing
entries and adds eleven missing entries; it has not been applied. The live host
reported zero running sessions during this inspection; that must be rechecked
immediately before any eventual installation. Do not delete or replace
that preset just to pass setup. Do not enable previously disabled plugins.

DSH plugins remain owned by the user's DSH host. The Debian app does not bundle
or provision all third-party plugins or external MCP servers. Native controls for
Model Picker and prompts have explicit integration; other web-plugin interfaces
must not be described as native features without verification.

Candidate 12 now passes the installed 12-request fixture with the reference
compaction settings and expanded tool catalog, and explicitly checks that the
existing prompt plugin is not duplicated. This does not exercise a forced
compaction at the context threshold. Evidence:
`outputs/cross-platform/linux-installed12-custom-compaction.{log,json}`.

## Original desktop comparison

The original Linux app and adapter expose Model Picker curation, shared chats,
Linux helpers and browser policy. They have no native Context, Metafolder or
Adaptive Reasoning controls. Compatibility requires preserving those DSH-host
capabilities; it does not establish that their web interfaces are native widgets.
The live Adaptive Reasoning configuration already scopes its route to
`augmentor-linux-product`. No routing change was made. The Metafolder load API
returns 404 on the existing host, so that read cannot qualify persistence and is
not evidence of a new desktop regression.
