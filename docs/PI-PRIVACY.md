<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Managed Pi privacy

Augmentor-managed SDK sessions disable install reporting, experimental analytics,
cache warming and automatic provider retries. These are product policy, independent
of upstream CLI settings. The original DSH GUI is presentation only: its account,
analytics, registry and price services are not mounted.

## Inherited telemetry override — October 13

Pi **1.1.0** checks `PI_TELEMETRY` before its SettingsManager install-reporting
value. An inherited true value can therefore override the Host's false setting
and add Pi attribution to a selected provider request. The preceding immutable
runtime **97897cf** reproduces this in three independently authored local fixtures:
ordinary Host chat, standalone prompt improvement and a desktop specialist.
All receive an unwanted `HTTP-Referer: https://pi.dev`; the synthetic OpenRouter
provider identity exercises the SDK's real attribution path without contacting
OpenRouter. This is a request-header defect, not evidence of external reporting
from the owner's running preview. Its stable/native launchers already set the
environment opt-out.

The authored `managedPiSettings` helper sets `PI_TELEMETRY=0` before creating each
managed SDK owner and supplies the existing false install/analytics settings,
cache warming off, disabled retries, empty package defaults and project trust
never. Chat and bounded child conversations retain their previous compaction
policy; prompt improvement and specialists retain compaction off. All three public
SDK creation paths use the helper. No SDK patch/private import, extra agent loop,
provider selection change or dependency is introduced.

This is a process policy: subprocesses normally inherit the opt-out. Configured
model/provider headers remain intact, including explicit owner attribution.
Upstream CLI settings on disk are not rewritten. This does not strip protocol
headers required by an explicitly configured provider, prevent an authorized
command from changing its own environment, or sandbox trusted extension code.
Reviewed extension/service policy and actual network evidence remain necessary
at every dependency upgrade.

## Destination inventory

| Traffic | Authority and destination |
| --- | --- |
| Chat, compaction, prompt improvement and specialist inference | The explicitly selected/configured provider; ordinary conversation or the documented isolated transformation/worker content. |
| Model discovery or credential operations | Authorized model/setup/refresh/login workflows and configured provider endpoints; SDK credential refresh and live endpoints require separate observation. |
| Memory and speech | Separately configured companions/services under their existing pause, capture, provider and placement policies. |
| Browser, web and MCP operations | Approved tools/resources and reviewed configured server startup; each service and extension has separate data practices. |
| Harness transport/assets/previews | Authenticated local Host and local bundled assets/workers; inspectors retain their narrower scope. |
| Install analytics/cache warming | Disabled in managed Pi sessions; unexpected reporting is a qualification failure. |
| Product updates/support exports | Existing explicit product workflows, with separate reviewable scope; this SDK guard does not qualify public distribution or support export policy. |

This table describes source ownership. It is not an exhaustive live packet audit
of configured services, an OS firewall or a European data-residency guarantee.
The [migration privacy gate](AUGMENTOR-HARNESS-MIGRATION.md#privacy-and-network-policy)
still requires fresh installs, upgrades, live destinations and selected extension
startup to qualify separately. DSH remains available for unqualified workflows.

## Evidence and remaining scope

`pi-privacy.test.mjs` starts a real private Host with telemetry/analytics enabled
in the synthetic saved CLI settings and `PI_TELEMETRY=true`, without `PI_OFFLINE`
or a version-check suppression flag. A preload records TCP attempts before Host
imports and rejects external destinations. Fresh/cold startup makes no provider
or cache-warming request; two explicit prompts contact only the configured local
fixture, without unsolicited attribution or tracking ID. Model, product and CLI
settings bytes remain unchanged. A separate standalone prompt improvement makes
one valid tool-free rewrite with the same header checks. The existing specialist
fixture completes its five-request synthetic task and checks every request while
preserving its exact selected model and explicit owner header. No physical input,
owner model or private conversation is used.

The predecessor fails all three actual header cases. The corrected focused cohort
passes **18/18**, including existing prompt cancellation/no-replay and specialist
permission/Stop/evidence/budget checks. Strict check/build pass. Complete source,
ordinary and immutable qualification are recorded separately below; the current
selected preview remains **97897cf / 20261013-142001-1f7f7f96** meanwhile.
No active window or draft is restarted for this source qualification.

These fixtures establish pinned managed-core behavior and header precedence.
They do not establish live external provider/MCP/extension/OS behavior, unknown
future package defaults, physical audio/display, public fresh-user installation
or Windows/macOS qualification. Full migration and those gates remain open.

### Qualified source

The final expanded **81-file MX cohort passes 432/432**, zero failures/skips/
cancellations, with Node **24.19.0**, two workers, matching isolated QtTest and
unchanged deadlines. Five source packaging cases pass. The first authored driver
omitted the required creation identifier and failed before its request; the
corrected comparator then observes the actual attribution defect. Both results
are retained. The three predecessor header failures and corrected wire cases
are distinct from full migration acceptance. Ordinary/immutable/installed
qualification follows separately; selected/running MX remains 97897cf meanwhile.
