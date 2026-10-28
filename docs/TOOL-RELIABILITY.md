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
screen. Actual mixed-scale capture/input acceptance is recorded below; mapping fixtures
remain distinct from those physical checks.

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

Strict TypeScript checking and full builds pass. The broad Python run passes
1,391 cases with 46 platform skips; the later response-stream cohort passes six
cases. The broad Node run at the final control-repair source contains 2,271 cases:
2,202 pass, 31 fail and 38 skip. Matching original GUI failure names also occur in
the pre-repair integrated source under the same environment. This is evidence
against a repair regression, not a claim that those tests are healthy.

The exact modern Linux and Mac candidates each pass 57 runtime cases; retained
model/effort UI checks pass on both, with the Linux queue proof separate. Actual
registered Windows tools pass mixed Unicode/emoji input, selection/replacement,
extended Home, stale-token rejection, Stop and three consecutive 256-codepoint
runs. The normal x64 and ARM64 Windows preview installers pass staging, sealing,
rendered Native launch and dictation checks. Source06c22298 also passes the real
bundled-DSH/Qt integration on macOS14 and26, including approval, question, shared
Browser pipe, exact fork and continuation.

An additional native DSH bug was found in that integration: transient assistant
frames can omit timestamps. Native Desktop now preserves supplied timestamps
and omits absent ones, continuing through terminal events rather than disconnecting.
The compatible Mac client retains its older progress UI and session projection.
No SDK or model switch is needed for that correction.

## Personal installed rollout

Linux Native runs the sealed release `20261027-210702-a9e1b87b`; its selected and
running roots agree. Its control overlay retains SDK0.85.1 and product0.2.11;
the modern Harness runs `20261027-211639-127f8221`, product0.2.13/SDK1.1.
The Mac Native app remains in `/Applications/Augmentor Agent Desktop.app`, product
0.2.12 with its existing SDK/UI/dependencies; its source06c22298 timestamp delta
is separately recorded over the control overlay. The Mac Harness remains
`20261027-tool-repair`, SDK1.1 with its actual retained model/effort UI.
These are explicitly inventoried personal compatibility overlays, not clean
whole-source bundles or version-number parity claims.

The Mac's 14 original Native chats and 28 session files remain preserved, with
identical model catalog and no configuration-file changes during the last update.
Original modern-Harness conversations/journal prefixes on Linux and Mac are
preserved. Linux's original 1,356 DSH sessions and 2,569 session files are retained.
Cold backups and exact private receipts remain outside Git. Actual unchanged-model
Native DSH write/read checks now pass on Linux (13.18s) and Mac (5.87s), with no
stream errors and observed terminal events. Earlier actual modern-Harness model
checks also pass on Linux and Mac. Authored diagnostics retain their own history.

Personal future defaults and eligible root conversations are Full; protected
archive/child scopes retain their explicit boundaries. The inactive classic Linux
Pi profile was migrated under its real startup lock: 13 Ask scalars changed,
nine Full records and all22 journals/model settings stayed unchanged. No old tool
or model actions were replayed. Two maintained Linux DSH role pins and the private
Docs skill were corrected with exact backups, preserving custom presets.

The actual owner Chromium profile has loaded the updated extension through its
normal reload control. Trusted accent/CJK/emoji input, independent page readback,
single-use observation rejection, selection/replacement and Stop pass on an
authored local page. The existing extension key/version and profile identity are
retained. Mac Brave and Windows owner-browser adoption remain separate checks;
real Google Docs saved/style readback is not claimed.

Linux's portal grant is now reusable for all three selected monitors. Actual
capture and independent Qt-button clicks pass on the HDMI mixed-scale screen and
DVI screen. The portrait screen captures correctly; its test click was refused
because existing owner EDGE dock windows cover it. No owner panel received input.
The selected KDE correction binds size-only portal streams injectively to fresh
compositor outputs and stops sharing if the topology changes. A subsequent
optional-accessibility correction is under review/qualification: complete absence
of field metadata can use an observed active window/title, while partial reads or
known focus changes refuse. It reports window binding honestly and keeps Stop.
macOS still reports Screen Recording disabled, with Accessibility granted. The
owner explicitly deferred those remaining OS grants until the other work finishes.

Windows source06c22298 is installed through the normal preview installer. Both
independent full payload scans, cold-profile comparisons, same-target junction
checks and fixed local health passed before canonical update completion. The
installed registered physical tool chain passes capture, Unicode/emoji, chords,
replacement, Home, single-use targets, Stop and 256-character input. Models,
saved harness choice and original sessions are retained. A grouped model-picker
font bug and missing proactive saved-backend restore were subsequently diagnosed;
their reviewed replacement build is pending installation. Restore is limited to
an existing selected managed home and matching service identity, uses the existing
admission/idempotence checks, and leaves model/profile provisioning unchanged.
Ordinary native, Browser and background login launch restore that selected DSH
and voice service once; failures go to private logs while the UI can still open.

The CI matrix is not wholly green: Windows command-job fixtures still report
memory-lease warnings/timing failures; broader qualification jobs have their own
status. Linux public packaging intentionally retains its open Office source/rebuild
qualification gate, and a separate cached-component installation timed out. These
are retained limitations, not suppressed checks or public-release approval.
