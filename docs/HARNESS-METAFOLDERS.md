<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Original Metafolder interface on Pi

The Harness source now offers **Settings → Plugins → Metafolders**. Enabling it
mounts the original public Metafolder browser; disabling it restores the existing
DSH workspace browser and retains saved groups. A new profile defaults to the
existing workspace browser. This is source qualification, not installed rollout.
The [plugin parity register](HARNESS-PLUGIN-PARITY.md) retains the wider migration gates.

## Public source and original presentation

Selected supplier: [DSH Metafolder Plugin 1.2.1](https://github.com/ManoloRemiddi/DSH-Metafolder-Plugin/tree/a5332d902e147e824231a5470d3e2822b9288719),
commit **a5332d902e147e824231a5470d3e2822b9288719**, MIT, Copyright 2026 Manolo
Remiddi. The complete licence, package manifest, README and original 1,173-line
client are retained. `client.js` is marked as adapted; original/adapted hashes
are in `apps/harness/vendor/dsh-metafolder/SOURCE.json` and the served provenance.
The entire supplier CSS block remains identical to the original client.

The build wraps the original dynamic-client body as a static module using the
application's existing React instance. It selects no Cordis loader, DSH Host
module, registry service or physical workspace mover. The browser notices retain
the full MIT licence. Existing 580 DSH MIT and 108 dsh-context Apache records,
brand assets, dependencies and their licences are preserved.

The copied layout supplies named/colored/collapsible groups, workspace/session
assignment, pointer drag, group menus, Workspace/Flat and Manual/Updated views,
search, typed paths/browsing and workspace/session actions. Adaptations bind
current Pi handlers and shortcut requests, preserve pin markers/order/hover/menu
actions and archived filtering/restore, normalize React SVG attribute names and
use semantic menu clicks. Explicit group deletion also clears its session
assignments and collapse state; real workspace paths stay intact.

## Ownership and persistence

Group display metadata has its own private `harness-metafolders.json` record
under the Pi config directory, independent of model/auth/settings/history files.
`metafolders.describe` and `metafolders.set` are operator APIs with a separate
revision and complete-value compare-and-save. Workspace IDs can contain paths;
assignments never authorize filesystem moves or model tools.

Absent reads create no record and import no browser-local DSH groups. Explicit
enable/disable and group/view changes persist accepted values across Host and
browser-origin changes. Initial expansion of the current workspace is derived
locally and does not save during render or cold opening. Existing session manual
order and archived filter use their current DSH view owner. Operator polling
shares cached revision hints with appearance, including the welcome page, without
creating a conversation or polling model/filesystem state.

Saves are bounded to 128 groups, 4,096 entries per map and 64 KiB for values.
The record is bounded/private, rejects links, wrong ownership/modes, invalid
UTF-8/JSON, unknown schemas/fields, duplicate groups and unsafe shapes. Linux
writes use an exclusive private temporary file, file sync, rename and directory
sync. A stale or unknown acknowledgment freezes further grouping writes until an
explicit refresh confirms the saved values; nothing is automatically replayed.
Late responses cannot populate a retired inspector or conversation view.

Inspectors and old Hosts do not read or mount the group profile. Read-only links
deny both APIs and receive no group revision hints. Normal actions reuse the
current Pi conversation/workspace owners: Fork adds no second navigation after
its existing draft-fenced handler, Archive keeps its running-work confirmation,
and asynchronous workspace operations reject stale view continuations. There is
no new agent, provider request, tool grant or independent execution loop.

## Qualification and remaining work

Tested implementation: **207aed299534801637e4c3263f1166d3fe532936**. Subsequent
qualification-record edits change documentation only.

Focused feature qualification passes **9/9 across two files**: eight profile,
failure, cold-Host and supplier-closure cases plus the actual copied-interface
Chromium workflow. It exercises enable, group creation/color, workspace menus,
pin, Fork, archive/restore, group rename/order/delete, real pointer session
grouping, both palettes and fresh Host/browser origins. Parent history and the
actual synthetic provider request log remain identical after organization,
branching, inspection and cold reads. Separate initial regression qualification
passes 29/29. The final complete MX cohort passes **453/453 across 85 files**,
with Node 24.19.0, two workers, no skips and unchanged deadlines.
Strict check/build passes; seven corrected licence-inventory fixtures and five
existing notice/production-workspace packaging cases pass.

This does not yet qualify ordinary/sealed/installed artifacts, owner grouping
import, broad corpus search, every directory/keyboard/rail/manual-order flow,
all accessibility behavior or physical workspace moves. Further tests and the
owner's MX feedback remain required for full plugin parity. Live Qwen/speech,
other named plugins, full privacy/distribution and other-platform gates remain.

The installed preview stays appearance runtime **97897cf**; the older qualified
combined artifact **2c4ca0b** remains unselected and does not contain this follow-up.
No selected release is patched, no owner draft is discarded and no model, GPU,
context/concurrency/precision or speech setting is changed. Further OS rollout
still waits for owner MX feedback. DSH remains available for unqualified workflows.

Shared presentation/runtime metadata is common source. No OS-specific launcher,
service or speech adapter is changed. Linux private-file durability is exercised;
Windows' existing atomic-JSON fallback and macOS installed behavior remain
unqualified. Prior `835ec1a` Linux CI passed the Node stage and then failed the
seven minimal licence fixtures; their missing synthetic root manifest is now
corrected. The production inventory rules are unchanged. New-head remote CI
and known further-platform failures remain separate from these source results.
