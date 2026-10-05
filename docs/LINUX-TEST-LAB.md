<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Persistent Linux test machines

The October 5 host crash left five reusable guest installations and their test
reports on disk. The recovery setup saves independent OS checkpoints on the DATA
drive and registers persistent machines in the owner's **libvirt user session**.
Virtual Machine Manager can show them after a host restart. It does not depend on
a running chat, an old process ID, or a temporary QEMU monitor socket.

Actual one-at-a-time recovery observations now pass boot, preserved SSH host
identity, readable root filesystem, installed native-package query and normal
shutdown for all five machines. KDE passes with the separately corrected management
account/shutdown path; its original ACPI timeout and wrong-account failure remain
recorded. Mint reports a failed `casper-md5check.service`; its cause is not yet
established. Leap's system was still `starting` at its read-only observation, with
no failed units. These are boot/access/shutdown checks, not full OS or desktop
application acceptance. All machines were left off at that recovery checkpoint.

The owner subsequently resumed testing with the existing64 GB and decided against
installing additional RAM. The existing one-machine guard and reserves below stay
in force. A new offline Mint checkpoint/writable generation, fresh boot, full
preservation audit and staging of two matching packages now pass; see the
[resume checkpoint](../release/qualification/next-targets/20261005-mint-resumed-preservation-checkpoint.json).
Mint is the sole active lab VM at that observation. Native adoption and graphical
acceptance are still pending; the previous generation and checkpoint are retained.

The subsequent [held-session admission](../release/qualification/next-targets/20261005-mint-held-session-admission.json)
records a strict fresh full audit after a cross-phase background-state refusal.
Keeping an ordinary management SSH/PAM session open avoids relying on a user
manager's lifetime between commands; it does not guarantee that background state
will remain unchanged. No service, routing, linger or metadata-comparison policy
changes. Actual before/after equality remains mandatory. Record normal control
session exit separately from the held-session full audit; logout/reboot is a new
scope. A private prefix account preview passes without changing any live account.

This is test infrastructure. A recovered OS disk does not certify a new Augmentor
release. Existing compatibility limits remain in [Linux rollout](LINUX-DISTRO-ROLLOUT.md).

Subsequent October5 collection recovered Mint's existing startup diagnostic and
ran one separate strict runtime-validation timing check, then shut it down normally.
The [diagnostic record](../release/qualification/next-targets/20261005-mint-browser-startup-diagnostic.json)
retains the original failed graphical scope; it is not a new acceptance run.
All11 hosted checks pass at1ffb509. To restore the host root-space reserve, three
completed build archives were copied to DATA with content, mode, owner, modification
time and extended-attribute verification, retaining their old paths as symlinks.
Their detailed migration receipts remain private; no VM disk moved. Original
inode/change-time identities differ, so historical physical-file identity checks
must not be relabelled as current observations.

The separately reviewed private KDE proof transport passes actual libvirt monitor
name/status and dedicated proof-user SSH with the preserved host-key alias. Its24
synthetic checks cover refusal/interface behavior. The [transport observation](../release/qualification/next-targets/20261005-kde-libvirt-transport-readonly.json)
records the source and boundary: no input or product work, public controllers unchanged,
normal shutdown afterward. A new graphical cohort still needs fresh installed-source,
native-session and consent admission. Old direct-QEMU wrappers cannot be replayed
against these libvirt machines.

## Storage and machines

The local lab is `/media/manolo/DATA/augmentor-test-lab`, mode 0700. Its private
catalog, SSH keys, cloud seeds, firmware, login secrets where supplied, domain XML,
disk images and raw reports stay outside Git. Source tools and sanitized evidence
are maintained in this application repository. The command is
`augmentor-test-vm`; the desktop menu entry is **Augmentor Linux Test VMs**.

