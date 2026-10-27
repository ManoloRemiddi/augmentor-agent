<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->
# Browser and Desktop tool repair — October 27, 2026

The [diagnosis](TOOL-FAILURE-AUDIT-2026-10-27.md) identified separate browser input,
permission adoption, local-preview and foreground-shell failures. This repair
keeps the owner's chosen inference models and saved conversation formats.
Installation and live acceptance are separate from source qualification below.

## Shared personal control

Pi Browser and Desktop expose the same personal file, shell, approved resource,
skill and desktop tools. Execution follows the selected conversation policy.
Full access dispatches without application action approvals. Read Only and Ask
remain selectable and are enforced at dispatch, including a policy change during
an in-flight model response. Delegated jobs retain their parent's explicit grants.
There is no additional browser-surface denylist.

The owner's explicit full-control instruction authorizes setting their personal
future default and existing active root conversations to Full access during the
guarded installation. Keep archived histories, child grants and model settings.
Do not silently change other users' installations or the product's fresh default.

The connected browser executor belongs to the existing native messaging host.
It uses the existing same-OS-user transport, a private per-host registry and an
exact executor identity when several browsers are connected. It starts no agent
loop. The existing DSH, Pi and Codex lifecycle remains authoritative. The per-chat
owner is coordination between conversations; it is not isolation from programs
already running as this OS user. Stop broadcasts only release that owner's
trusted browser targets and never repeat input. Native-port disconnect, idle
expiry and normal agent completion release debugger connections.

`browser_capabilities` describes the actual installed Chrome permissions and
rich-input route. With several native hosts it returns their capabilities and
tabs so the agent can select the observed `executorId`. Ordinary DOM tools remain.
Trusted tools add exact-tab observation, keyboard chords, text and pointer input
for canvas/frame editors. An observation has a single-use token, document,
viewport and focus identity; stale targets require a new observation. Pointer
centres focus a location, so the agent must deliberately position the caret
before inserting text. Input acknowledgment is dispatch, not task completion.

The extension adds Chrome's `debugger` permission and persistent screenshot host
access. Its key/extension identity and storage are preserved. Chrome may require
one re-enable/reload of the updated extension. Do not fabricate that grant by
editing Chrome's preferences. Native OS grants likewise remain real: Linux may
ask once for the selected monitors and input; its rotating restore token requests
persistent reuse. macOS retains Screen Recording/Accessibility. Windows uses its
ordinary signed-in desktop and respects secure desktops and target integrity.
The independent desktop Stop banner remains.

## Bounded foreground work and generated files

Pi shell calls without an explicit timeout receive a default 120-second SDK
execution deadline, including calls nested inside codemode. Set
`AUGMENTOR_FOREGROUND_SHELL_SECONDS` to another finite duration or zero to disable
this default. Invalid values fall back to 120 seconds. An explicit tool timeout
is preserved; its SDK validation still applies. Partial output/side effects are
retained, and a timeout never replays a command. Use existing bounded jobs for
long work. DSH already supplies its bounded/background shell mechanism.

`open_artifact` uses the existing Harness server and path/version validation to
publish an immutable, short-lived local HTML/text snapshot. Its artifact URL has
its own random capability, without the operator bearer. The response is no-store,
nosniff and sandboxed; scripts cannot read the Harness origin or fetch network resources.
A generated page can still navigate its own tab. Opening returns after dispatch. It does not wait for Chromium to exit or
assert that the requested page loaded. Prefer the connected signed-in browser;
fall back to the supported system opener only when no executor is connected.

The pilot launcher keeps private state and explicit IPC locations while retaining
the graphical `XDG_RUNTIME_DIR`. `AUGMENTOR_DESKTOP_SOCKET` can explicitly isolate
a desktop-test endpoint without moving Wayland or PipeWire into a fake runtime.
The default installed endpoint remains stable.

## Platform adapters and evidence

Linux selects the shared stream overlapping the active application, maps portal
compositor geometry independently of screenshot pixels, and rejects ambiguous
or changed topology. Missing stream identity is allowed only for one actual
screen. The first portal grant and mixed-scale live click acceptance still need
the actual desktop; authored mapping tests are not that proof.

Windows uses the existing authenticated named pipes and kernel locks. Its new
adapter observes the physical foreground window/displays, captures its monitor,
and sends input with per-thread DPI awareness. It refuses a changed or covered
target and elevated/secure desktop access, releases keys on Stop, and paces
Unicode character batches to preserve order in real Qt targets. The physical
VZmore proof passed 1920×1080 capture, mixed Unicode/emoji text, selection and
replacement, consumed-token rejection and Stop. Seven native pipe/lock cases
also passed. Another-user account creation is limited to the existing disposable
CI fixture, not the owner's PC. Multiple physical Windows displays are not
claimed by the one-display proof.

Independent Opus5.5 scope, reconciliation, browser code and desktop code reviews
ran through the authorized Claude subscription. Recommendations and lead
decisions are in [the plan](PLAN.md#october-27-repair-integration). Later desktop
review receipts also list Opus4.8 usage; no exclusive model-use claim is made.
Initial Qt Unicode tests failed and were corrected before promotion.

Strict TypeScript checking and full builds pass. The broad run completed 2,265
cases: 2,190 pass, 39 fail and 36 skip at that intermediate source. Missing test
Python/QtTest and separate browser-test dependencies were corrected. Most
remaining GUI failures exercise earlier composer/sidebar/origin behavior;
the owner-restored layout is preserved. A focused core rerun and corrected cases
cover both policies, real SDK/browser tools, session continuation and crash
recovery; record final counts and exact staged-source identities before activation.
No incomplete suite is presented as a clean pass. Real Google Docs saved/style
readback and installed extension adoption remain separate acceptance gates.
