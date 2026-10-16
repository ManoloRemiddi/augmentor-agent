<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Shared automatic-memory settings

The original DSH **Settings → Plugins** now exposes the existing automatic-memory
controls. The native automatic-memory panel uses the same companion and state.
This adds no second conversational owner, extraction loop or settings database.
The supplier shell, navigation, controls, CSS and Augmentor marks are preserved.

The panel shows capture/recall state, processing pause, transcript/pending/stopped
counts and the **configured memory request mode**. `off` means the local engine
setup selected thinking off for memory requests; `default` delegates that choice
to the server. A missing/unknown choice is labelled accordingly. Configuration is
not proof of the running provider request: actual transport qualification lives in
[the full memory proof](PI-MEMORY-LIVE.md). Chat/voice retain their separate settings.
Changing mode still requires explicit local engine setup; the panel does not
restart an engine, change a model or silently adopt the proof backport.

**Pause automatic memory** disables new capture and recall and also pauses
processing. Stored records remain. **Resume automatic memory** resumes capture
and recall while retaining the processing pause. Processing has its own explicit
Pause/Resume control; resuming it creates no activity lease or inference budget.
Existing limits and active tool-window admission still apply. If a call is active,
the status can report pausing until that call settles.

## Authority and failure behaviour

The operator Host advertises `memorySettings: true` and exposes only:

| RPC | Allowed parameters | Behaviour |
| --- | --- | --- |
| `memory.status` | none | Sanitized metadata, no engine/network refresh. |
| `memory.configure` | boolean `enabled`, `expectedEnabled` | Explicit capture choice with a current-state guard. |
| `memory.processing` | boolean `paused`, `expectedPaused` | Explicit processing pause with a current-state guard. |

The service compares capture state inside its existing SQLite transaction and
processing state under its existing budget lock. A conflicting current value is
refused. These are boolean state guards, not revision-history/ABA detection.
Existing direct clients without an expected value remain compatible; new UI
mutations require the companion's advertised guard capability. Older companions
remain readable but cannot receive new UI writes. No schema migration is needed.

The browser binding fences late responses by connection epoch and local generation.
An unconfirmed write is never replayed. The controls disable until an explicit
Refresh confirms current state; Refresh itself performs no mutation. Native uses
the same expected states and disables changes after a lost acknowledgement or
malformed result. Errors shown in these controls are static, without private
exception payloads.

The Host status excludes person IDs, PIDs, endpoints, keys, source text and job
payloads. Global memory RPCs are excluded from read-only conversation inspection,
including status. That view does not show this card. No browser route exposes
memory append/bind/activity, a bank/person choice, processing jobs or a mode write.

## Qualification scope

The new Chromium case uses a fresh synthetic configuration with inference
disabled, the actual Host/companion and the original Settings screen. It checks
both themes, text contrast, stale choices, independent pauses, no model request
and inspector exclusion. Common Node cases cover redaction, malformed/legacy
status, lost acknowledgements and retired connections; offscreen Qt cases cover
the existing native controls. Two current-state guard tests fail against the
preceding source because stale writes were accepted. This UI evidence is distinct
from actual Hindsight/Qwen transport and sealed MX review qualification.

The installer/backport adoption and existing-bank migration remain separate
release gates. Source changes do not update an installed or running review.
Linux is the tested target; shared Node contracts are registered in the three-OS
SDK workflow, while hosted results and native/platform artifacts require their
own evidence.

Workspace Browser surfaces retain their existing context-only boundary: global
memory settings belong to standalone Augmentor. This change does not grant a
workspace extension personal/global memory authority. The older unscoped direct
Browser client remains compatible; its legacy manual-library flow is separate.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests:apps/native QT_QPA_PLATFORM=offscreen \
  python3 -m unittest -v test_memory_budget test_hindsight_memory \
  test_hindsight_isolated_proof test_dual_memory test_hindsight_setup \
  test_dual_memory_panel
node --test --test-concurrency=2 tests/memory-settings.test.mjs \
  tests/harness-memory-settings.test.mjs tests/pi-memory-settings.test.mjs \
  tests/harness-memory-settings-chromium.test.mjs tests/harness-server.test.mjs
