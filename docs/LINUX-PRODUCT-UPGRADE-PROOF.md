<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Published Linux product-version upgrade qualification

The existing Arch/Leap package-release upgrade and rollback keeps product0.2.13.
It does not qualify a different product version or coordinated DSH/history
rollback. A separate isolated Debian fixture now prepares the actual published
[0.2.12 complete preview](https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.12-complete-preview.1)
and [0.2.13 complete preview](https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.13-complete-preview.1).
The [input checkpoint](../release/qualification/next-targets/20261003-published-product-upgrade-preparation.json)
records their exact complete/native/manifest identities. This older pair does
not qualify current source-Qt rollout artifacts or Voice0.1.19.

Both bundles' complete member checksums and nested native release metadata pass.
Their target is Debian13 amd64 and readable data schema is1. Both retain
DSH0.1.5-rc.1, Voice0.1.16, Adaptive0.2.3 and Picker1.1.2. The0.2.13 native package
adds declared QtQuick/QML dependencies. Matching version strings alone are not
artifact identity or compatible integration evidence.

The rootless fixture has no owner mounts, devices, privileged mode or host
network. Its storage is on a secondary disk, separate from protected VM backing
disks. The original Debian13.6 image's identical image ID and layers are retained.
Official Debian signed repository metadata and all11 registered signing files
are verified; three absent documentation files in the slim image prevent a full
keyring-package audit claim. Signature checks remain enabled. One normal APT
transaction installs the published0.2.12 packages and declared/setup prerequisites;
both native file audits pass. Actual Python3.13.5, PySide6.8.2.1, Qt6.8.2 and
GI3.50.0 are recorded. The image's existing service-start policy and absence of
systemd make this an offscreen container case, not login/session acceptance.

The [maintained baseline preparer](../release/prepare-published-linux-upgrade-fixture.py)
requires the exact owned container marker, unused product state, private ordinary
UID1000 home, immutable checksummed public bundle and matching native audit.
It journals intent before the unchanged published installer, uses a numeric
loopback synthetic provider that refuses model turns, and disables only package
reinstallation and login-service starts because those are externally provisioned
fixture prerequisites. No failed/preparing account is resumed. Four synthetic
admission/durability tests pass. One actual ordinary-user run of reviewed4e090
passes in28.28seconds: unchanged published installer exit0, matching installed
receipt/selection/harness, and zero model requests. No SDK turn has run.

Strict independent process-absence postflight refuses two UID1000 defunct child
entries (StateZ, PPid1, empty argv). Native package and product identity checks
pass; the preparation result remains PASS while complete postflight remains FAIL.
Both fixture ports are bindable and no live user process remains. One normal
TERM request to the exact fixture returns0 but PID1 sleep stays running; no
repeat, forced stop or restart follows. The historical process evidence remains.
A subsequent normal signed installation of tini0.19.0 verifies both registered
executables and root metadata. Two absent changelog files in the slim image
prevent a full tini package-audit claim. Future descendant reaping or a separately
admitted init namespace must be established before SDK execution; this does not
remove or relabel the old defunct entries.

The remaining execution must establish both synthetic role histories on0.2.12,
stage immutable old/new roots through the canonical updater, install the new
integration through its checked Setup contract while idle, restart only the
fixture-owned DSH host, authenticate the new product identity and select0.2.13.
It must preserve model/plugin settings outside intentional version/path updates,
all saved history events and request counts, and demonstrate coordinated old
integration/selection rollback. A desktop rollback alone does not restore DSH
composition or plugins. Extra resume events, settings mutations, unknown actions
and compatibility failures remain failures; they are not normalized or replayed.
Legacy memory companions lack the newer maintenance API and require an explicitly
attributed, idle, fixture-owned normal shutdown plan before SDK execution.
Product upgrade/rollback, graphical Browser, physical speech, legal and release
acceptance remain open.

## October 3 admitted init namespace and legacy companion source

A separately admitted local snapshot preserves all28,695 regular home files,
507 symbolic links and5,499 directories with identical bytes and metadata. Its
new process namespace runs verified tini0.19.0 as PID1 and contains no ordinary
user process entries. The original namespace and its failed process-absence
result remain preserved. The installer was not repeated; no SDK turn has run.
Only public packages and synthetic fixture state enter this local snapshot.

[The separate legacy companion helper](../release/published-linux-legacy-companion.py)
is restricted to that exact init154 namespace, ordinary UID1000/private home,
matching published Debian0.2.12 or0.2.13 native identities and the exact common
memory source checksum. Native package audits must pass. Unlike the current
maintenance helper, it explicitly checks that historical root:root0664 files and
root:root0775 parents cannot be written by this non-root-group fixture account.
Links, foreign owners/groups, world-write, hardlinked source and root/root-group
callers refuse. It does not alter installed permissions or current705 guards.

The helper refuses a pre-existing companion, socket or memory-engine
configuration, then journals one fresh owned spawn before starting the unchanged
public source. It binds the direct child, UID, start time, argv, source and Unix
socket peer/inode. Only read-only memory description is used: configured engine
and active processing refuse. After the fixture DSH Node host is absent, normal
cleanup journals one SIGTERM to that exact direct child and waits for its normal
exit/endpoint removal. Unknown signal/wait never retries or escalates. State,
logs and journals remain private; eight synthetic ownership and failure cases
pass. This source helper still needs actual start/read/normal-stop acceptance
before different-version SDK execution. No physical speech or memory engine is
provisioned, and this is not a production lifecycle adapter.
