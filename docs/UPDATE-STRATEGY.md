<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor update research and implementation strategy

Research date: 2 October 2026. This is an implementation proposal, not an enabled updater or a qualification report for new update behavior.

Augmentor should check for an eligible published release every 24 hours, notify the user once, and offer an explicit preference for downloading and installing updates when work has finished. Release eligibility must include the operating system, CPU, installation method, channel, component dependencies and data compatibility. A repository commit or a higher product version alone cannot establish eligibility.

The recommended architecture is one shared release policy and transaction coordinator, with installation adapters for each supported distribution. Reuse the existing Linux staging mechanism and the substantial Windows lifecycle work. Keep update decisions deterministic and outside the conversational agent. Ship discovery and supported manual downloads first; enable automatic installation separately as each installation adapter passes real cross-version and recovery qualification.

## Evidence and research scope

The canonical checkout uses the correct public origin and branch `main`, but its local HEAD is `f353c52b060a5b762da70b862d88a6434329ab6b`, with existing uncommitted work. Remote references were fetched for read-only inspection without changing the checkout or its working files. The source snapshot reviewed on GitHub is `3c1dddfc6ff5a60e7c64320d546229679f7b6201`, including the October 2 Handy merge. The separately fetched Windows PR #20 head is `e52ee862aa9f7c5515f3c25f6936d3f08021b943`; it was open and unmerged when inspected.

Repository findings below come from source inspection, release metadata and recorded qualification. No new runtime tests, installation, service restart or failure injection were performed for this analysis. Historical passing tests are evidence for their recorded artifacts, not a fresh qualification of current source. No installed user data or credentials were inspected for this report.