| Short name | Installation retained | RAM | Local SSH port |
| --- | --- | ---: | ---: |
| `ubuntu24-gnome` | Ubuntu 24.04 GNOME, working Mesa fixture | 6 GiB | 22601 |
| `fedora44-gnome` | Fedora 44 GNOME, latest adoption clone | 6 GiB | 22602 |
| `fedora44-kde` | Fedora 44 KDE, completed native/SDK installation | 6 GiB | 22603 |
| `mint223-cinnamon` | Mint 22.3 Cinnamon, Chromium installed | 4 GiB | 22604 |
| `leap16-gnome` | openSUSE Leap 16 GNOME | 6 GiB | 22605 |

Arch's completed environments are **containers**, not a recovered desktop VM.
Creating an Arch desktop VM is separate work. Owner-managed libvirt system
domains, including the existing Omarchy machine, are outside this lab.

Each machine has a `machine.json`, copied launch assets, immutable standalone
`checkpoints/<label>/base.qcow2`, and a separate `runs/<generation>/disk.qcow2`.
The checkpoint no longer needs an original cloud image or worktree backing path.
UEFI guests also retain their actual firmware variables, with a separate writable
copy per generation. Original disks and their historical reports are preserved.

Import checks every source qcow2 layer **without repair**, flattens it, compares
logical guest disk contents against the original, checks the new image, records
SHA-256, and synchronizes the files. The recorded recovery checkpoints may contain
the guest's last crash-consistent filesystem state. Guest journal replay and a
normal login require a separate boot observation; image checks alone do not prove
filesystem or application health.

## Start, stop and test an update

After a host reboot, wait for the DATA drive to mount, then use:

```sh
augmentor-test-vm status
augmentor-test-vm check ubuntu24-gnome
augmentor-test-vm start ubuntu24-gnome
virt-viewer --connect qemu:///session augmentor-lab-ubuntu24-gnome
```

For command-line guest access, the retained local identity configuration is:

```sh
ssh -F /media/manolo/DATA/augmentor-test-lab/ssh-config augmentor-lab-ubuntu24-gnome
```

Use the helper for starts. Its default is **one lab VM at a time**, with the full
configured guest RAM, an 8 GiB available host reserve and 1 GiB overhead. It also
requires 4 GiB free on the host root and 20 GiB on lab storage. It repeats admission
after expensive disk checks. Direct starts in Virtual Machine Manager or `virsh`
bypass these helper admission checks. Autostart is disabled for every lab domain.

The current definitions retain CPU emulation, Nehalem, and QEMU's pinned
`pc-q35-10.0` machine type. KVM was unavailable after the crash; switching to
hardware acceleration or a different CPU is a separate infrastructure change and
requires fresh desktop qualification. More RAM does not itself enable KVM.

Before testing an Augmentor update, close active guest tasks normally, shut the
machine down and save a dated checkpoint:

```sh
augmentor-test-vm shutdown ubuntu24-gnome
augmentor-test-vm checkpoint ubuntu24-gnome --label before-next-update
augmentor-test-vm start ubuntu24-gnome
```

Install through Augmentor's maintained installer/updater, record the exact source
and package identity, and run the applicable [qualification](LINUX-DISTRO-ROLLOUT.md)
checks. Checkpointing does not change the selected working generation. Restore to
a fresh generation when needed:

```sh
augmentor-test-vm shutdown ubuntu24-gnome
augmentor-test-vm reset ubuntu24-gnome --label before-next-update
```

Reset preserves the previous working disk and creates a new overlay and firmware
variables. It never commits guest changes into an immutable checkpoint. It refuses
active domains, mismatched definitions and saved guest memory.

## Host reboot and crash recovery

For a planned reboot, normally close guest tasks and run `shutdown` for each
active lab machine. The helper waits up to 180 seconds and sends no forced power
off on timeout. Do not reboot until status shows all test machines shut off.
Registration and disks survive reboot; the machines remain off until started.

The KDE fixture did not shut down through the virtual ACPI power button. Its
configured path uses the preserved dedicated SSH identity and the fixture's
existing passwordless sudo permission to request ordinary `systemctl poweroff`
inside the guest. No host sudo or forced power-off is used. A dropped SSH
connection is followed by read-only domain-state observation, never another
shutdown request or an automatic fallback. Other fixtures retain the observed
ACPI shutdown path.

