<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Matching MX client publication and recovery

`services/dsh/client_publication.py` connects a verified cold archive to the
configuration, startup files and matching build selections. It is an internal
Linux API. It does not discover or stop owner processes, install a Browser
extension, restart ordinary clients, restore databases or establish owner
acceptance. The installed main/pilot and Native app have not been updated by
this source checkpoint.

## Prepare one reviewed cut

Inventory and adopt every real launcher first. In particular, the installed
review opener must honor the deployment gate **before** any owner cut begins.
The source opener now recognizes legacy registrations below `releases/`, holds
the shared launch reader throughout opening/startup and refuses a persistent
`dsh-preservation.json`. An explicit entry `launchData` can identify another
managed deployment location. Non-deployment standalone reviews remain standalone.
Running SDK/shared owners still use their existing data leases; this opener
reader closes the startup gap and is not their lifetime ownership mechanism.

Use `client_publication.maintenance(home, primary_data, pairs, additional_data)`
only after all real callers are idle and stopped. It holds the declared deployment
writers plus the existing DSH and shared-store cold gates. Current process/launcher
maps are advisory; they cannot authorize a later cut. Preserve the current service
command, cwd, environment, provider choices and external retained modules.

Capture the complete reviewed data coverage with `cold_backup.capture`. Then call
`preservation_transaction.prepare(..., cold_backup={root, sha256})`. Preparation
verifies that archive against the still-original covered data, before writing
configuration backups or fences. The configuration journal now uses **schema 3**;
older operators cannot drive it. Recover an older journal with its matching
qualified operator; never edit its schema or relabel its source identity.

`prospective_selections` supplies read-only inputs for the incoming artifact's
`install-desktop-startup.startup_plan(..., selection=...)`. Rendering creates no
directories/backups, writes no files and runs no service command. Ordinary startup
installation does not accept this override and retains its selected-release check.
Load the renderer from the verified incoming artifact. Review the exact output,
Browser-host expectations, registry changes and custom launcher dependencies.

`client_publication.prepare` generates both current/previous selectors from the
verified incoming artifact. Existing selectors, including an existing previous
selection, must be covered by the bound archive with matching bytes/modes. All
declared clients target the primary guarded pair; a primary-store migration is a
separate qualified operation. The exact reviewed bootstrap list is bounded to
128 files / 64 MiB; individual images are at most four MiB. Shared-store/application
payloads are rejected. The reviewed list must also exclude every additional
project/profile payload; binding that exact real list remains an operator duty. Named installed launcher helpers inside
mixed deployment storage are explicitly allowed. Snapshot and replacement checks
retain the startup installer's owned-file rules, including canonical parents and
preservation of observed concurrent edits; they are cooperative ownership checks.

Private before/after images, immutable publication identity and a configuration
ownership marker precede application. Once linked, the configuration-only commit
and reverse APIs refuse mutations outside the matching publication. Markers cover
every declared deployment and DSH home. The actual 64 GiB reserve also applies to
the planned client backup bytes. This stores small bootstrap/configuration images,
not another application build or another copy of project data.

## Apply, finalize or reverse

`apply` resumes only known before/after bytes. Under all cold guards, recovery first
restores its own exact original selectors and explicitly rebinds that verified
guard value; the configuration API's original-selection invariant stays intact.
It applies configuration and reviewed bootstrap images, runs the fixed controlled
backend and actual candidate Native-adapter preflights, rechecks suppliers, then
publishes matching selectors. It keeps all startup fences. No model call is
requested by these preflights.

`finalize` requires the matching after-images, immutable supplier identity and a
still-valid archive. A new guard reruns preflight rather than trusting an old
success flag. Durable finalizing intent precedes marker removal; primary deployment
startup opens last. Interrupted finalization can complete forward. The result says
`clientPublicationComplete`, with `activationComplete`, ordinary-client startup
and owner continuation still **false**. Those remaining steps need actual evidence.

Before finalizing, `rollback` restores exact selector/bootstrap/configuration bytes
and modes, including removing its newly created bootstrap files. It never restores
databases, overwrites an unknown edit or replays a user action. After finalizing
intent, startup may have reopened: automatic old-cut reversal is refused. A fresh
reviewed cold reverse cut must account for any new user work. Keep the original
archive, journals and needed rollback app; do not silently restore old data.

## Qualification and remaining operator work

Local **92 Python** checks pass, including 22 publication cases, plus **10 Node**
checks. Tests interrupt real child processes after each of seven forward writes,
seven reverse writes and all three marker removals. Missing preparation markers,
foreign edits/fences, removed archives, changed suppliers, wrong backends, reserve
refusal, active readers and configuration-only bypass attempts are covered.
Publication health replies are synthetic; the existing nine backend-probe tests
exercise their real namespace/transport boundary separately.

The Node group assembles one temporary sealed application from public source and
opens the actual SDK profile warm/cold. A pending deployment blocks a new private
link without disturbing its existing conversation. History bytes, single-owner
startup, owned menu installation and collision refusal pass with two authored
model requests and zero owner requests. The managed workspace removes this assembly;
no new installed release is retained. Local checks use a read-only host filesystem,
isolated network and real managed-workspace reserve. Hosted small archive fixtures
simulate available capacity, as their logs declare; that is not owner-data evidence.

Remaining: qualify one combined immutable artifact against the real retained
integration; bind and pre-adopt the exact current bootstrap/client graph; verify
the matching loaded Browser; capture one actual cold backup; apply/finalize and
reopen/verify real owner continuation. No more project transfers before pilot
feedback; VR-RasterStudio stays DSH. Voice expansion and later OS remain deferred.
