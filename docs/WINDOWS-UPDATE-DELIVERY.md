<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Windows signed update delivery

Development implementation; no customer updater or signing identity is enabled.
Inno remains the installer and WinSparkle 0.9.4 remains the downloader and update
notification framework. See [installer ownership](WINDOWS-INSTALLER-DECISION.md)
and [the shared coordinator](LIFECYCLE.md). No package is executed by this layer.

Bootstrap now includes the hash-pinned native WinSparkle DLL and license notices
for each CPU. Its staged manifest records that customer checks are disabled.
The runtime proof inspects its PE architecture, checks its digest and loads the
actual DLL without initializing checks. The rejected Velopack dependency is no
longer in the app runtime; historical fixtures require the archived lock at
`805664f`. These new payload changes await native execution.

## Trust and compatibility boundary

`services/lifecycle/release_bundle.py` verifies a handled WinSparkle download before
any update preparation or component shutdown. The callback must return handled or
error, never allow WinSparkle's default installer execution. The native fixture
now exercises this callback with ZIP delivery, including a valid outer download
signature whose inner release metadata or installer is invalid.

WinSparkle authenticates the downloaded bundle with its configured Ed25519 key.
The bundle additionally carries an independently signed release manifest, binding
the installer digest/length to version, source revision, OS/CPU, channel, data
schemas, protocols, minimum Windows build and delivery validity interval. Feed
metadata alone cannot establish these identities. Installed configuration must
supply both trust roots; the archive and appcast cannot introduce their own keys.
Missing or invalid release keys fail closed. Key provisioning/rotation and the
customer update UI/backend connection remain open gates.

The signature covers the exact UTF-8 manifest bytes prefixed by the bytes
`augmentor-release-manifest/1` followed by NUL. Verification uses the already
bundled, explicitly addressed Node runtime's built-in Ed25519 implementation,
through `verify-release.mjs`. It does not add another cryptographic dependency.
The bounded request uses stdin; inherited Node preload options are removed.
A timeout or verifier failure cannot reach preparation. The helper has no network
operations. These signatures do not substitute for Windows Authenticode signing
or establish SmartScreen publisher reputation.

Delivery accepts only a strictly newer three-part numeric product version on the
same installed OS/CPU and channel, with a different source commit, matching
protocols and bidirectionally readable data schemas. A schema/protocol migration
requires its own explicit implementation and qualification. Metadata expires,
permits at most 90 days of validity and tolerates five minutes of future clock
skew. Incorrect clocks fail with a clock/expiry error. Previously installed
versions cannot be delivered as updates. Retained recovery uses the separate
exact-identity policy below; the forward-delivery API has no downgrade bypass.

## Bundle and retained bytes

The stored ZIP contains exactly `manifest.json`, raw 64-byte `manifest.sig`, and
`installer.exe`. It has no comments, ZIP64, compression, directories, extra fields,
links or additional entries. A bounded central directory is checked before ZIP
parsing. Metadata is limited to 64 KiB; the installer to just below 2 GiB. The
installer already compresses its payload. This internal update envelope does not
ask users to extract anything; the website's direct installer remains an EXE.

The manifest schema is `augmentor-release-bundle/1`. Its exact keys are `schema`,
`release` (the existing durable journal artifact identity), `installerBytes`,
`minimumOSBuild`, `protocols`, `issuedAt`, and `expiresAt` (UTC Unix seconds).
Duplicate and unknown fields are refused. A Windows target currently requires
minimum build 26200 or newer, checked against the caller's actual trusted OS build.

Only fixed filenames are written into a new private cache directory. Installer
bytes are streamed, length/hash checked and flushed. Exact signed metadata is
retained alongside them. The returned installer handle denies writes/deletion on
Windows; WindowsApply independently rechecks the same signed digest on launch.
Failures remove only newly created files and preserve existing releases. Closing
the observation leaves the retained release available; it does not authorize
installation or archive a transaction.

## Revalidating retained recovery bytes

`open_retained_release` reopens an existing private cache entry only when its
signed release identity exactly matches the independently recorded recovery
identity. The caller must obtain that identity from the verified installation
receipt or update journal, never from the candidate cache's own metadata. The
function checks the installed trust key, OS/CPU, channel, both directions of data
schema readability, protocols, minimum OS and the complete installer digest and
length. It retains a Windows handle denying writes/deletion until closed. Invalid
or incomplete artifacts remain untouched for diagnosis; no command is executed.

