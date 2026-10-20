<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Harness on personal Apple-silicon Macs — October 20, 2026

## Installed artifact and scope

The 16 GiB MacBook Air and 32 GiB Mac Mini select the existing macOS artifact
built from `38fabc4d8643a12994151c9f60b1406baaaa0809`, product 0.2.13,
Pi 1.1.0, Node 24.19.0 and Python 3.12.13. Its application inventory SHA-256 is
`7e16b745b1e2ba8d88452431406db8dbff212a65f3c3b5d16370984463c9a299`.
The macOS defaults/Search implementation is tracked in
[PR #51](https://github.com/ManoloRemiddi/augmentor-agent/pull/51).
This documentation does not merge that branch or qualify a new application build.

The Air received one existing arm64 application artifact over authenticated SSH;
all 6,122 inventory files verified before activation. It has an independent,
private profile. Existing approved model declarations and picker settings were
provisioned privately; no Mini conversations, projects, browser credentials or
OAuth tokens were copied. No build ran on MX and no additional complete app copy
was retained there. Both Macs retain their ordinary Applications entry.

## Startup and reopening

Open **Applications → Augmentor Harness**. The launcher follows the stable
`~/Library/Application Support/Augmentor Harness/current` selection. Runtime,
configuration, data and histories live in separate directories beneath that home;
the runtime socket is in a private, user-owned temporary directory.

Two enabled graphical-user LaunchAgents implement startup:

| Label | Behaviour |
| --- | --- |
| `com.augmentor.Harness` | RunAtLoad and KeepAlive; starts the selected runtime with its explicit bundled environment. |
| `com.augmentor.Harness.open-at-login` | RunAtLoad; opens the Applications launcher after graphical sign-in. |

The launcher can bootstrap a missing service and waits for the existing owner
socket. The profile retains its browser address and operator login across service
recovery. Startup occurs after the user signs in following reboot; it is not a
pre-login system service. An offline model endpoint does not require changing
the selected release or deleting profile data.

For maintenance, preserve active work and drafts. `host.shutdown` performs its
own guarded preparation; do not call `host.prepareShutdown` and then call
`host.shutdown`, because the second preparation is correctly refused once the
owner is quiescing. An already-prepared owner can be retired through its owning
LaunchAgent and bootstrapped again. Never kill an unrelated process to reclaim
a port or socket.

## Components and connections

Metafolder grouping and keyless Web Search/Fetch are enabled. Prompt library,
in-input Improve prompt, Model Picker, Context Insights and Adaptive Reasoning
are bundled application components. Improve prompt requires an eligible nonempty
draft. A new personal prompt library does not automatically import another
machine's saved prompts. Existing Mini groupings and conversation histories stay
intact.

DeepSeek and the existing GX10/Olares model declarations are available without
changing server model, context, precision or concurrency settings. Both local
models are pinned. Their private LAN endpoints require the relevant home network
or an independently working remote route; installation does not create a public
gateway.

Wiki Tools/Skills remain disabled on macOS: their descriptor-relative filesystem
and operation-receipt adapter still requires Linux qualification. Do not remove
that platform guard merely to display an enabled plugin. Voice expansion and
broader desktop/browser-extension adapter acceptance are separate work.

The owner explicitly deferred OpenAI/Codex subscription setup on both machines.
Both pending SDK sign-ins were cancelled and model settings reconciled; neither
owner remains blocked by an unfinished sign-in. No subscription credential was
copied or represented as connected. Later use the original Models account dialog
and supported Pi OAuth flow, while the owner is idle.

## Air connectivity and power

Tailscale was initially offline while LAN SSH remained available. Its login-item
helper was already enabled. The Air's configured idle sleep was one minute on
both mains and battery; that can suspend network reachability, but no complete
disconnect root-cause or sleep/wake cycle was established.

At the owner's explicit choice, an enabled user LaunchAgent
`com.augmentor.AirAwakeOnAC` runs `/usr/bin/caffeinate -s`. Its system-sleep
assertion was observed. It prevents idle system sleep on mains power while
retaining battery and display sleep settings. It does not promise network access
while powered off, during forced/lid sleep or when the network is unavailable.
The final Tailscale read reports Running, online and no health warnings.

## Actual acceptance and remaining limits

- Air: 17/17 focused server, browser-access and setup checks pass with a clean
  fixture environment. An earlier invocation inherited the live Harness-mode
  variable and correctly refused nonprivate fixture configuration directories;
  the product path checks were not weakened.
- Air: real SDK replies from DeepSeek, GX10 and Olares returned READY. Initial
  calls reported connection errors; subsequent endpoint/TCP checks and real
  completions passed without altering model-server settings. No specific cause
  is asserted for those initial errors.
- Air: one real default-model AH installation conversation returned READY with
  zero tool calls; it was archived and its history survived service recovery.
- Both: browser HTML and authenticated operator access, enabled grouping/Search
  and the Prompt library service passed. Automatic launchd recovery produced a
  new runtime PID while retaining the same browser link, selected model and
  saved histories. Four current Mini conversations and the Air's one installation
  conversation verified preserved. No inference or tool action was replayed by
  the recovery check.
- The first Air restart wrapper incorrectly prepared shutdown twice. The guard
  refusal was retained; the same prepared service was retired/restarted through
  launchd, and the corrected recovery check then passed without another model
  submission. This was a verification-wrapper error, not an application fix.
- Both Applications launchers were opened; launch-at-login jobs validate and are
  enabled. A new physical reboot, lid-close/wake test and final visual inspection
  of the remote Mac screens were not performed.

Private machine receipts and bounded logs remain with each installation, outside
public Git. Never include model keys, authorization links/codes, owner histories
or private endpoint values in portable installation evidence.
