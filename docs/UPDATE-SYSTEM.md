<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Shared application updates

## Implementation checkpoint — October 3, 2026

This feature is under implementation on `feat/automatic-updates`, based on
`c7f895d416e6b94ca601b66a09caf4846a64b907`. It has not replaced an installed
application, published a signed repository, or qualified automatic installation.
The complete intended scope includes optional automatic installation, independent
health observation and recovery across supported installation methods. The
discovery/download checkpoint below is not completion of that scope.

Desktop **Versions & updates** and Browser **Settings → Updates** use one
model-independent service. They show installed version/build, the last successful
check, an available release and transfer progress/errors. Preferences support
daily or two-day checks, stable or preview releases, and separate download and
installation consent. Automatic installation remains disabled until the installed
build has a qualified external installer adapter and a provisioned signed feed.
The UI does not silently turn that preference into permission to replace files.

Automatic checks default on for an installed application, off for a development
checkout. Downloads default off. The scheduler runs while the shared service is
running, starts after a short boot delay, adds up to fifteen minutes of jitter,
and retries failures with bounded backoff. It catches an overdue check on the
next launch; this is not an operating-system task that wakes a closed application.
Changing the schedule is shared across surfaces, not tied to a model or chat.

Notifications are claimed once per exact release across both surfaces. Users can
skip a release or postpone for one/two days. The native primary window uses its
existing tray when available, otherwise an unobtrusive tooltip on More. Browser
shows a button opening the Updates section. No modal dialog interrupts chat.
Failure retains the previous successful-check time and candidate instead of
claiming the application is current. An unknown legacy build cannot be declared
older than another build of the same product version without a bridge receipt.

## Ownership and data

`services/updates/manager.py` belongs to the per-user shared prompt service, rather
than starting a second unowned daemon. Prompt service maintenance admission covers
the whole background discovery/download operation. Busy downloads refuse graph
maintenance; cancellation terminates only the updater's own transfer child.
An updater initialization/recovery error cannot disable conversations or prompts.

Windows transfers create new cache bytes instead of preserving public temporary
file ACLs. The Python owner verifies the file’s existing user/SYSTEM allow-list
through an opened kernel handle before setting its protected flag. Foreign/public
grants and linked files are refused without changing their permissions. Hosted
Windows tests must verify this producer boundary on both CPUs.

Private data lives under `<AUGMENTOR_SHARED_DATA>/updates` (or the existing shared
data default): atomically written `state.json`, verified repository metadata,
digest-named cache files and `ready/<channel>-<target>-<version>-<build>/` downloads
with their original filenames. Status responses hide filesystem paths. An explicit
**Show downloaded files** action opens that dedicated folder without executing
the installer. Cache files have bounded sizes, verified hashes and private file
permissions; linked/hardlinked or foreign files fail validation. Conversation,
credential, model and speech directories are not replaced by downloading updates.

Saved preferences use optimistic revision checks. Dirty settings forms preserve
the draft and its original revision while another surface changes the service.
An old-channel response cannot overwrite a newer selection. Interrupted workers
become an explicit interrupted state; observing that state never replays install.

Desktop transports updates through `PromptClient`, including when the model is
offline. Browser uses a short independent native connection. A mismatched product
handshake permits status, discovery, download, cancellation and opening the
download folder to support repair; it does not permit preferences or installation.
The existing embedded application SDK administration guard still blocks this
shared surface entirely. Update actions reject caller-provided URLs, commands,
release objects and download destinations.

## Publisher tooling checkpoint

[`scripts/update-repository.mjs`](../scripts/update-repository.mjs) creates a
two-of-three Ed25519 root and separate targets/snapshot/timestamp keys. Secret
material must live outside any Git checkout and outside public output. Routine
`publish` and `refresh` do not load offline root private keys. Both channel
catalogs pass the same Python schema used by installed clients; new artifact
entries require actual size/hash-verified bytes. Existing public target names
cannot be relabeled with another digest. Refresh verifies retained signed
publication history and re-signs unchanged content with a higher sequence.

A publication uses consistent versioned snapshot/targets metadata and hash-prefixed
catalog files. Timestamp expires in seven days, snapshot in thirty, targets in
ninety and the initial root in two years. The output is a new immutable local
publication directory; upload remains a separate release-owner action. Publish
versioned files/catalogs first and timestamp last, retaining prior versioned files
and root history. The installed TUF client verifies catalog-prefixed paths; GitHub
installer filenames retain their public names and pass the maintained model’s
exact target verification.

A private exclusive publisher lock and durable pending claim prevent simultaneous
or uncertain publication from reusing a role version. Interrupted initialization
or publication fails closed for explicit owner recovery; root rotation/recovery
commands and portable CI provisioning are still in progress. No real publisher
keys have been generated or public feed uploaded by this checkpoint. Synthetic
publisher tests exercise the complete producer → HTTP → installed TUF-client
path, independent root custody, online-only refresh, immutable asset refusal,
tampered history, private permissions and concurrent-writer exclusion.

## Discovery and signed delivery

