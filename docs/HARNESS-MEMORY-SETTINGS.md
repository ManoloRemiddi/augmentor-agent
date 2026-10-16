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
