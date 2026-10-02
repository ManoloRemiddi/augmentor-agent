<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Linux candidate package transactions

## Current implementation and acceptance boundary

`release/linux-package-guard.py` is the standalone root guard foundation for
explicit Leap 16.0/RPM and dated Arch/ALPM candidates. It imports no application
code and reads no user homes. Existing Debian and Fedora packages keep their
current hooks. New builders, guard bootstrap, real package transactions and
interrupted-reboot recovery remain required before either new adapter is admitted
to the complete installer matrix.

The [checked source proof](../release/qualification/next-targets/20261002-joint-package-guard-source.json)
records exact working files and actual Arch/Leap native suites: **699 tests,
two Mac-only skips, each**. Seven synthetic-root cases use real kernel flocks
and file writes to exercise joint refusal, changed/unlisted payload rejection,
interrupted mirror writes, lost `/run` mirrors, incoming-identity mismatch,
unsafe ownership/modes/links and database-query failure. Other cases test the
persistent startup fence and explicit receipt retention across managed staging.
These establish source behavior, not execution of downstream package managers
or real multiuser/reboot transactions.

## Joint maintenance and persistent intent

Preflight validates the exact host target, then exclusively acquires one stable
transaction lock and both existing `/run/augmentor/augmentor-{runtime,desktop}.lock`
inodes. Any live shared lease or recognized older application process refuses
before a pending record is written. Root-owned directories/regular lock files
must have safe modes and single links. The guard never closes applications.

The intent record lives at
`/var/lib/augmentor-package-maintenance/pending.json`, with format, transaction
UUID, target, manager, operation, previous package and expected incoming package
when supplied. Writing and flushing this persistent record is the commit point.
Ephemeral component mirrors are written afterward. Both Linux lifetime leases
check the persistent record while holding their shared lease, so reboot or a
failure writing one mirror cannot allow reopening an unresolved package.

The next guard refuses a second operation while that intent is unresolved.
Its `complete` action requires actual final state: exact registered package
name/version-release/architecture, matching target/product/source/Desktop
identities and the complete regular-file/internal-link inventory from the
root-owned `linux-package.json`. Unexpected, changed or external-link members
refuse. Removal requires the package to be explicitly absent and its app root
and Desktop marker gone. A query/database failure is not proof of removal.
Completion clears mirrors first and unlinks/flushed persistent intent last.
Any validation failure retains the record; no timer, reboot or post-hook alone
clears it. `recover-unchanged` verifies the recorded old package identity,
complete old payload inventory and exact old receipt hash before resolving
intent under all three exclusive locks. A previously absent app must still have
no partial app root or Desktop marker. A changed receipt, payload, package query
or identity refuses recovery and retains intent.

`services/lifecycle/lease.py` accepts the explicit receipt only for the two
reviewed target/manager pairs. RPM checks full name/version-release/architecture;
ALPM checks exact name/version-release and registered x86_64 architecture from
the locale-stable `pacman -Qi` database query. Source, target and product must match
the selected release. `desktop-deployment.py` retains the receipt in the immutable
managed artifact. The existing Fedora receipt and Debian component checks remain
separate and tested.

The [recovery source checkpoint](../release/qualification/next-targets/20261002-joint-package-recovery-source.json)
adds two focused cases, for nine guard cases in total. Both actual Arch/Leap
native suites pass **701 tests, two Mac-only skips**. The first attempt exposed
a strict legacy Fedora query mock rejecting a new environment argument; that
failure is retained, and the locale override is limited to the new Arch query.
These are source/synthetic-root results; the downstream checkpoint below is
distinct and still does not establish full product or RPM transaction acceptance.

## Leap RPM adapter design

