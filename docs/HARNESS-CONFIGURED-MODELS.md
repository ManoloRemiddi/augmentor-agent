<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

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

Staged qualification and the exact private DSH-reference comparison are recorded
after assembly. Voice and other operating systems remain deferred.
