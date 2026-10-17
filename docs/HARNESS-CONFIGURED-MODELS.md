<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

[Local model identity](HARNESS-LOCAL-MODEL-ROUTES.md) now adds generation-time
verification for explicitly named llama.cpp providers. The picker remains a
configured/credential-available catalogue; it does not claim that all local
profiles are loaded. Dormant selections/pins stay available, while a mismatch
refuses prompt dispatch without loading or substituting a model.

# Configured provider catalogue for MX review

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