Use trusted self-contained `%pre` and final-removal `%preun` guards invoking
`/usr/bin/python3.13 -I`. Their failure protects Augmentor's own unpack/remove
boundary. Verify the final installed state in `%posttrans`; verify final removal
in `%postuntrans`, whose code must survive disappearance of app files.
The [RPM 4.20.1 package state machine](https://github.com/rpm-software-management/rpm/blob/c8dc5ea575a2e9c1488036d12f4b75f6a5a49120/lib/psm.c)
establishes the refusal boundary. Its
[transaction processing](https://github.com/rpm-software-management/rpm/blob/c8dc5ea575a2e9c1488036d12f4b75f6a5a49120/lib/transaction.c)
can continue other packages after one failure and still invoke later scripts.
A post-transaction invocation alone therefore cannot finalize pending state.

Run the complete installer's joint preflight before zypper for the earlier
boundary on its planned operation. A libzypp commit plugin is not an assumed
veto: its [documented ERROR response](https://github.com/openSUSE/libzypp/blob/master/zypp/doc/autoinclude/Plugin-Commit.doc)
cancels the plugin rather than the commit. The
[Leap zypper manual](https://manpages.opensuse.org/Leap-16.0/zypper/zypper.8.en.html)
records exit 107 for a script failure with packages already registered; inspect
both the command result and actual finalized Augmentor state.

## Arch bootstrap and hook ownership

The required preflight is an **already-installed** ALPM `PreTransaction` hook
with `AbortOnFail`, triggering Install/Upgrade/Remove of `augmentor-agent`.
Ordinary `.INSTALL` pre-scriptlets cannot protect the payload: upstream
[add.c](https://gitlab.archlinux.org/api/v4/projects/pacman%2Fpacman/repository/files/lib%2Flibalpm%2Fadd.c/raw?ref=54d9411)
and [remove.c](https://gitlab.archlinux.org/api/v4/projects/pacman%2Fpacman/repository/files/lib%2Flibalpm%2Fremove.c/raw?ref=54d9411)
ignore their return values. The
[ALPM hook manual](https://man.archlinux.org/man/alpm-hooks.5.en)
specifies the abort boundary; a post-hook failure does not undo a commit.

A separate guard package must own the hooks and trusted helper outside the app
root and survive app removal. Install it in a separate bootstrap transaction
before the app, rather than as a simultaneous first-install dependency. Upstream
[hook.c](https://gitlab.archlinux.org/api/v4/projects/pacman%2Fpacman/repository/files/lib%2Flibalpm%2Fhook.c/raw?ref=54d9411)
reads installed hook directories separately in each phase: an app-owned hook is
absent before first install and gone after removal. Guard removal must refuse
while the app remains installed; combined removal needs an explicit staged
procedure. PostTransaction validates actual complete receipt state, and the
installer independently confirms finalization.

### Actual Arch mechanism checkpoint

The [guard recipe](../release/arch/README.md) pins published `daf35a3` helper bytes
and all source checksums. Ordinary-user makepkg succeeds, and the
[checked real ALPM proof](../release/qualification/next-targets/20261002-arch-alpm-guard.json)
passes with explicitly synthetic application receipts/text. Real pacman hooks
protect first install/reinstall, runtime/desktop and joint UID1000/1001 shared
leases, guard removal, upgrades, downgrade and staged removal. A later abort
retains persistent intent; losing volatile mirrors still fences startup, and
exact old-state recovery resolves it.

An actual post-hook complete-inventory refusal leaves the new package registered
and pending **while pacman exits 0**. Independent completion and unchanged-old
recovery both refuse the bad state. Only removal of the exact known empty
synthetic injection followed by full state verification allows completion.
This is not a production repair procedure or selected product payload edit.
Three earlier proof-driver/build setup failures and safe observed-state cleanup
are retained separately. Full application PKGBUILD/runtime/desktop/browser,
real multiuser applications, data retention and interrupted reboot remain open.

## Required real qualification

Build both matching payloads and runtime policies from a clean reviewed source.
Use the real dedicated RPM and pacman fixtures for first install, active Desktop
and runtime/Browser-only refusal, multiple users, reinstall, upgrade, downgrade,
removal and retained user data. Inject later-script/final-validation failures and
interruptions; verify unchanged payload on refusal, durable state after reboot,
and explicit verified recovery. Publish only those actual configurations that
pass. Root hooks must continue to avoid user homes, credentials, conversations
and service ownership.
