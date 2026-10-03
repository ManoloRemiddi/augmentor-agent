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

## Temporary password fixture preparation

`release/gnome-password-fixture.py` is root-only test instrumentation restricted
to the marked Ubuntu24.04 QEMU comparison guest and its dedicated UID1000
account. An explicit clean source and selected artifact hash must match the
private selection. The original randomly generated Cloud account password is
unavailable; a temporary synthetic credential is needed for a real password
test. The helper requires the original Cloud password hash to match before any
dispatch, and retains the complete original shadow image and account age in a
root-only private journal. Credentials and shadow contents are never returned.

Preparation uses native `openssl` and one `chpasswd` invocation. Restoration
uses the original hash and, if needed, a separate native `chage` operation. Each
command has a pending receipt before dispatch. A lost reply requires inspection;
the helper never repeats an uncertain operation. Foreign account changes refuse
restoration, and the full original shadow image must match before restoration
is reported. Seven focused Linux tests cover account preservation, invalid
requests, concurrent changes, interrupted restoration and a real child timeout.
These are source checks. The helper has not changed a guest credential or
established password authentication, locked shortcut behavior or recovery.
An actual run also needs the full VM/native/managed-artifact admission and
observed normal GNOME password entry; administrative unlock is separate cleanup.

The [October3 actual password checkpoint](../release/qualification/next-targets/20261003-noble-real-password-authentication-partial-pass.json)
records the subsequent owned Ubuntu GNOME46 run. One wrong password produces the
native failure screen and PAM failure record; one correct password unlocks
normally. No administrative unlock is used. The same accepted idle main PID5599,
mapped native window, source368 selection and Shell owner survive. The observer
refuses while locked; a fresh unblocked observer has a new epoch after unlock.
Full native/managed/runtime checks pass before and after. The complete original
account database and password age are independently verified restored, both
temporary readable credentials removed, and PAM/GDM configuration preserved.

This is partial qualification: the first F9/F10 lock sequence has no registered
custom shortcuts because the previous proof restored its original empty registry.
Its unchanged app state does not qualify shortcut suppression. F10 opens the
native password context menu, dismissed once without entering a credential.
The retained observer worker exits normally before password entry, so its stale
instance is not read after unlock. A fresh run needs verified registrations,
both running windows and the retained stale-instance check. No installed payload
is patched, key/password action replayed or production input enabled.

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

## Actual Ubuntu application Settings acceptance

[The maintained installed rerun](../release/qualification/next-targets/20261003-noble-actual-settings-pass.json)
passes on selected clean368 with073c429 proof source: both real opted-in windows,
four Save clicks, four collision clicks, native readback and conflict refusals.
Settings and foreign bindings restore successfully. No selected payload is
patched. Normal global shortcut delivery and authenticated password-lock/reboot
acceptance remain separate; the original pre-Save loader failure is preserved.

## Selected GNOME artifact reboot proof

[`prove-gnome-selected-reboot.py`](../release/prove-gnome-selected-reboot.py)
adds a separate Ubuntu24/Fedora44 owned-VM reboot entry. It requires explicit
source and artifact digests, the private host/QEMU/key/disk contract, verified
guest security/native package/runtime/inventory, a normal idle service-owned
main window and no secondary window or pending Settings journal. It records an
exclusive private receipt before one reboot request. The request transport allows180 seconds for the full pre-mutation immutable
runtime verification and the bounded15-second reboot child. A timeout or lost SSH
reply never repeats that request. Recovery requires a changed kernel boot ID,
the identical selected contract and an actual service-owned Wayland app with
the GNOME observer available. Three focused cases cover retained pending
evidence and real transport timeout/lost reply without redispatch. Installed
current-artifact reboot acceptance is pending. This proof does not test password
authentication, locked shortcuts, a connected harness or desktop input.

Example, from the canonical checkout, with a fresh private output:

```sh
python3 release/prove-gnome-selected-reboot.py \
  --target ubuntu24 \
  --directory outputs/linux-rollout/ubuntu24-gnome-mesa2-vm \
  --identity outputs/linux-rollout/ubuntu24-gnome-vm/id_ed25519 \
  --source <exact-selected-source> --artifact <exact-selected-inventory-sha256> \
  --output outputs/linux-rollout/<fresh-run>/reboot.json
```

## Current Ubuntu selected reboot acceptance

[The installed reboot proof](../release/qualification/next-targets/20261003-noble-selected-reboot-pass-shortcut-runner-timeout.json)
passes with command exit0: one request, changed boot identity, identical selected
clean368 source/artifact/runtime/inventory, clean native audit/active AppArmor and
an actual service-owned Wayland app/observer. The fixture uses automatic login
and remains offline with its normal Connect DSH modal. Password authentication
and locked shortcut delivery are not tested. The interrupted outer-bounded
shortcut run is retained separately and cannot establish native key acceptance.


## Current Ubuntu native shortcut acceptance

[The maintained native shortcut command](../release/qualification/next-targets/20261003-noble-native-shortcuts-pass.json)
passes with normal exit0 on the same immutable clean368 selection. QMP input
through the owned VM keyboard hides/shows main and secondary independently,
cold-launches secondary, accepts an idle main close and launches a new
service-owned main through the canonical shortcut. Main PID1435 becomes5599;
secondary3610 remains independent and then closes normally. The run-owned
settings journal restores and foreign entries are preserved. Independent final
readback confirms the same main idle, no secondary and no pending journal.
Standalone Qt form Save is recorded separately from the earlier passing actual
application Settings phase. The previous overall-runner timeout remains failed.
This establishes native VM shortcut delivery, not physical host keyboard,
password authentication, locked shortcut behavior, connected harness/model or
production GNOME input acceptance. The selected-artifact reboot pass remains a
separate command and checkpoint.