The GitHub release list at inspection contains seven published releases, all marked prerelease. The newest public Linux and Mac releases are 0.2.13, published on October 1. Their qualified binary source is `0eb2ec112afa52b886b63606f80967198a7feb0c`, earlier than current main. Consequently, recently merged source features are not necessarily downloadable product features. See the [0.2.13 publication record](https://github.com/ManoloRemiddi/augmentor-agent/blob/3c1dddfc6ff5a60e7c64320d546229679f7b6201/docs/RELEASE-0.2.13.md).

## Existing update mechanisms and gaps

| Area | Observed mechanism | Consequence for the proposed updater |
| --- | --- | --- |
| Native Linux managed desktop | `augmentor-update` stages a separate artifact, hashes its inventory, checks imports and authenticated DSH compatibility, atomically replaces the selected descriptor and retains the previous selection. | Reuse selection and staging. Add trusted remote delivery, install identity, whole-component coordination and independent health/recovery. |
| Linux system packages | Debian runtime and desktop packages have lifetime leases, maintenance markers and matching-version checks. Fedora packaging also exists, with separate qualification. | Preserve package-manager ownership. An app cannot silently replace root-owned package files through the user-local updater. |
| macOS | The development installer stages bundles, verifies their seals, holds an installation lease and journals replacement with restoration after interruption. Public previews use an ad-hoc signature. | Existing safeguards are useful, but network discovery, publisher trust and complete product coordination remain missing. |
| Browser | Native messaging requires the loaded extension and companion to have the same product version. Preview installation uses Load unpacked and a manual reload. | Upgrading the companion alone can make Browser refuse connections. Account for both loaded and on-disk extension identity. |
| Historical Browser updater | Old registry/GitHub checks and extraction code remain. Unified mode returns an installer message and refuses the legacy download operation. | Keep that refusal. Reusing its in-place extraction would bypass current immutable-release and lifecycle rules. |
| Windows development | PR #20 contains Inno Setup plus WinSparkle, signed release-bundle verification, a shared update journal/coordinator, admission controls and independent recovery work. Customer checks are disabled. | Reconcile and reuse this work. Its delivery verifier is currently Windows-specific; it is not already a complete cross-platform updater. |
| Dictation and external services | Embedded Handy has no independent updater. Resonant Voice and memory remain separate companions. Codex 0.159.2 is an external, version-checked prerequisite in current main. | Include owned dictation binaries in the product transaction. Declare external requirements explicitly and preserve external service settings. |
| Home and Mobile | Home deployment belongs to its deployment companion. Mobile streams the actual selected Qt application; an internal Android wrapper also exists. | Include the mobile host in desktop maintenance. Treat NAS deployment and any Android wrapper update as separately owned operations. |

The primary source evidence is the current [Linux deployment implementation](https://github.com/ManoloRemiddi/augmentor-agent/blob/3c1dddfc6ff5a60e7c64320d546229679f7b6201/scripts/desktop-deployment.py), [package leases](https://github.com/ManoloRemiddi/augmentor-agent/blob/3c1dddfc6ff5a60e7c64320d546229679f7b6201/services/lifecycle/lease.py), [macOS installer](https://github.com/ManoloRemiddi/augmentor-agent/blob/3c1dddfc6ff5a60e7c64320d546229679f7b6201/scripts/install-macos.py), [Browser handshake](https://github.com/ManoloRemiddi/augmentor-agent/blob/3c1dddfc6ff5a60e7c64320d546229679f7b6201/apps/browser/native-host.mjs), [legacy Browser update refusal](https://github.com/ManoloRemiddi/augmentor-agent/blob/3c1dddfc6ff5a60e7c64320d546229679f7b6201/apps/browser/pipe.mjs), and Windows [delivery design](https://github.com/ManoloRemiddi/augmentor-agent/blob/e52ee862aa9f7c5515f3c25f6936d3f08021b943/docs/WINDOWS-UPDATE-DELIVERY.md).

## Relevant external practices

GitHub Releases can host the artifacts, but its latest-release endpoint excludes prereleases and drafts. Augmentor needs an explicit preview channel and platform selection. A temporary notification-only implementation can list published releases and filter eligible targets; production delivery should read a small maintained release catalog. [GitHub release API](https://docs.github.com/en/rest/releases/releases#get-the-latest-release).

Public clients should not need a GitHub token. GitHub's unauthenticated API limit is 60 requests per hour per originating IP, which can affect many users behind one connection. Prefer a cached static catalog; otherwise use conservative polling, conditional requests, jitter and rate-limit backoff. Conditional responses save bandwidth, but GitHub documents the primary-rate-limit exemption for correctly authenticated requests, so do not assume anonymous checks are exempt. [Rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api), [API practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api).

Sparkle is a mature macOS update framework with signed archives, appcasts and platform installation support. Its integration still has to cooperate with Augmentor's active-work veto, shared services and installation lease. Package-based Sparkle updates require authorization and have additional limitations; select an application-bundle path if it satisfies Augmentor's installation needs. [Sparkle documentation](https://sparkle-project.org/documentation/), [signed publishing](https://sparkle-project.org/documentation/publishing/), [package limitations](https://sparkle-project.org/documentation/package-updates/).

WinSparkle provides signed delivery and update notifications independently of the UI toolkit. The existing Windows branch already pins and tests a version; research of newer documentation does not authorize replacing that pin. Keep Inno's installer and the Augmentor coordinator responsible for maintenance. [WinSparkle](https://winsparkle.org/), [integration](https://winsparkle.org/guides/integrating-winsparkle/).

The Update Framework, TUF, addresses update threats such as rollback, stale metadata and compromised keys through trusted metadata roles, versioning and expiry. Use a maintained implementation as the preferred trust foundation for production automatic delivery, with Augmentor compatibility fields attached to authenticated targets. The Windows branch's signed manifest is a valuable starting boundary, but does not by itself establish full TUF protections or key rotation. [TUF overview](https://theupdateframework.io/docs/overview/).

Qt Installer Framework can maintain components across desktop operating systems. Adopting it would still require Augmentor's service coordination and would replace existing installation contracts. I recommend retaining current packaging for this work. Electron and Tauri updaters are similarly tied to application frameworks Augmentor does not use. [Qt Installer Framework](https://doc.qt.io/qtinstallerframework/ifw-overview.html), [Electron updates](https://www.electronjs.org/docs/latest/tutorial/updates), [Tauri updater](https://v2.tauri.app/plugin/updater/).

MSIX/App Installer offers platform scheduling and deferred updates on Windows. It remains an alternative if Windows packaging is reconsidered; it should not replace the branch's researched Inno decision without testing installation, removal, external browser registration and active-work behavior. [Microsoft update settings](https://learn.microsoft.com/en-us/windows/msix/app-installer/update-settings), [Augmentor installer decision](https://github.com/ManoloRemiddi/augmentor-agent/blob/e52ee862aa9f7c5515f3c25f6936d3f08021b943/docs/WINDOWS-INSTALLER-DECISION.md).

## Proposed release identity and publishing contract

Use an installation receipt identifying the product version, exact release/build ID, source revision, artifact identity, OS/CPU, installation method, channel and owned components. Record selected and running identities separately. Development/mixed installations need their own classification and should receive advice rather than automatic public-package replacement by default.

The version 0.2.12 already has multiple Mac preview builds. Checking only `0.2.12` misses preview.1 to preview.3. Likewise, the managed Linux previews can retain older product contracts while carrying newer feature overlays. Introduce an authenticated release sequence or precisely specified version/build ordering. Preserve human-readable versions, but never use file modification times or source-commit dates to rank eligible installations. The Windows forward verifier currently requires a strictly newer three-part numeric version and rejects same-version rebuilds; extending that policy requires tests and a deliberate manifest revision.

The signed catalog should bind each eligible target to:

- Product version, release sequence/build identity, channel, source revision and publication time.
- OS, CPU, minimum OS and any relevant distribution, libc or CPU-instruction requirements. Do not treat every ARM64 machine as the same target.
- Installation method and artifact format, download location, length, archive digest and payload inventory identity where applicable.
- Required DSH/Pi/plugin/voice/dictation contracts, and optional external prerequisites such as the pinned Codex CLI.
- Data schemas readable before and after updating, explicit migrations and rollback limitations.
- Minimum updater version, release notes, revoked/bad-build status and rollout policy.

The compressed archive hash and the existing Linux file-inventory hash have different meanings; keep their fields distinct. Verify the signed target and downloaded archive before extraction or running candidate imports. Existing Linux staging executes candidate Python during preflight, which is appropriate for locally trusted candidates but must follow publisher verification for remote downloads.

Publish artifacts first, finish installed-artifact validation, then update the catalog as the final promotion step. Publishing must bind a complete component set to a reviewed revision. The website downloads and update feed should consume the same promotion record. Failed or partial uploads must leave the prior release eligible. Keep prior recovery artifacts, and support withdrawing a bad release without mutating its existing bytes.

A practical proposed location is a static updates path on the existing official website, with payloads on GitHub Releases. This endpoint does not currently exist as an implemented contract. A trusted catalog can maintain different qualified targets while reporting release lag explicitly; absence of a target means no compatible update is available, rather than an invitation to download another OS's artifact.

## Proposed check schedule and user experience

Default to automatic checks every 24 hours. Offer 48 hours and manual checking. Use a small random delay to spread traffic. Check shortly after launch or resume if overdue; an always-running tray should also check while the chat window is hidden. Start with scheduling inside the app/service that already owns lifetime. Add OS background scheduling only if checks while Augmentor is fully closed become a requirement; never wake a sleeping computer just to check.

Persist the last attempt, last successful check, next due time, selected channel and previously notified release. A network error should leave the previous result visible with its age and a retry opportunity. It must not become a false claim that the app is current. Discovery should work without a model, DSH connection, microphone or administrator rights, including Browser-only installations through the companion.

Suggested controls in the established settings design:

1. **Check for updates automatically**, plus **Check now**.
2. **Download updates automatically** as a separate choice.
3. **Install updates automatically when Augmentor is idle**, enabled only for qualified installation methods.
4. A channel choice separating stable releases from explicitly selected previews.

Retain the installed channel unless the user changes it. Public preview users must be able to receive preview fixes, while future stable users must not receive development builds automatically. Avoid an immediate restart as an implied consequence of permitting automatic downloads.

Notify once per eligible release, with a persistent settings/tray indicator and actions to view changes, download/update, postpone or skip that release. If several daily releases arrive, show the newest eligible one rather than accumulating dialogs. Show distinct states for available, downloading, ready, waiting for work to finish, installed and restart required. A blocked dependency or unqualified platform must have a truthful supported next action.

A minimal check needs no conversation contents, credentials, hardware serial numbers or model configuration. It can fetch a shared platform/channel catalog without a unique user ID. Separate crash reporting or rollout telemetry would require its own product decision. Network requests still expose ordinary network metadata to the hosting service.

## Proposed installation transaction

Discovery and downloading must remain harmless to active work. The transaction that actually changes installed software should follow this sequence:

1. Resolve the exact installed identity and eligible target. Obtain and authenticate both target and retained recovery artifacts. Confirm disk space for the download, extracted candidate and old build.
2. Stage in a private bounded cache. Reject unsafe archive paths, links, duplicate entries, unexpected files and oversized output. Preserve resumable downloads only when their identity and final digest can be revalidated.
3. Verify local dependencies and ownership without changing user configuration. Edited DSH presets require a supported merge or manual action; never reset them to pass an ownership check.
4. Acquire a maintenance reservation that prevents new work from starting. Polling an idle flag is insufficient because a task can begin between the check and replacement. Defer when any owned participant has work or unsaved state.
5. Persist intent, then request acknowledged graceful shutdown of the affected component graph. Observe actual process exit and release of lifetime leases. The installer must run from outside the software it replaces.
6. Apply through the installation adapter, retaining exact previous software and compatible integration metadata. Update selection atomically where supported; use a durable journal across operations that cannot be one filesystem transaction.
7. Independently verify installed identity, owned registrations and payload. Run bounded local health checks in disposable state, without a paid model request or replaying a conversation action.
8. Record completion, release admission, and reopen only the components that were previously active and remain allowed by user preferences. Restore drafts and session references through durable state. Report actual running identity separately from selected identity.

The component graph includes primary and secondary windows, the mobile Qt window and host, browser native hosts/connections, owned harness workers, managed DSH integration, dictation/recording/paste operations, speech work and affected memory jobs. Discovery must not start any of these services merely to check a release. An unrelated external DSH, memory, voice or NAS service cannot be stopped through an assumption of ownership.

Reuse the Windows [shared coordinator](https://github.com/ManoloRemiddi/augmentor-agent/blob/e52ee862aa9f7c5515f3c25f6936d3f08021b943/services/lifecycle/update.py) and [durable journal](https://github.com/ManoloRemiddi/augmentor-agent/blob/e52ee862aa9f7c5515f3c25f6936d3f08021b943/services/lifecycle/update_journal.py) after reviewing integration with current main. Extend the existing lifecycle rather than implementing parallel update behavior in each surface. The update API belongs to trusted application administration; model tools and embedded SDK workspaces should not gain authority to install software from page/session text.

## Installation adapters

| Installation | Recommended path | Automatic installation boundary |
| --- | --- | --- |
| Managed Linux user-local release | Verify downloaded artifact, stage separately, coordinate owned integrations, use existing atomic desktop selection. | First candidate for app-managed updates; qualify dependency upgrades and independent recovery before enabling. |
| Debian or Fedora package | Obtain matching artifacts, prepare the affected component graph and invoke the supported package-manager path. A signed package repository is a later distribution option. | Respect administrator authentication and package ownership. User consent cannot grant filesystem privileges or bypass busy package hooks. |
| macOS bundle | Evaluate Sparkle 2 delivery/installation with a small native integration; retain Augmentor preparation, services, journal and health boundaries. | Automatic production delivery needs updater trust keys and validated signing/permission behavior. Current ad-hoc previews can first provide notification and explicit manual guidance. |
| Windows | Continue PR #20's Inno/WinSparkle and coordinator integration. | Require customer trust configuration, real different-version upgrade/recovery, current-main component convergence and UI wiring. Existing same-build evidence is insufficient. |
| Unpacked Chromium extension | Stage matching files and give truthful reload/reconnect guidance. | Treat full unattended extension adoption as unavailable until demonstrated. Store delivery is the eventual supported automatic path. |
| Home deployment and Android wrapper | Report component compatibility and route to the owning deployment or application distribution. | Do not grant the desktop updater NAS/container or phone installation authority implicitly. |
| Source/development/mixed artifact | Display release information and identify the supported migration route. | Preserve local work; no automatic Git pull, reset, dependency install or replacement of an unrecognized build. |

Code-signing, archive-signing and HTTPS serve different purposes. A matching checksum is not publisher authentication if an attacker can replace the checksum alongside the download. An updater key embedded in an approved application can authenticate future updates, but does not make an ad-hoc Mac app notarized or an unsigned Windows installer trusted by SmartScreen. The existing owner-approved preview choices remain the context for manual preview delivery; this proposal does not change them or request them again.

The Mac remains a PySide6/Qt app. A Sparkle bridge is a packaging/lifecycle adapter, not a UI rewrite. Its interaction with launchd, shortcut services, Browser native messaging, installation locks and macOS privacy permissions needs real installed testing. Maintaining bundle identity and signing identity is necessary, but cannot be treated as proof that permissions survive every upgrade.

Chrome normally owns automatic updates for store-delivered extensions. Google's supported self-hosted extension distribution is platform-limited, so adding an `update_url` to the current unpacked extension is not a general Mac/Windows solution. Store updates and companion updates will not be simultaneous. Plan a narrow, versioned compatibility window and a compatibility/status exchange that still explains recovery when the main handshake refuses; retain the current strict guard until that contract is implemented and tested. [Chrome distribution rules](https://developer.chrome.com/docs/extensions/how-to/distribute/host-on-linux).

## Risks and blind spots

| Risk | Existing evidence or gap | Required control |
| --- | --- | --- |
| Old installations never receive the checker | Public builds lack this feature. | Publish an updater-enabled bridge release and a supported one-time manual migration; show upgrade guidance on existing download channels. |
| Wrong release offered | Linux/Mac assets are separate prereleases; Windows is an unmerged development path at inspection. | Filter by channel, target and installation method; use the explicit promoted catalog. |
| Same version conceals different builds | Multiple 0.2.12 Mac previews and managed mixed artifacts exist. | Add exact release identity and authenticated ordering; never infer provenance from version alone. |
| Partial component upgrade | Browser/companion and desktop/runtime checks are strict; DSH integration also has a product identity. | Install a coordinated compatible set with backups and owned-configuration checks. |
| Work starts after an idle check | Several surfaces can submit tasks or use the microphone. | Reserve admission across the graph and verify shutdown, rather than relying on a status snapshot. |
| Download becomes code execution | Linux stage imports candidate code; old Browser logic extracts over its own tree. | Authenticate and bound remote bytes before imports/extraction; keep legacy unified-mode refusal. |
| Compromised or stale distribution | Current release hashes do not provide independent publisher keys. | Pinned trust roots, signed targets, anti-rollback/freshness rules, key rotation and a documented bad-release procedure. |
| Rollback restores incompatible software | Linux rollback selects a desktop but leaves external integrations/data unchanged; its preflight needs the matching live DSH. | Retain the dependency set and prove rollback/data readability; support independent offline recovery where feasible. |
| Interrupted installation cannot repair itself | The main payload or interpreter may be missing or mixed. | Keep a trusted recovery observer/installer outside the replaced payload; inspect fresh state before deciding. Never replay an uncertain saved command. |
| External dependencies drift | Codex is separately installed; voice and memory have separate repositories/services. | Pin supported requirements, report prerequisites, and update only expressly owned components. Preserve models, credentials and placement. |
| Store extension advances first | Strict equality can block both chat and settings operations. | Define and test controlled compatibility plus a limited recovery/status path; allow explicit reload guidance in preview. |
| Disk exhaustion and daily churn | Mac public artifact is about 523 MB; Windows development payloads exceed 1 GB. | Budget download/extraction/backup space and retain known-good builds under a bounded policy. Start with full artifacts; add deltas only with a verified full-download fallback. |
| Migration destroys data or rollback | `dataSchema` fields exist but do not describe every external database or harness store. | Inventory all stores and migration owners. Back up before destructive migration; never promise rollback after incompatible writes. |
| Scheduler or network hides a stale result | Offline machines, proxies, wrong clocks and rate limiting occur. | Bounded timeouts/backoff, cached last-success age and explicit errors; expired metadata blocks installation, not ordinary use of existing software. |

Saved history is not the whole preservation problem. Unsaved drafts, pending approvals, queued prompts, active recordings, unpasted transcription and unknown action outcomes need explicit refusal or durable recovery semantics. Automatically reopening a conversation must never re-submit its last prompt or tool action.

## Release and qualification sequence

**First delivery: identity, release discovery and notification.** Define the catalog/installation receipt, preview ordering and per-platform eligibility. Add the same check/status semantics to native and Browser settings, and supported download/release-note actions. Keep a failed network check independent of chat readiness. Provide a bridge-release migration path. No automatic installation is required for this first useful delivery.

**Second delivery: trusted downloads and guided updates.** Provision publisher trust, stage verified downloads, show progress/cancel, budget disk and retain recovery artifacts. Connect each qualified installer adapter to the shared coordinator. Mac and Windows must receive explicit supported upgrade procedures before the UI offers installation. A fresh-install wrapper must not be reused against existing private state; current complete setup deliberately refuses that case.

**Third delivery: optional automatic installation.** Enable per installation method only after actual N-to-N+1 and previous-version restoration tests, failure injection, user-state preservation and independently observed health pass. Keep previews explicit. Permit auto-download while busy, but defer installation whenever active work or drafts cannot be preserved. A permanently active service should expose a pending update, not be forcibly terminated to meet a timer.

**Operational follow-up: release promotion and staged rollout.** Automate build, artifact validation, signing and final catalog promotion. Start with a small opted-in test group; expand only with adequate observed acceptance. Revocation stops new delivery. A client already on a bad release needs an authenticated recovery/fixed-release policy; switching the feed backwards must not weaken anti-rollback rules. Proactively renew expiring metadata even when no new product version is published, with monitored publication failures and tested key rotation.

The minimum acceptance matrix covers current qualified Linux packages and managed releases, Apple-silicon Mac bundles on the supported OS range, Windows x64/ARM64 when merged and release-qualified, and Browser companion/extension combinations. Also qualify optional Home/mobile participation and each supported harness separately. Do not infer Intel Mac, Raspberry Pi Linux ARM64, all distributions or physical OS acceptance from a same-CPU component build.

Required failure tests include wrong OS/CPU/channel, same-version preview ordering, mismatched or missing components, modified/expired/replayed metadata, revoked builds, unsafe archives, missing prerequisite, network interruption, full disk, simultaneous update attempts, every durable crash boundary, offline repair, active tool/model work, drafts/approvals/queues, voice/dictation activity, edited presets and lost shutdown/apply acknowledgments. Actual package tests must prove data retention, no repeated actions, complete payload and registration identity, graceful reopen and truthful selected/running status. Fixture checks and physical permission/microphone tests remain separately labelled.

The first concrete implementation should therefore be the shared release catalog and daily discovery/status feature, designed to attach to the existing lifecycle work. The longest remaining work is platform coordination and recovery qualification, especially extension adoption, external dependencies and Windows cross-version delivery.