```

## Qualified MX review — October 16

Application **b7e0afaa86db9e76e3422583f5e9c4a77cbdf314**, product **0.2.13** /
Pi SDK **1.1.0**, is staged as unselected review **20261016-050949-2145f2db**.
The **24,524-entry** seal is SHA-256
`d9a4016e51fbbb1b22a4486354381ac5c9b089e12cdeb850fb4d9b5072cf353b`.
No sealed release is patched to obtain a pass.

| Scope | Result |
| --- | --- |
| Source / fresh ordinary / exact sealed target | Each 761 pass, two existing optional skips, zero failures/cancellations; 134 files, all 55 Harness Chromium files. |
| Common memory / native settings | Source and fresh ordinary each 52 Python and 31 memory Node cases; new controls are also in the wider cohort. |
| Source and licence boundaries | 25 cases pass; Office public redistribution gate remains closed. |
| Frozen input verification | 3,411 tracked, 1,063 compiled, one Node executable, 20,702 dependency inputs and 1,932 Browser test inputs remain unchanged after use. |

Both guard negative controls fail against **dcb157de**, specifically because a
stale write raises no error. Positive cases pass with the same assertions. Build
and type check pass; the existing Office duplicate-key build warning remains.
Existing test bounds/workers stay unchanged, with two cohort workers. The added
shared CI step uses those two workers; its hosted result is separate evidence.

The **full actual Pi/Hindsight/Qwen scenario** also passes against this frozen
application and its frozen driver. All 18 observed memory requests carry
`enable_thinking: false` and finish. Both jobs complete six stages at attempt zero,
with no call failures and respectively **102.33 seconds / 37,515 tokens** and
**93.50 seconds / 25,727 tokens** remaining. Ten conversation requests/two authored
tools verify seed/correction, scoped fresh recall, person/project isolation, exact
historical branch, cold restart, paused capture/ordinary chat and outage recovery
without replay. All proof actors and its engine are terminal; public cache and
source overlay verify. Existing 120-second/65,536-token job/window, 45-second/
4,096-output call, model/server/GPU and source/date/scope contracts are unchanged.
Earlier default-mode failures remain retained and unqualified by this pass.

The owner review starts with a separate empty profile, fresh labelled engine and
volume, explicit memory-only **off** and the verified MIT refresh-default overlay.
Its engine owns no previous banks. The original engine remains **default**. The
existing CPU recognition-only **0.1.22** service is reused without changing its
profile/process; shared distribution pins remain unchanged. Browser QA verifies
both 2px animated marks/themes, Settings text, the configured mode, capture and
processing controls, original Permission/account confirmation, cached recognition
and zero initial sessions/events/jobs/budget rows. QA submits no recording or
model/tool work and restores the initial memory settings. Its browser is closed;
the review Host and its own memory engine intentionally remain available.

Twelve sealed inventories/thirteen review owners plus recognition, the selected
installation, 38 canonical/four original private changes and six model/service
configuration hashes are preserved. Qwen is online. Breeze remains failed below
its unchanged GPU-memory prerequisite; no service retry, GPU move or tuning occurs.

Retained preparation failures include the initial type narrowing, two incorrect
Python module names, an incorrect negative-control class name, expected stale-HTTP
rejection classification, a relative ordinary-driver path, missing preferred
Office licence input in an unsealed assembly, and a sealed-driver working directory
that lacked external test dependencies. They are not counted as passing evidence.
The corrected assembly includes the public preferred vendor source. The corrected
sealed driver uses external public tests/dependencies and the sealed application;
the seal verifies unchanged before and after. No limits, workers or skips change.

For this review only, the engine is prepared by the opt-in
[`hindsight-isolated-proof-engine.py`](../scripts/hindsight-isolated-proof-engine.py)
with the explicit backport/off options, a new private ownership marker and the
unchanged public local-model declaration. Its fresh `hindsight.json` is placed in
the review's private shared-data directory before Host startup; credentials/data
remain outside the seal and public record. It is not a production installer or
existing-bank migration. Startup does not activate the installed selection or add
autostart. The private owner receipt records exact Host/container identities and
the local access link. To retire this review, drain its Host first, then use the
helper's `stop --root` for that exact owned engine. Preserve its volume/profile;
the reused recognition service and original engine belong to other owners.

Physical MX feedback, installed adoption/backport installation and existing-bank
migration, default-mode timing/broader load/semantics, full voice/distribution,
remaining plugin/Home/Office workflows and later OS releases remain open.
[Portable qualification and review evidence](../release/harness-memory-settings-review-20261016.json).

[The installation path](HINDSIGHT-INSTALLATION.md#actual-installation-and-rollback-qualification--october-16)
now qualifies separately with synthetic offline-cache Docker banks and actual
restart/replacement/archive restoration. This does not update the existing owner
review or adopt its data into an installed engine.
