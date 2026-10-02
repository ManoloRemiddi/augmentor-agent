<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Arch package guard candidate

`guard/PKGBUILD` builds the independently owned guard from a fixed public source
commit and SHA256-checked files. Build normally as an ordinary user with
`makepkg`; install the guard in its own completed pacman transaction **before**
installing any future `augmentor-agent` package. A simultaneous dependency
transaction does not establish the pre-hook boundary. Keep the guard installed
through application removal and unresolved recovery; remove it afterward in a
separate completed transaction.

The [full application preparer](../../scripts/package-system-qt.py) now generates
an independent PKGBUILD and checksum-checked complete payload. Its ordinary-user
native build and complete application inventory inspection pass; see
[exact scope and remaining installation/installer gates](../../docs/LINUX-SYSTEM-QT-PACKAGES.md).
Neither these private candidates, the guard nor the synthetic proof payload is a
public application release. The
reviewed target is the coherent Arch snapshot dated 2026-10-01, x86_64; rolling
updates and derivatives require their own actual acceptance.

The [real ALPM mechanism proof](../qualification/next-targets/20261002-arch-alpm-guard.json)
uses ordinary-user `makepkg` plus real pacman Install/Upgrade/Remove hooks in the
exact marked disposable container. Its payload contains only synthetic receipts
and text. It covers first install/reinstall, shared runtime/desktop leases from
UIDs1000/1001, both leases together, guard removal refusal, later pre-hook abort,
verified old recovery, upgrade/downgrade and staged application/guard removal.
Deleting volatile mirrors explicitly simulates their loss; it is not a real
reboot. Actual application processes and user data are not qualified here.

Injected extra synthetic inventory makes the real post-hook refuse completion.
Pacman nevertheless exits **0**, with the new package registered. The pending
record remains and startup is fenced. Both direct completion and recovery to
the changed old package refuse. Removing only that known empty synthetic
injection allows explicit completion after complete inventory verification.
This is a controlled proof failure; it is not a production package-repair
procedure. The full installer must independently verify finalization, rather
than trusting pacman's exit code.

The guard remains installed outside `/usr/lib/augmentor` so it survives payload
removal. Hook files are not overridden or disabled during tests. Three earlier
proof-driver/build setup failures and their verified cleanup logs are retained;
the checked report binds them separately from the passing run. Read
[the transaction contract](../../docs/LINUX-PACKAGE-TRANSACTIONS.md) before adding
the full product builder or installer integration.