The installed [`release/updates.json`](../release/updates.json) currently has
`enabled: false`. The fallback discovers public releases through the canonical
GitHub API, including prereleases for the preview channel, and selects exact known
asset names for the host CPU. It filters drafts and the other channel. GitHub
asset SHA-256 plus exact length detect corrupt manual downloads. This is HTTPS
public discovery, **not publisher-signed installation authority**. Unsupported
targets return no candidate; no x64 installer is offered to an ARM64 user.

`services/updates/repository.mjs` integrates pinned `tuf-js` 6.0.0 and
`@tufjs/models` 5.0.0. The maintained TUF client verifies root, timestamp, snapshot,
targets, expiry, version rollback and artifact identity. The adapter adds bounded
HTTPS transfers, cancellation, atomic private cache writes and exact official
artifact paths. Production cannot enable the test-only loopback transport through
a request or configuration. Enabled repository configuration must use the fixed
official artifact host and the `augmentoragent.com/updates/` metadata/catalog
namespace with a bundled initial public trust root.

An enabled signed feed fails closed: unavailable, expired or invalid metadata
does not fall back to an unsigned installer. The catalog schema
`augmentor-update-catalog/1` identifies version **and build sequence**, exact source
commit, release channel, OS/CPU, installation method, minimum OS/updater, protocols,
readable data schemas and required component hashes/sizes. Debian requires runtime,
desktop and Browser as a set; Mac and managed Linux need a bundle; Windows needs
its installer. Withdrawn, incompatible, partial, ambiguous or unsafe entries are
rejected. A signed selected digest must still agree with TUF targets when downloaded.

The catalog does not itself establish runtime health or authorize data migration.
Protocol/data compatibility changes require an explicit migration route. Linux
catalog entries require an explicit map of supported Debian/Ubuntu/Fedora version
floors; the kernel minimum is checked separately. Unknown distributions fail
closed for signed selection. Those declarations still require actual installed
distribution qualification before automatic installation can be enabled.

## Verification and remaining integration

Code checkpoint: `dc814c224c8d37e740d2806372bfb9ee61fb49b0` on
`feat/automatic-updates`. Linux source verification passed build/type checks,
version synchronization and the private-source boundary. Full Node suite: 513
cases, 511 passed and 2 explicit skips. Full offscreen Python/Qt suite: 839 cases,
803 passed and 36 explicit platform/integration skips. Browser suite: 87 passed.
The update-focused Python set passed 77 cases (one existing OS-specific skip);
real TUF/transfer set passed 11. Production dependency staging collected original
notices for 236 package instances including the new TUF dependencies. The host
QtTest binding was extracted from Debian’s matching 6.8.2.1-4 package into a
temporary test fixture; system/application installations were not changed to
provide that dependency. Native control layout was checked in a 480×500 offscreen
render without clipping. These are Linux/synthetic source checks, not installed
Mac/Windows or cross-version package acceptance.

Focused tests use temporary private state and independently authored inert payloads.
Repository tests use real Ed25519 metadata and local HTTP transfer through the
maintained client: valid catalog/payload, corrupt cache, altered catalog/payload,
relabeled artifact, expired/replayed timestamp, untrusted signature, dual-authority
root key rotation, root-cache replacement, trusted bridge advancement, linked
cache refusal and transfer cancellation. Manager
tests cover notification deduplication, skip/postpone, failure age/backoff, settings
revision/channel races, admission, cancellation, explicit opt-in, unsafe commands,
manual file naming and recovery refusal. Qt and Browser controls are exercised
without a model connection; Browser connection tests cover mismatched handshake
and disconnect without replay.

Run source build/type checks, `node --test tests/updates-repository.test.mjs`,
the `test_update*.py` tests with `PYTHONPATH=apps/native QT_QPA_PLATFORM=offscreen`,
and `node --test apps/browser/test/update*.test.mjs`. The full suites and separate
native OS/package qualification remain required for release. A local offscreen
Qt or synthetic provider result does not establish physical OS, microphone,
signed package or cross-version installed acceptance.

Required remaining work, retained in the authorized full implementation scope:

- Provision a publisher-controlled trust root, separated signing roles, monotonic
  publication tooling and expiry refresh; publish/monitor the signed repository.
- Stamp exact build identities in every artifact and ship a manual bridge release
  for legacy installations; distinguish source, selected and running identities.
- Compose each installation adapter with the existing admission/drain coordinator,
  an external installer, durable one-shot journal and independent health/recovery.
  Recheck freshness, consent and revocation immediately before authorizing apply.
- Preserve matching Browser/DSH/voice components and immutable Linux deployment
  selection. Unpacked Chromium extensions require explicit reload.
- Qualify N-to-N+1 upgrades, refusal during accepted work, power/process interruption,
  full recovery and native CPU execution across supported distribution/OS methods.
- Document/verify automatic consent and user postponement through actual installation,
  and disclose hosting requests/disk retention in the installed user guides.

Existing mechanisms: [immutable Linux selection](DESKTOP-DEPLOYMENTS.md),
[Windows signed delivery](WINDOWS-UPDATE-DELIVERY.md),
[Windows installer decision](WINDOWS-INSTALLER-DECISION.md), and
[platform parity](PLATFORM-PARITY-AUDIT.md). These are reusable mechanisms with
their own evidence limits, not proof that the new customer update flow is complete.
