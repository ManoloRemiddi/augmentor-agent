<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Owned GNOME shortcut qualification

The qualification scripts accept only the explicitly marked Ubuntu 24.04 Mesa
comparison guest or Fedora 44 GNOME guest. They verify the ordinary test user,
QEMU identity, OS, security mode, clean source and selected artifact before
using installed code. Managed roots require a matching verified artifact hash.
Ubuntu resolves the interpreter through the selected artifact's reviewed
runtime policy; Fedora requires the native `/usr/bin/python3` contract. A cached
`selected-python.txt` is never an interpreter authority.

`release/gnome-vm-qualification.py` is shared test instrumentation. Stage it
beside `release/prove-gnome-vm-lifecycle.py` when using the guest lifecycle proof.
Run the latter with the interpreter returned by `verified_profile(target,
source)`, an explicit `--target ubuntu24` or `--target fedora44`, and the full
clean source SHA through `--source`. It verifies the selection again after the
proof. Its lock test uses administrative `loginctl` lock/unlock; it explicitly
does not qualify password authentication, shortcut delivery while locked or a
reboot. Those remain separate real-session cases.

## Actual Settings controls

Normal app launches reject every UI test request. The existing hidden
`--ui-test-control` startup option enables bounded controls only in that
process. Sending the option to an already running singleton cannot enable it.
Both actual fixture processes must be started explicitly with the option for
this phase. Keep the ordinary service/canonical launch phase separate.

The `shortcut-settings` test operation opens the normal Settings dialog in the
actual app, selects one key combination through its actual `QKeySequenceEdit`,
clicks its Save button and waits for the normal asynchronous worker callback.
It exposes only `open`, `inspect`, `choose`, `save` and `close`. It refuses hidden
or busy windows, drafts, unrelated dialogs, maintenance, stale binding labels,
changed key selections and saves already in progress. No widget lookup, code
evaluation, global input or arbitrary Settings mutation is accepted. The
window layout, shortcuts adapter and native Save behavior are unchanged.

From the public repository root, the host driver accepts:

```bash
python3 release/prove-noble-gnome-shortcuts.py --directory outputs/OWNED-VM --identity outputs/OWNED-IDENTITY --target fedora44 --source CLEAN_SOURCE_SHA --output outputs/NEW-PROOF/settings.json --app-settings-only
```

Use `--target ubuntu24` for the marked Mesa comparison guest. The
historical filename is retained for existing callers. The output must be a
new file beneath `outputs`; earlier evidence is never overwritten. The host
checks its own QEMU process, dedicated disk, QMP socket, network forward and
absence of host device/filesystem attachments, stages the hashed guest helper,
then resolves the selected runtime afresh.

This phase requires both existing windows to be idle, visible and explicitly
opted in. It saves both launcher rows in each real window, refuses foreign and
other-instance collisions, confirms native settings and restores the owned
settings journal without overwriting concurrent foreign changes. It sends no
QMP keys and makes no launch request. A stalled or uncertain Save is not retried.

Before uploading guest helpers or any dialog/settings operation, a pre-existing
journal refuses the run and preserves its original staged recovery scripts.
Every host run generates a fresh 256-bit proof token and retains it with
the exact source, target, interpreter and script hashes in a private
`settings.json.run.json` receipt beside the requested output (using that
output's name). Every guest action and worker receives the same token. Journal
creation is exclusive; read, update and restore require both the exact source
and token. A stale journal at the same source SHA belongs to its original run
and cannot be restored by a later run's `finally` cleanup. Legacy journals
without a token are also refused.

After interruption, retain that receipt and the guest journal. Recovery uses
the already staged guest script's `restore` action, its recorded target/source
and `--proof-token` from the original receipt, with the verified selected
interpreter. The same package, guest and foreign-settings guards still apply.
This restores only that run's journal; it does not begin a new proof or replay
an uncertain input/Save. A different receipt, changed source or foreign
settings refuses recovery and preserves the journal for explicit review.

Omit `--app-settings-only` in a separate normal-process phase to run the retained
standalone shortcut-form setup followed by actual QMP global shortcut delivery:
main hide/show, independent secondary cold launch/hide/show, idle main close and
canonical shortcut cold launch. This phase requires only the main instance at
entry. The report distinguishes standalone-form Save from actual-app Settings
Save and records the guest/helper hashes and verified selected contract.

## Artifact and acceptance boundaries

Build clean target artifacts containing the bounded UI hook before running the
actual Settings phase. Fedora needs its matching native RPM/runtime; Ubuntu
needs its matching package/artifact and verified selected managed interpreter.
Do not patch a selected root in place. PySide6 QtTest is a test-phase prerequisite
for choosing/clicking widgets; ordinary launch does not import it through these
controls. Preserve the authenticated Noble Mesa comparison provenance.

Source-level validation on 3 October 2026 passed 36 focused tests in the owned
Leap complete-package container with Python 3.13.14 / Qt 6.9.1, offscreen, as its
ordinary synthetic user. Tests include the actual dialog and asynchronous
callback transport, stale-state/conflict guards, both runtime contracts and the
GNOME 46/48/49/50 shortcut profiles. No installed desktop or VM acceptance was
performed for this source change. The matching Ubuntu/Fedora artifact runs,
reboot, real password lock/unlock and locked shortcut non-delivery remain open.
GNOME desktop input stays disabled; these proofs do not qualify model, portal
input, physical audio or owner hardware.

## Source-Qt proof child contract

[The installed failure/correction checkpoint](../release/qualification/next-targets/20261003-noble-settings-source-qt-proof-child.json)
records both actual clean368 app processes on the verified Noble source-Qt
selection. The original Settings helper failed importing its Qt key codec before
any Save; its run-owned journal and foreign bindings restored successfully.
The helper now starts only its two bounded Qt operations in a separate child,
using the selected runtime's verified pre-exec environment. The parent still
checks guest/source/target/security/inventory/interpreter and journal ownership;
entry continues refusing inherited loader overrides. The120-second child limit
and no-retry behavior remain unchanged. Six focused cases include a real ELF
loader regression and failed/uncertain child handling; eleven existing selection
and journal cases pass. Actual installed rerun and ordinary shortcut delivery
remain separate gates. Neither selected payload nor visible UI is changed.
