<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

[Local model identity](HARNESS-LOCAL-MODEL-ROUTES.md) now adds generation-time
verification for explicitly named llama.cpp providers. The picker remains a
configured/credential-available catalogue; it does not claim that all local
profiles are loaded. Dormant selections/pins stay available, while a mismatch
refuses prompt dispatch without loading or substituting a model.

# Configured provider catalogue for MX review

## Effort menu labels — October 20 follow-up

The Harness adaptation supplied each reasoning choice as `{id, label}`, while
the original DSH `ModelSelect` consumes `{id, name}`. The result was real,
clickable choices with blank visible/accessibility labels, even though the Host
advertised supported effort levels. The source fix changes that adaptation to
`{id, name}`; the original supplier UI and the runtime reasoning policy remain
unchanged. It applies to the shared Harness web UI on Linux and macOS, not the
separate Agent Desktop/Browser effort controls.

**Off is the saved effort, not an Auto indicator.** Adaptive reasoning is a
separate per-conversation mode and profile policy. It changes request effort only
when enabled for the conversation preset and explicitly mapped for the exact
model. Without a mapping it retains the saved effort. A model profile advertising
only `off` cannot offer adjustable effort; that metadata alone does not establish
whether the remote model performs reasoning internally. See [reasoning
controls](AUGMENTOR-HARNESS.md#adaptive-reasoning-and-effective-thinking-controls).

Read-only inspection of the installed Air confirmed the same defective
projection, two configured DeepSeek models with multiple advertised effort levels,
two local Qwen profiles with only `off`, and an enabled Adaptive policy with no
model mappings. No owner model, endpoint or reasoning preference was changed.

A rendered regression first fails with five blank labels instead of the five
advertised levels. After the fix, **20 checks pass** across the real Chromium
picker, reasoning controls/provider-request test and public-hook policy tests.
The picker test selects `high` through the actual menu, verifies Manual mode and
saved effort, reloads and verifies the checked `high` row, then selects `off`.
These setting changes dispatch no provider requests or history edits. Existing
pin/order/search/credential-refusal and responsive-meter checks still pass. The
previous credential-refusal assertion was updated to the current reconnect
message; rejection remains required. Builds/tests used managed disposable
storage, and completed unreferenced scratch was removed after inspection.

This is a tested **source correction**. No selected release or running owner was
changed in this follow-up; an installed update and owner-browser verification
must be recorded separately for the confirmed target installation.

### Installed on MX, Air and Mini — October 20

The owner's clarification that every Harness installation is affected authorizes
the installed follow-up. Source correction **63004ee6** is now applied to both
registered MX profiles and the personal Air and Mini. The normal MX owner and
both Mac owners run the corrected packages. The older MX review remains inactive;
its registered selection is corrected for its next ordinary launch.

| Target | Artifact SHA-256 prefix | Installed verification |
| --- | --- | --- |
| MX older review | `acc26f87c7f3` | Exact rendered picker test; registered, remains inactive |
| MX current Harness | `0ce06166c4c9` | Exact rendered picker test and actual running GUI/reload |
| MacBook Air | `a3be9f2e690d` | Exact Comet picker test and actual running GUI/reload |
| Mac Mini | `f3b8eec96e59` | Exact Comet picker test and actual running GUI/reload |

This is a bounded backport to each existing package. It changes the authored
source property and its equivalent compiled property, updates the three affected
esbuild byte counts, and adds an explicit overlay receipt. Every other application
file, runtime, native binary, dependency and supplier input is preserved. The
original selected roots are retained for rollback; no selected release was
patched in place. The Mac base is the existing research/Wiki artifact
**44ae92b3 / 41629b72…64134**. The two Mac artifact identities differ in the
overlay receipt's file permissions, not in the functional correction.

Each exact candidate passes the existing rendered picker test, including visible
effort labels, actual `high` selection, Manual mode, reload/checkmark and `off`
restoration, with no setting-triggered provider request. The Mac test invocation
uses private canonical short temporary paths, an explicitly created owned Comet
test tab and Command+A. Historical bases accept only their two exact known
authentication-refusal messages. No deadline or assertion of effort behavior is
relaxed, and no case is skipped. Earlier fixture failures were retained as
diagnostics and corrected before activation.

Guarded owner shutdown and normal startup controllers activate the new packages.
The MX registrar requires the sealed installed-controller/menu path; its existing
opener bytes and menus are retained. An initial old-owner restart during the
registration interval was detected by the exact-root guard, then safely settled
after the new registration was durable. Both Mac replacements use their stable
`current` selection and existing launchd recovery. A transient closing response
was observed during restart; final new-owner readiness is verified separately.

On all three running installations, a fresh isolated browser checks that the
served JavaScript hash matches the selected artifact and that the actual Effort
menu exposes the Host's advertised levels before and after reload. Existing idle
local-model conversations advertise only `off`; those live checks truthfully
show one labelled option. Their saved reasoning mode/effort/revision and session
counts remain unchanged, with **zero chat prompts**. Configuration hashes and
every existing saved-history prefix verify preserved. Both Mac inventories
contain **47,141** inputs and verify after live use. Managed MX scratch and Mac
disposable application copies are removed; small private receipts and rollback
roots remain.

Already-open Harness tabs need a reload to replace their in-memory GUI. The Air's
idle Agent Desktop was closed through its guard, reopened normally and verifies
online/model-ready. MX Agent Desktop initially retained its unsent draft and old
selected-root binding. After the owner explicitly confirmed saving the draft and
closing the window, inspection showed that closing had hidden the application
in the tray. The identified, idle background Desktop process was stopped with
SIGTERM and reopened through the normal installed launcher. It now verifies
online/model-ready, with empty connection/session-restoration errors and the
same selected Desktop package. No adaptive mappings or provider capabilities
were changed, and no physical reboot is claimed.

[Portable installed record](../release/harness-effort-picker-installed-20261020.json).

The owner's October 16 feedback identified a truthfulness gap: the previous
review's picker listed Pi's complete installed catalogue (42 providers/1,564
models) despite its private profile configuring one provider. Pin/scroll tests
covered mechanics, not parity with the owner's actual DSH configuration.

Read-only authenticated inspection of the running DSH owner establishes the
reference: ten model groups, 431 model entries and twelve saved pin references.
Ten pins match the current catalogue; two are historical references. Three saved
hidden references include one current model. One legacy provider alias lacks its
configured credential reference. These are configuration/credential observations,
not endpoint-health or successful inference claims.

## Picker contract

`models.list` now exposes configured profiles, credential-ready providers and
explicitly registered extension providers. Installed providers with no setup do
not appear in the conversation picker or curation page. Provider setup/discovery
retains the full supported provider directory in its explicit settings flow.

An explicit profile model list bounds that provider's picker entries, including
for a built-in provider whose SDK catalogue contains additional models. Profile
provider/model order and display names are retained. Declared models lacking
credentials remain inspectable with **Credentials required** in the original
dropdown. This label does not infer endpoint health. Exact provider/model keys,
pin order, hidden filtering, effort controls and selection ownership are preserved.

The profile projection contains names and model IDs only. It does not resolve
credential commands, expose keys/headers or probe endpoints. Unapplied external
profile edits refuse the projection until an explicit Models refresh reconciles
the SDK; they cannot silently redefine the running catalogue.

## Private owner setup

The local reference import uses the live DSH settings/catalogue rather than an old
settings backup. It preserves declared models, names, limits, compatible metadata,
endpoints and existing credential references in a separate private Pi profile.
No DSH files, model/GPU service configuration or production installation change.
Private configuration, keys, endpoint addresses and operator links stay out of
public source, fixtures, archives and CI. The public tests use authored providers.

The effective matching pins/hidden entries are adopted; historical references stay
preserved in DSH and the private reference receipt. No conversation migration is
implied. Model capabilities and provider transport breadth still need their own
workflow qualification; listing an imported configuration does not certify every
provider or GPU alias online.

## Qualification

Source build and 28 targeted MX cases pass across seven files, two workers,
unchanged deadlines and no skips/failures/cancellations. The rendered Pi/Chromium
case now declares a bounded custom catalogue plus a single-model built-in profile
and a credential-missing provider. It asserts exact groups/count/order/names,
absence of unconfigured built-ins, exact built-in subset, visible credential
status, pin persistence/identity, selection/error/no-replay and responsive meter
containment. Existing Models/forms, peer fencing, SDK reconciliation, commands
and attachments remain covered. A command-key scope read stays nonexecuting and
an unapplied external edit refuses the picker projection.

## Corrected private review

Application `1dd0fc0c6d700c7d58e46a85357aa90f3dcce50f` is staged in
**20261016-105557-8890e8e5**, artifact
`0f3c82e4de5cab82b2e4ed99c57a1bebd800d227dde093c59e1ab76da58e9efb`.
The same 28 targeted cases pass against its staged runtime/GUI with bundled Node;
16 licence/private-boundary cases pass. All 24,548 sealed and 1,069
compiled inputs verify after owner-browser QA, with production dependencies,
Node and components unchanged from the verified preceding release.

A private comparison asserts equality of every provider name, model ID/name and
provider/model order against the live DSH reference, plus exact effective pin and
hidden preferences and the original default model. The rendered original picker
shows 430 visible entries, ten matching pins in the original order, initial scroll
zero and no console warnings/errors. Nine providers have the referenced credential
material; the legacy credential-missing alias has an explicit status. No inference
or endpoint-health probe is submitted during this comparison or owner QA.

The separate profile imports the live provider settings and matching curation,
retains one empty conversation and leaves prior review histories intact. DSH's
historical references remain preserved; personal settings/keys and the operator
link are not included in public evidence. Original DSH and model/GPU services,
selected installation and existing review processes remain unchanged. Voice and
other operating systems remain deferred. See the [portable review
record](../release/harness-configured-models-review-20261016.json).
