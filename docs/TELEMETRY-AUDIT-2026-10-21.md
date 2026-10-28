<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Telemetry audit and local safeguards — October 21, 2026

The owner requested a code/network audit, then authorized applying safeguards to
the running memory container and checking integrations. The initial core audit
passed, but the integration follow-up found Chrome background requests and an
enabled legacy community updater with independent browser tracking. Those paths
are addressed below. A passing Pi core test does not qualify its integrations.

## Inspected and changed scope

Source reference: `2305425af1cee77b368d6c0da870daedeebabf38` on the canonical
repository's `feat/augmentor-harness` branch. The running Linux Harness is the
separate immutable `20261021-103715-4720d0ad` artifact, with Pi 1.1.0. The initial
audit verified 7,670 runtime/UI/Pi dependency inventory entries without mismatch
and passed the existing core privacy, prompt-improvement, kernel-observer and
fresh/cold Chromium lifecycle checks against that artifact. No installed
application bytes or dependency pins were changed by the operational follow-up.

### Running memory container

Processing was idle before maintenance. Its processing-only pause was enabled
temporarily; capture stayed enabled. The stopped PostgreSQL volume was copied to
a private tar, structurally verified and SHA-256 recorded. The
previous container is retained stopped with restart disabled. It shares the
database volume with the replacement: never start both, and retain the separate
stopped database snapshot for rollback.

The replacement uses the exact same image digest, database/extension mounts,
host-network setting, CPU/RAM limits, restart policy and existing model/provider
credentials/settings. Only these environment values changed:

```text
HF_HUB_DISABLE_TELEMETRY=1
DO_NOT_TRACK=1
OTEL_SDK_DISABLED=true
HINDSIGHT_API_OTEL_TRACES_ENABLED=false
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
PYTHONDONTWRITEBYTECODE=1
```

Both embedding/reranking models were already cached. The actual libraries report
Hugging Face telemetry disabled, offline loading enabled and Hindsight tracing
disabled. Health is healthy, existing banks are accessible, and a synthetic
read-only recall completes without a memory write. Original journal counts and
processing preference survive; historical pending/stopped work was not retried.

Host `strace` attached immediately after replacement start and followed service
descendants through startup, health, recall and preference restoration. All 62
observed IP calls were loopback: API/database endpoints and local route probes.
There were no external destinations. This excludes the small interval before
attachment; it is bounded syscall evidence, not an OS egress firewall. Tracing
was detached afterward. Private inspect/configuration backups contain credentials
and must never be published.

The existing installer already supplies the main telemetry opt-outs; offline
loading additionally requires cached models. Do not turn an offline-loading
failure into an automatic download or silently change the selected model.

### Playwright MCP

Installed Playwright MCP 0.0.79 uses Playwright 1.63.0-alpha-2026-08-05 and a
Chromium revision 1228 browser, version 149.0.7827.55. Its explicitly selected
Chrome for Testing executable sent background requests despite the normal
Playwright background-networking switches. A new synthetic profile navigated
only to a local authored page; kernel tracing still detected external attempts.
An independent netlog run identified Google account-list, push check-in/
registration, network-time and AI-eligibility URLs. The network-time request
reached the HTTP request-header stage. The evidence does not establish that
private conversations were uploaded or that all other requests completed.

Playwright describes the same distinction between full Chrome and Headless Shell
in [upstream issue 42910](https://github.com/microsoft/playwright/issues/42910).
The already-installed **Headless Shell from the same revision/version** was
qualified instead. No browser download, version upgrade, DNS blocklist, proxy,
firewall or replacement of the owner's ordinary browser was needed.

Fresh MCP initialization discovers the same 24 tools. Local-page navigation and
snapshot succeed, followed by 15 seconds idle. Descendant tracing and browser
netlog contain only the expected local page. One apparent external `connect`
was investigated separately: a UDP socket does `connect`/`getsockname`/`close`
without a send/write. It is Chromium's local IPv6 route lookup, described in
[Chromium host-resolution documentation](https://github.com/chromium/chromium/blob/main/net/dns/README.md#ipv6-and-connectivity),
and is reported separately rather than mislabelled as an HTTP upload or silently
added to a network allowlist.

The managed Harness profile was backed up, then changed through its revisioned
`session.mcpConfigure` operator API. Only the Playwright executable argument
changed. The saved receipt completed and all ten loaded Native owners applied
the new profile revision without pending registration. Both enabled MCP servers
retain their 24/26 tools. No model prompt or owner browser navigation was used.

### Blender MCP

The installed `blender-mcp` 1.0.3 imports `blmcp`; it is not interchangeable with
unrelated similarly named MCP projects. Code inspection found its normal socket
bridge and bundled documentation searches, without a telemetry SDK/export path.
Fresh initialization, one bundled API-documentation search and one read-only
objects-summary call against an independently authored local socket peer pass.
Kernel tracing records exactly that one local peer connection and no external
destination. No owner scene was read or changed. Arbitrary user-submitted Python
and Blender add-ons retain their own authority and network behavior.

### Legacy DSH and speech

The initial audit's statement that the relevant legacy community trackers were
disabled was incomplete: `web-ui-update` remained enabled. Its browser code
calls the same daily heartbeat as other community components, targeting
`https://dsh-market.com/api/telemetry/event` with a persistent browser visitor ID
and plugin/version metadata. DSH's own telemetry environment switches do not
control that separate client code. Browser automation's `navigator.webdriver`
suppresses this tracker, so a synthetic automated page alone is insufficient
to establish its absence.

The legacy composition now explicitly disables `web-ui-update` and selects the
same qualified Headless Shell for its Playwright server. The service restarted
only after confirming no running sessions. It returns online with the saved
session inventory retained; the updater namespace is no longer mounted. Its
independent community updater UI is consequently unavailable. This does not
disable the managed Augmentor product's separate update workflow. Core DSH
telemetry switches remain set; the separately inspected DeepSeek session-log
setting is also `enabled: false`.

The remaining inspected legacy extensions had no additional matched analytics
exporter. Adaptive Reasoning's file called `telemetry.js` writes a local rotated
JSONL diagnostic file; the name alone is not evidence of an upload. Embedded
Handy explicitly disables its independent update checks. A final 30-second idle
trace attached successfully to 24 live MCP/Handy/Breeze processes and followed
181 task files: no IP calls were observed. Audio recording, downloads, remote
ASR/TTS and physical speech were not activated by this audit.

## Operational limits

The Harness preview's separate memory connection was already unavailable before
maintenance and points to a different local endpoint. It was not redirected to
the running container: that would require a deliberate memory-destination
migration. Its journal and prior data are preserved.

Configured model requests, account refresh, explicit search/fetch, downloads,
visited websites and arbitrary extension code have separate destinations. These
checks establish the recorded bounded workflows; they do not certify every
website/provider, future package version, the full desktop browser or another
OS. Repeat qualification when the MCP/browser/runtime versions or configuration
change. macOS/Windows installed instances were not changed in this local Linux
maintenance. Private operational traces, credentials, paths and raw memory data
remain outside the public repository.

See [managed Pi privacy](PI-PRIVACY.md), [memory operations](MEMORY-OPERATIONS.md)
and the [sanitized evidence summary](../release/telemetry-audit-20261021.json).
