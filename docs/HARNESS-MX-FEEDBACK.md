<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# MX review feedback: model picker and composer

The October 16 owner feedback takes priority over voice, other operating systems,
public installers and optional integrations. The immediate target is a usable
review on the owner's MX machine. Preserve the original DSH presentation and
current review conversations while preparing a separately staged correction.

## Model picker

The original dropdown scrolled its current selection into view on entering the
Model pane. The local Qwen provider appears near the end of the large catalog,
which reproduced the owner's bottom-first opening. The Harness binding also
discarded the profile's pin/hidden settings, and provided the wrong result shape
to the supplier selection callback.

The marked MIT ModelSelect adaptation accepts optional curation and top-first
opening. Harness enables both. Pins keep their saved order in a Pinned group,
hidden models disappear from the picker, and pinned rows are removed from their
provider group. Exact provider/model identities remain separate even when two
providers advertise the same model ID. The unfiltered directory retains the
selected model's label and effort. Keyboard navigation and explicit selection
remain; successful selections close the menu, failures show the original toast
and never retry the request. Upstream defaults remain available to other callers.

Settings now has **Model Picker Augmented**, following the owner's MIT plugin:
search, pin/unpin, hide/show, and move-up/down controls. Its settings-card CSS
comes from the already tracked public 1.1.2 archive (SHA-256
`9a2c2e17c128da3565520b5f39cb85606823440ee0e1e4c2316f806fc58914fc`),
`package/lib/client.js`. The original notice is retained in
`licenses/dsh-model-picker-augmented.txt` and compiled GUI notices. Presentation
binds to the existing Pi owner, not the plugin's DSH Host or patching machinery.
Provider configuration and discovery keep their existing Models page.

`models.curate` applies one pin/visibility/order action against the exact settings
revision. Stale edits refuse, unknown outcomes are not retried, and restricted
inspectors cannot call it. Choices persist in the private Harness profile.

## Context meter and browser access

The meter's former centered position below the composer was the selected DSH
baseline's dock placement. An optional InputBar adaptation places the same meter
inside the existing toolbar; Harness selects it. Original meter data, popup,
styling and default dock placement remain available. The existing toolbar wraps
on narrow widths without a detached context indicator or horizontal overflow.

A bare loopback URL does not authenticate a new browser. Supply the complete
private link returned by `harness.open`, including its `#token=…` fragment. The
fragment is consumed into that tab's session storage and removed from the address
bar. Copying the shortened address afterward does not transfer access. Keep
authentication enabled and private links out of public documentation/logs.

## Qualification

The source build and **28 cases across seven targeted MX files** pass with two
workers, zero skips/failures/cancellations and unchanged test deadlines. The new
real Chromium/Pi test checks top-first opening with a tail selection, persistence
across reload, ordered pins, hide/show, no duplicates, matching IDs on separate
providers, keyboard search/selection, exact rejected selection without replay,
stale writes and authentication. It checks meter containment at 1440, 666 and
420 pixels. Only the declared rejected model choice produces one matched HTTP
400/network log; unexpected page/network errors fail. One authored-provider seed
supplies context usage; curation/selection/layout checks send no further provider
requests. This is fixture evidence, not another live Qwen inference claim.

Existing provider forms, two-window stale-edit fencing, account restrictions,
SDK configuration, composer interactions and attachments pass in the same run.
Initial driver/empty-context/expected-HTTP assertion failures remain in local
evidence. Mounting every curation card beneath Models initially interfered with
its provider menu; the plugin now has its own original-shell settings section,
and the original Models workflow passes without weakened assertions.

## Corrected private review

Application/source `1f050f03410272611944158bb3dde9f4eccf79c9` is staged in
**20261016-102350-38ccb6f8**, seal
`a67bb9f8048b8902058004c87782a508ca10202831bcf71f84cb6653d3db1123`.
The same 28 focused cases pass against the exact staged runtime/GUI with its
bundled Node; 16 notice/private-boundary cases pass. All 24,546 sealed files and
1,069 compiled inputs verify after owner-browser QA. Production dependencies,
Node and components retain the preceding verified baseline bytes. An initial
unsealed assembly omitted the existing preferred runtime supplier source; it
remains preserved and the complete assembly passes the original notice checks.

The private review is running and connected. Browser QA confirms first group
Pinned, local Qwen first exactly once, initial scroll zero, readable curation
controls in the original Settings shell, and zero console warnings/errors. Its
profile copies only the preceding review configuration, starts with local Qwen
pinned and one empty conversation, and submits no prompts/audio. It reuses the
existing review memory gateway and CPU recognition service without installing or
moving either. Existing conversation history stays in the preceding review;
there is no production-profile or conversation migration. Earlier review processes
and selected installation remain intact. Private links and filesystem/profile
records stay outside public evidence. See the [portable review
record](../release/harness-mx-picker-review-20261016.json).

This qualifies the requested local feedback changes. Broader MX workflow/migration
acceptance remains open; voice, later platforms, full-release CI and public binary
redistribution remain separate. No DSH retirement, installed activation or merge.