After an unexpected crash:

1. Confirm the DATA drive is mounted and check `status`.
2. Run `check <name>` on each machine while it is off. This checks the exact backing
   chain, checkpoint hash and fixed launch assets as well as qcow2 consistency.
3. If checks pass, start one guest and observe its new boot/login and application
   state. The guest may replay its filesystem journal. Record interrupted actions
   as unknown outcomes; do not replay old tests, prompts or GUI clicks automatically.
4. If checks fail, preserve the working image and reports. Use `reset` with a known
   checkpoint for a fresh generation. Repair, if needed, belongs on a separate
   copy after reviewing the exact error; this tool never invokes `qemu-img -r`.

Generation changes have a synchronized pending record. An interrupted change
blocks lifecycle commands. `augmentor-test-vm reconcile <name>` can finish an exact
prepared transition, or replace an exact old definition after checking the new
files. It refuses an unrelated or changed definition. It never starts a VM.
New start/shutdown intent, dispatch and outcome receipts are kept in each machine's
`events/` directory; last-value files are conveniences, not the sole history.

RAM snapshots are not configured in this lab. `start` refuses libvirt managed-save
memory, because memory contains a separate saved device configuration and needs
its own checked restore. Clean shutdown and disk checkpoints are the supported
reboot path. Crash recovery cannot reconstruct unsaved RAM, keystrokes, drafts or
guest writes that never reached storage.

## Independent backup

A checkpoint on DATA survives a host reboot but is not a backup against loss of
that drive or computer. Use a separately mounted external drive or NAS:

```sh
augmentor-test-vm shutdown ubuntu24-gnome
augmentor-test-vm backup ubuntu24-gnome --destination /mounted/independent-backups
```

Backup refuses a destination on the same filesystem device. It creates a new
standalone image of the current working disk, verifies its contents, and copies
firmware, private launch assets and an import specification with a file-hash
inventory. Keep the backup private. On another host, install QEMU/libvirt/passt,
verify that inventory, adjust the import specification's paths to the mounted
backup in a separate copy of the specification, and import into a new private lab
directory. Do not edit the disk's backing
header or reuse stale process/session identifiers.

An independent backup destination has been requested; none is assumed. A complete
off-device restore drill remains separate from the local disk-preservation checks.

## Reproduce and maintain the helper

[`scripts/linux-test-lab.py`](../scripts/linux-test-lab.py) uses Python's standard
library, QEMU image utilities, libvirt and passt. No application model settings,
host GPU placement, physical audio routing or production installation changes are
needed. The local launcher uses a retained copy on DATA, so deleting a development
worktree does not remove the VM controls.

An import specification provides `name`, `disk`, `memoryMiB`, `cpus`, `cpuModel`,
`sshPort`, and optional `seed`, `sshKey`, `knownHosts`, `loginSecret`,
`firmwareCode`/`firmwareVars`. Private paths and values stay local. Import is explicit:

```sh
python3 scripts/linux-test-lab.py --directory /mounted/private-lab import \
  --spec /private/machine-spec.json --label initial-checkpoint
python3 -m unittest discover -s tests -p test_linux_test_lab.py -v
```

The focused tests include actual QEMU disk-byte comparison across a backing chain,
source preservation, corrupt-image refusal, domain-redirection refusal, saved-memory
refusal, fresh RAM admission, interrupted registration recovery and normal shutdown
without a forced fallback. See the [October 5 recovery record](../release/qualification/next-targets/20261005-persistent-linux-test-lab.json)
for actual machine inventory, tool identity and observed scope.

References: [QEMU image checks and conversion](https://www.qemu.org/docs/master/tools/qemu-img.html),
[libvirt persistent domains and managed save](https://www.libvirt.org/manpages/virsh.html),
[libvirt guest lifecycle and user networking](https://libvirt.org/formatdomain.html).
