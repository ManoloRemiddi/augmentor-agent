<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Branch-owned plans and todos

The Pi Harness candidate adds **plan_read**, **plan_update**, private
**session.plan**, and a read-only **Plan** inspection view. One existing Pi
AgentSession still owns each conversation. There is no scheduler, automatic
continuation, child agent, extra loop or separate authoritative planning store.
General goals, background jobs and delegation remain accepted migration work.

The plan is reported progress. **completed** means the agent marked a step
complete; it does not verify external effects or completion of the user's task.
Plans grant no tool permissions. Stop cancels the current turn through its
existing owner and leaves the last reported plan states intact. An in-progress
step is not automatically changed to cancelled, completed or unknown by Stop.
Its actual outcome must be inspected separately.

## Tools and ownership

Read the current revision with **plan_read** before **plan_update**. Updates
replace the full title and ordered step array at exactly that revision. Preserve
steps still needed by the task. Each step has a unique stable ID, text, explicit
**pending**, **in_progress**, **completed**, **blocked** or **cancelled** status,
and an optional note. Empty title and steps explicitly clear the plan and retain
a new revision; clearing does not revert to the initial **empty** revision.
Revision tokens are fresh UUIDs, avoiding equal revision numbers across branches.
There is no non-idempotent toggle operation or inference from answer text.

Limits are 64 steps, 64-character alphanumeric/underscore/hyphen IDs, 1,024
JavaScript string units per step text, 512 per note, 256 per title, and 128 KiB
of serialized UTF-8 title/step content. Duplicate IDs, unsupported states,
unexpected fields and stale revisions are refused before a native append.
The existing SDK result/error and execution guards remain conservative; an
error after tool dispatch retains action uncertainty even when the plan reports
refusal before append. Read the stored revision rather than automatically
replaying an update. Plan reads are classified as reads and updates as changes.

Native and browser-only sessions use their own scoped native state. Browser
planning tools grant no OS/MCP tools. Read-only policy permits reading and
refuses updating; the existing approval path governs updates in other restricted
presets. A disconnected interface cannot silently approve an update. No direct
operator write RPC is added. Native/Browser controls and layout are unchanged;
their existing conversation inspection opens the Harness view.

## Persistence and inspection

Updates append **augmentor/plan-v1** full snapshots with the public Pi extension
**appendEntry** API. Every operation reconstructs the latest snapshot from the
public read-only **getBranch** projection. Reloads do not depend on an extension
closure cache. Native ancestry owns inheritance: a completed-reply child sees
the plan at that reply, excludes a later abandoned future, and can diverge
without changing any source-parent bytes. The record retains its originating
native session and tool-call ID; a child's current native ID is separate.

An accepted native append is not a claim that bytes reached disk. The SDK can
defer persistence in a blank session. Loaded reads explicitly say
**native-session-memory; saved record confirmation is separate**; update results
say **accepted-by-native-session; disk confirmation requires saved inspection**.
After an owner restart, **session.plan** reads the saved native source through
the verified index and reports **saved-native-entry**. It does not open/migrate
an SDK SessionManager, load approved resources, connect MCP, perform inference,
change model selection, replay a tool or write the original history. Derived
private index files may be built.

Cold projection follows only the selected saved ancestry. It scans at most
4,096 indexed ancestry records, decodes at most 4 MiB of custom-entry source bytes, and
admits a custom record up to 256 KiB. Reaching a limit reports unavailable
coverage, preserving originals. Initial index construction reads the native
source under the existing indexed-history limits; verification reads enclosing
source blocks. The projection limits do not bound that first index build.
Unavailable coverage does not claim no plan. An invalid newest
matching record is reported unavailable instead of falling back to an older
valid snapshot. General original-history inspection remains available for the
preserved evidence; automatic corruption repair is not implemented.

The Plan view renders title, steps and notes as text, and displays the revision,
native entry, origin and persistence boundary. Late results are bound to the
conversation/selection epoch. A scoped read-only inspector can read only its
selected conversation. Rendering and reload require no inference. Diagnostic
capture is not the plan's authoritative store; clearing diagnostics must not
erase the native plan.

## Source selection and qualification

Pi 1.1.0's official
[todo](https://github.com/earendil-works/pi/blob/abe508e1b89912adde45528136c3221eb69acdd7/packages/coding-agent/examples/extensions/todo.ts)
and
[plan-mode](https://github.com/earendil-works/pi/tree/abe508e1b89912adde45528136c3221eb69acdd7/packages/coding-agent/examples/extensions/plan-mode)
examples were inspected locally. They establish branch-state persistence through
public extension APIs. The terminal widgets, tool activation changes and
answer-text completion markers are not transplanted into Augmentor. This
product implementation is independently authored; no supplier/private source,
private SDK import/patch, dependency, native component or supplier notice is
added or changed. Existing selected MIT notices remain intact.

Reproducible source checks after **npm run build**:

```sh
node --test tests/pi-plans.test.mjs tests/plans-history.test.mjs tests/harness-plans-chromium.test.mjs tests/harness-context-chromium.test.mjs
```

The independently authored synthetic provider/private-owner cases exercise
actual SDK tool execution, revision refusal, branch inheritance/divergence,
clearing, Stop, cold restart, read-only Native/Browser policy and unchanged parent
originals. Public SDK-authored saved fixtures verify native ancestry, invalid
latest records and scan/byte limits. Real Chromium qualifies text rendering,
stale selection results, reload, narrow viewport and scoped inspection without
new model requests. A held startup subscription demonstrates that the
**Read-only** label can precede completed selection; it is not a readiness check.

Common Node/public SDK and web behavior serves Linux/macOS without a new OS
adapter or Python product change. These fixtures are separate from live model,
physical OS, installed/update and packaging acceptance. Full P0/P1 requirements
in the [migration specification](AUGMENTOR-HARNESS-MIGRATION.md) remain binding.
Preserve DSH and selected installations until those workflows qualify.
