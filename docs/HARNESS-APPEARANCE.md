<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Harness appearance across restarts

The original DSH Settings General row keeps its Light, Dark and System controls.
On a modern operator Host, an explicit choice now belongs to the private Pi
profile, so a new browser origin after restarting or updating the MX preview
does not lose it. The [requested Augmentor mark and Dark text corrections](HARNESS-BRAND.md)
remain in the original header, collapsed rail and welcome seats. This binding
changes persistence and synchronization; supplier layout, CSS and motion remain
unchanged.

## Preference contract

`config/harness-appearance.json` contains only schema
`augmentor-harness-appearance/1`, a revision and `light`, `dark` or `system`.
Its revision is separate from `settings.json`, shortcuts, Context preferences,
diagnostic capture and model selection. Reading an absent record returns revision
zero with a null preference and creates no file. An existing browser-local choice
then remains in effect until the owner explicitly selects a profile preference;
there is no implicit migration write. Accepted choices also update the existing
local browser cache. System stores the choice, not its resolved color: each
device follows its own OS preference without further profile writes.

Operator `appearance.describe` reads the record; `appearance.set` takes the
expected revision and publishes one checked choice. It neither opens an
AgentSession nor changes a conversation or invokes a provider/tool. Unix records
are bounded to 4 KiB, private, regular and single-link. Exclusive temporary writes,
file/directory sync and atomic replacement preserve the committed value on a
denied write. Unsupported/corrupt/linked/public records are preserved for repair;
errors do not disclose their contents. Existing Windows private-storage helpers
are retained, but physical Windows qualification remains open.

The existing live session poll carries only an operator appearance revision hint.
A ready operator with no selected conversation polls the cached revision through
`GET /api/appearance/revision`; it does not create a conversation to synchronize
theme. The endpoint performs no file read or SDK work. A higher hint triggers a
checked preference read. Pending saves defer hints, older revisions cannot
overwrite an accepted choice, and a retired view cannot apply a late response.
Read-only inspectors cannot read/write the profile or receive its revision. Their
theme controls, and compatibility with old Hosts without the capability, retain
local browser styling.

Modern profile failures do not silently fall back to a browser-only save. The
original controls are briefly disabled while a read/write is pending and show
errors through the existing notice owner. Unknown save outcomes are never
automatically retried or hidden by a peer hint. Reopening Settings explicitly
reads the committed choice before another edit.

## Qualification — October 13

The previous installed runtime **d79e476** loses Dark after a real fixture Host
and Chrome restart at a different loopback origin. That comparator is retained;
it uses independently authored profiles and no owner conversation or inference.
An initial driver queried a nonexistent close aria-label; the corrected test uses
the original Escape behavior. An early renderer binding mistakenly addressed
`settingsShell.state`; the actual supplier observable is used directly. A denied
write test also caught a generic storage helper normalizing parent permissions;
the appearance writer now preserves those permissions and the prior bytes.

Focused backend/client/real Host/original Settings/brand checks initially pass
19/19. A strengthened original GUI case then catches missing peer updates on the
welcome page: session polling requires a conversation. The cached operator-only
revision endpoint fixes that case without manufacturing a session. Final source,
ordinary artifact and immutable candidate qualification follow separately below.

Tests use real Pi Host/SDK/HTTP and Chrome for cold new-origin recovery, live peer
choices and OS System changes, with zero fixture model requests. Pure/store tests
cover stale writes, private-file guards, failed writes, duplicate/retired responses,
lost acknowledgments and unchanged global/model/auth state. HTTP tests verify
operator authority and inspector exclusion against the selected test runtime.
The original Appearance row, shell focus/actions and unchanged timing deadlines
remain exercised by the existing Settings and brand tests.

Authentication tokens and HTTP origins retain their existing lifetimes. Stable
links, automatic reconnect, selected-tab/placement restoration and full migration
are separate open gates. This feature does not alter native or standalone Browser
appearance preferences. MX is qualified first; Windows, macOS and further Linux
implementation/physical checks await owner MX feedback. Public distribution,
live-provider/privacy and known CI gates remain open.

### Qualified source

Final strict check/build pass with Node **24.19.0**. The exact 79-file MX cohort
passes **415/415**, zero failures, skips or cancellations, using two workers,
matching isolated QtTest and unchanged deadlines. Five source packaging cases
also pass. The strengthened cold/System/welcome-peer case passes in this complete
cohort, after retaining the failed no-conversation comparator. The selected
installed preview remains **d79e476 / 20261013-124421-a8c9d4c5** until a separate
ordinary assembly, sealed qualification and guarded idle adoption succeed.

### Ordinary and installed MX qualification

Runtime **97897cf82eee3277ae7ad664d695571eb5de112a** is selected and running in
private MX release **20261013-142001-1f7f7f96**, product **0.2.13**, artifact
**05c20ef7bfb07c926cacc8d548a0dc734e77c4c68c9a57aab9efa551327f7ada**.
The earlier source-only selection paragraph records the preceding checkpoint.

Source and separate ordinary artifact each pass **415/415 across 79 files**, plus
five packaging cases. **163 sealed checks across 19 files** pass with the actual
bundled Node **24.19.0**, candidate runtime/SDK/GUI and matching ordinary pure
drivers. Final candidate and selected inventories match all **23,914** entries.
Compiled GUI/JS, app bindings, licences and Node match the tested ordinary inputs;
no selected release is patched. The preceding **151 npm instances**, **20,801
dependency files**, nine native/Wasm binaries, 786 licence/provenance files and
580 MIT/108 Apache supplier records retain their bytes. Only authored bindings
and the new authored profile module change; no supplier source/CSS is changed.

Fresh idle maintenance closes the exact prior Native/Host before normal updater
activation and stable detached Native startup. Selected/running roots agree and
Native is online/model-ready. At adoption, all **twelve histories/queues/session IDs**, drafts,
attachments, settings/revision, model/auth profiles, production selection and
model-router arguments remain preserved. All **247 prior saved files** are
byte-identical; no placeholder, provider request or automatic preference write
is added. The actual installed Host advertises appearance and its absent-record
read still creates no file. Choosing Light/Dark/System once now saves that choice
to the profile; existing browser-local style is not silently promoted.

The old owner browser tab remains a blocked error page under browser URL policy.
The independent original-GUI candidate cases qualify cold recovery, System,
peer updates, logos and settings colors; a new installed-owner visual read is
not claimed. The owner receives the fresh private HTTP link for manual opening.
Private links, profiles and logs are excluded from publication. Stable addresses,
authentication/reconnect/placement, full migration, live/privacy/public
distribution and platform/CI gates remain open. The preceding runtime stays
available for rollback; further OS implementation awaits MX feedback.

A later read-only maintenance check observes a Native draft/busy flag while the
new roots remain online/model-ready and all installed entries still verify. That
new owner activity is preserved; no second restart or palette change is attempted.
The initial idle adoption proof remains distinct from this later running check.
