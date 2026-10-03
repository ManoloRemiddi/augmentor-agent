<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

## October 3 current KDE proof guards

[The proof guard checkpoint](../release/qualification/next-targets/20261003-kde-native-consent-proof-guards.json)
adds explicit RPM/dpkg queries and verifies the selected managed inventory,
native source/target/version and package audit before starting the executor.
The driver requires the exact owned VM marker/name and dedicated account.
Native consent must belong to the live portal process and be its sole focused
window. Allow/deny labels and points come from an actual screenshot whose hash
is retained; changed geometry refuses input. `--observe-consent` captures the
pending dialog and presses Stop without granting sharing. Fifteen focused guard
tests pass. Fedora44 KDE native clean368 installation passed with SELinux
Enforcing, but its original60-second complete bootstrap failed. A separate
51.009-second readiness measurement does not establish that failure's cause.
Fresh matching2035 installation and consent/input/visible Stop acceptance remain
open; these proof changes do not qualify another desktop or enable GNOME input.


# Linux desktop control preview

Pi, DSH and opt-in Codex development source use the same per-user desktop executor. It captures a consented screen
and can click, send a short key chord or type up to 256 ASCII characters into an
accessible focused control. DSH and Codex personal Browser chats can use this executor; the Pi Browser role
retains its separate tool scope.

The current target is Debian 13, KDE Plasma Wayland, one active monitor and a
model configured for image input. The desktop package supplies the capture/input
dependencies. The Augmentor window and independent Stop control use XWayland;
the tested target application, Kate, uses native Wayland. Other desktops,
multiple monitors, password fields and non-ASCII typing are not supported.

Codex setup first requires an explicit successful **Check image response**, then
a new conversation. Its consent, target-token, durable-call and cleanup behavior
and actual disposable-VM evidence are described in the
[Codex desktop checkpoint](CODEX-INTEGRATION.md#consented-desktop-tools-and-plasma-vm-evidence).
This is development source; Codex packaging, macOS/device and complete product
qualification remain separate gates.

## October 2 capture compatibility checkpoint

The pinned [GNOME control plan](LINUX-GNOME-CONTROL-PLAN.md) records portal
negotiation, logical coordinate mapping, owner/capture cancellation, responsive
Stop and eight real graphical acceptance cases. The separate
[Cinnamon contract](LINUX-CINNAMON-ADAPTER.md) includes actual Mint password-lock
and reboot evidence plus its activatable screensaver lifecycle. Both remain
source plans; GNOME/Cinnamon capture and input are not enabled or qualified.

Actual Leap 16/Python 3.13 native tests exposed gst-python's context-managed
`StructureWrapper`. RGB-frame validation now keeps its parent caps alive through
that context, while retaining exact RGB format, integer positive dimensions and
complete padded-row checks. Direct Structure APIs remain supported. Real Arch
and Leap suites run 687 tests with 2 Mac-only skips, including incomplete-buffer
and wrong-type refusal. See the [distro proof scope](LINUX-DISTRO-ROLLOUT.md#october-2-actual-noble-keyboard-and-next-runtime-acceptance).
This change does not alter consent, target identity, cancellation or visible Stop.
GNOME 48 source compatibility and Noble keyboard/lifecycle acceptance still leave
full GNOME capture/input qualification open.

## Using it

1. Open the intended application and a harmless test document. Enable
   accessibility for that application. Configure an image-capable model in Pi,
   or declare image input in the DSH provider configuration.
2. Ask Augmentor for a bounded action. The OS opens **Remote control requested**.
   Choose **Share** yourself to allow capture and keyboard/pointer input. If the
   dialog opens behind another window, select it with Alt+Tab. Declining or
   cancelling it leaves sharing closed.
3. Keep the independent **Stop desktop control** button visible. Either that
   button or chat **Stop** closes sharing and releases held keys. A turn ending
   also releases its owned connection; five idle minutes close unused sharing.
4. Inspect the application or saved file to verify the result. Input dispatch
   alone does not prove success. After cancellation, text may be partial; an
   uncertain action must not be replayed automatically.

Each action requires a screenshot with a fresh compositor-owned window identity.
Its target token expires after 30 seconds and is consumed once, including refused
actions. The executor rejects a changed or covered target, changed monitor
geometry, inaccessible keyboard focus and another chat's ownership. These checks
reduce accidental input; they are not an operating-system sandbox.

Covering windows from the same process now participate in scene invalidation and
click refusal. A dialog appearing after capture consumes the stale target without
dispatching input; a stable dialog only blocks points it covers. The
[Linux rollout](LINUX-DISTRO-ROLLOUT.md) also adds a read-only GNOME 50 observer
with a private compositor proof. Its tracked-scene/point checks remain separate
from input qualification; the current GNOME control registration stays gated.

Screenshots go to the selected model and may remain in the harness conversation
history. The executor itself writes no screenshot file and does not use the
clipboard to type. See DATA-AND-SUPPORT.md for data locations and deletion limits.

The Pi development runtime now also offers a [bounded desktop
specialist](DESKTOP-SPECIALIST.md). Its screenshots stay in a separate worker
context and private local evidence files; the coordinator receives a short
structured result. This has different retention behavior from direct desktop
tools. The native executor and its platform limitations remain the same.

## Reproducible evidence

`scripts/vm-desktop-proof.py` drives a disposable full Plasma Wayland VM. It
checks declined consent, Stop during consent, target/owner/replay refusals, actual
Kate Save As contents, and interruption of a long write through the independent
Stop button. `--scale` selects 1, 1.25 or 1.5. By default it runs the installed
executor; `--source` explicitly records candidate source staging instead.

Supply `--expected-source`, `--expected-target`, `--expected-marker` and
`--expected-vm-name` for the exact owned guest. Installed runs resolve and verify
the managed selection. The only accepted account/UID pairs are `beta`/1000 and
`augmentor-complete-proof`/1001. Start with `--observe-consent`, inspect its
retained native screenshot, and record the actual dialog's button labels and
relative coordinates in the observation JSON. A later bounded acceptance run
requires `--consent-observation` pointing to that screenshot-bound record;
changed native portal package, window identity or geometry refuses the click.
The observation phase qualifies only pending-consent cancellation.

`scripts/vm-desktop-engines-proof.py` uses actual Pi and DSH SDK tools with a
deterministic HTTP model. A private SSH socket forwards only desktop operations
to that VM, while host desktop autostart is disabled. It verifies actual image
bytes reaching the model, exact saved-file text and cancellation. The model
fixture supplies known coordinates; this is not a visual-reasoning benchmark.

The exact tested candidate and scales are recorded in PRODUCTIZATION-STATUS.md.
Independent hardware/users and model quality remain beta gates. The VM uses a
consistent Nehalem CPU model: `release/vm-avx-mask-proof.c` reproduces a masked
AVX2 load fault in QEMU 10.0.11 TCG that also crashed Qt/Breeze. The test avoids
that emulator defect without changing Qt or the user's system.

### Fedora KDE Wayland proof children

[The current helper checkpoint](../release/qualification/next-targets/20261003-kde-wayland-proof-helper-correction.json)
keeps the executor'sxcb banner environment, while the boundedkscreen-doctor
child uses the actual Wayland session. Its own20-second timeout reaps that
child. Native portal matching reads full compositor PID/application/id/title/
geometry through KWin.execute; the product controller is unchanged. Eighteen
focused proof guards pass. Earlier pre-consent timeout remains recorded and
actual consent/input/visible Stop acceptance remains pending.