An already retained release may be recovered after its delivery window expires:
expiry blocks *new delivery*, while offline recovery needs the exact prior bytes.
Malformed/unbounded validity windows and future issuance remain refused. A future
version is not accepted as the previous installation. This separate reader does
not weaken the forward verifier's version or expiry checks and cannot itself
authorize rollback. No temporary signing key is installed in the product.

Five additional tests exercise reopening/held-file behavior, expiry separation,
wrong recorded identities and incompatible installations, modified metadata/signature/
installer bytes, and hard-linked files. The 32 local update/journal/coordinator
tests pass; native execution of this addition is pending. Native tests pass both CPUs at [59dbbf4](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36404083441).
Initial installer source retention now has a separate native implementation under
qualification, described in the [installer decision](WINDOWS-INSTALLER-DECISION.md#retain-original-installer-bytes-before-replacement).
Its raw receipt is not a signed update bundle. Exact installed source selection now has a separate native receipt and private
reader, under qualification. An independently available recovery runtime, interrupted-state inspection, actual
recovery application, health and obsolete-file cleanup are still required.

The standalone retained installer now supplies a registered exact-build repair
path without relying on the installed Python/Qt runtime. This uses the separate
native source receipt and is not signed-bundle rollback. Manual repair/removal
refuses any unresolved `updates/active.json`; the coordinator's Windows journal
directory is `<private Augmentor base>/updates`. See [independent repair and its
pending native evidence](WINDOWS-INSTALLER-DECISION.md#independent-repair-from-windows-installed-app-controls).

Normal native desktop/browser startup now refuses an unresolved journal before
loading Python. The [isolated local-health action](WINDOWS-INSTALLER-DECISION.md#recovery-aware-startup-and-isolated-local-health)
can examine the newly installed UI without starting normal services or altering
the journal. Its observer verifies metadata identity and natural owned-process
exit; the caller still supplies trusted full-payload verification and the release
pair. This new path requires native qualification and is not a recovery executor,
automatic rollback or permission to replay an uncertain installer command.

Busy preparation can now be [cancelled and durably archived](LIFECYCLE.md#confirmed-cancellation-before-shutdown)
by its original live writer after the Windows context confirms all reservations
released, before any shutdown checkpoint or installer attempt. Unknown cleanup
or journal outcomes remain pending. This prevents a known reversible refusal from
permanently blocking startup; it does not clear interrupted APPLY or implement
restart recovery. New local fault tests pass; native DSH integration is pending.

## Evidence and remaining work

Eleven new local tests execute real Node Ed25519 verification and private storage,
covering valid delivery, tampering, wrong/missing keys, wrong CPU/OS/channel,
downgrades/relabeling, schema/protocol/build mismatch, expiry, malformed archives,
unsafe entries and inherited preload refusal. Together with journal/coordinator
checks, 27 local tests pass. Native x64/ARM64 execution passes at `594b56d`: the [fast workflow](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36394998226)
includes real held-file write/deletion refusal, and the [Inno workflow](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36394998456)
executes actual WinSparkle ZIP callbacks with all four acceptance/refusal cases.
Both workflows also pass at `98891c1`; its newly bundled updater DLL still needs
full payload/import qualification.

Native fixtures use temporary signing keys, synthetic release identities and an
explicit synthetic OS-build policy so the Server x64 runner can exercise metadata
validation. They do not claim Windows client acceptance, publisher trust, actual
N-to-N+1 application, recovery/rollback, notification UI wiring or public delivery.
The production path must use actual installed/OS identity and durable retained
source/target artifacts before composing this verifier with WindowsApply.

Primary references: WinSparkle's [pinned callback/key API](https://github.com/vslavik/winsparkle/blob/v0.9.4/include/winsparkle.h)
and [download verification](https://github.com/vslavik/winsparkle/blob/v0.9.4/src/updatedownloader.cpp),
plus Node's [crypto.verify API](https://nodejs.org/docs/latest-v24.x/api/crypto.html#cryptoverifyalgorithm-data-key-signature-callback).
The runtime remains pinned to the tested Node 24.19.0; inspecting newer docs does
not change that dependency.
