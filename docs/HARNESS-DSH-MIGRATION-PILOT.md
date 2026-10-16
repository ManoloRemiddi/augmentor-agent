<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# DSH project migration pilot — MX Linux

The operator-approved pilot copies one inactive DSH project conversation into a
separate private Harness profile. Working files stay in their existing folder.
The original DSH store, current Harness profile, selected installation and running
review remain available. Bulk migration is not enabled by this pilot.

## Retained data and continuation

The cold export captures the complete parent event sequence at a verified cursor,
workspace membership, archive/pin membership and historical subagent families
through their durable parent addresses. Each captured cursor and workspace record
is checked again before the export is published. Running source conversations,
changed cuts, non-advancing pagination and oversized families are refused.

The offline importer uses the pinned Pi **1.1.0** public `SessionManager` API. It
creates native conversation data and derived Harness metadata/display files in a
new state directory. It does not start an agent, contact a provider, execute a tool
or import a historical queue, goal, permission grant or agent job. The explicit
continuation model comes from the already configured Harness profile. Imported
conversations initially use **Read Only**.

The exact export is retained privately, addressed by SHA-256. Every derived display
event records its DSH session, original sequence/time and archive hash; zero-based
DSH sequences become one-based Harness display sequences. Historical tool proposals
and completed results are paired for the existing Chat/Trajectory presentation.
No DSH system prompt or historical agent-instruction/bootstrap message becomes the
new Pi system prompt. Those originals remain in the archive.

Pi continuation receives the original human messages and labelled historical
assistant/runtime text. Old tool proposals are not native executable proposals.
Tool-result text uses at most **16,384 original characters total**, preferentially
from recent results, at most 256 per result. Cut markers and coverage labels make
these excerpts explicit. Full arguments, results and historical subagent logs stay
in the archive; parent results also stay complete in the display timeline. The
native boundary provides the exact archive path for subsequent historical lookup.
This is a continuation transcript, not a reconstruction of DSH's effective context.

Historical display entries use the existing `unattributed` input mode so the
automatic-memory adapter does not recapture old statements as new live memory.
New admitted messages retain ordinary memory behavior. Historical usage/cost,
request-source snapshots and live Fleet-job ownership are not manufactured.

## Private operator procedure

1. Back up the complete DSH directory, the current Harness profile and the project
   directory, including Git/untracked work, credentials, attachments and links.
   Store this outside Git with a private directory and access-restricted files.
   Verify archive content hashes and restore the project/profile into a separate
   verification directory. A live whole-store backup is not an atomic global
   checkpoint; verify the selected conversation and working folder are inactive.
2. With the matching Python runtime and DSH adapter dependencies available:

   ```sh
   python scripts/export-dsh-project.py --project /absolute/project --output /private/pilot.json
   ```

   Use the reported SHA-256 for the import. Exports never overwrite an existing
   output. The exporter accepts one project with zero to 128 parent conversations;
   rich image exports also read its explicitly selected `--dsh-home` attachment store.
3. Prepare a new private profile parent and copy the already qualified Harness
   configuration privately. Keep its `state` destination absent. Build the importer
   with the repository's pinned TypeScript toolchain, then:

   ```sh
   node scripts/import-dsh-project.mjs /private/pilot.json /private/profile/state SHA256 PROVIDER MODEL
   ```

   Existing target state, including dangling links, is refused. Import staging is
   private and removed on failure; publication is a same-parent rename. No live
   profile merge or original-store rewrite is performed.
4. Start the qualified immutable MX application against this separate profile and
   socket, using the existing deployment lifecycle. Confirm the expected project,
   original chat, completed tools, unchanged source checksums and no initial model
   requests. Use a separate qualification profile for live verification messages.
5. Test a new explicit continuation, actual project reads, cold restart, recall of
   the new validation marker and Stop. Keep the owner-facing imported conversation
   free of qualification messages. Supply its complete private authenticated link
   in chat; never put that token in public documentation.

## Pilot limits

The initial single-conversation pilot refused multi-conversation projects. The
[current project importer](#multi-conversation-projects--october-16) adds that
cardinality support. The [source-history converter](#source-replacements-compaction-and-inherited-history--october-16) now handles current-format replacements, completed compaction and inherited cuts. Unresolved tool calls, sequence gaps, other historical formats, non-image attachments and opaque reasoning parts still require conversion. [Plaintext reasoning and stored images](#reasoning-and-stored-images--october-16) now have an explicit converter. Their originals remain backed up. Historical
subagent logs are archived, not recreated as live Pi Fleet jobs. Branching at an
old imported answer, historical request-context reconstruction and original usage
accounting are not qualified. Existing memory banks, Wiki data, credentials,
resources/skills and MCP connections need their own migration/acceptance paths.

The selected parent's messages contain text and completed tools; there are no
parent attachments to qualify. Whole-store backup includes the original attachment
store, but this does not establish attachment-import support. Other projects must
pass format/inventory checks before any wider transfer. Voice, other platforms and
public binary distribution remain outside this MX pilot.

## Verification evidence

The authored synthetic importer tests cover cold context persistence, complete
source/display retention, paired completed tools, no executable historical calls,
no old instruction activation or memory recapture, bounded tool excerpts, stale
source hashes, occupied/dangling destinations, gaps, incomplete calls/turns,
unsupported attachments/compaction and workspace membership. Exporter tests use
an authored read-only remote fixture and exercise family capture, running-source
refusal and changing-source detection. Private owner exports are never test
fixtures or CI inputs.

Actual private pilot results are recorded below. Source and installed/running
application identities remain separate: the importer is an offline operator tool,
not a patch to the immutable application.

## Large-history Trajectory compatibility

The actual pilot exposed `rowVirtualizer.scrollToEnd is not a function` when the
original table enabled virtualization above 100 records. The selected upstream
component expected newer virtualizer methods/options than the pinned TanStack
**3.13.12** supplies. A marked MIT adaptation uses supported `scrollToIndex` for
initial tail positioning and append-follow, and removes unsupported newer-version
options. The original table/inspector layout and CSS are preserved. A separately
owned synthetic import with 140 completed tools reproduces the old frozen
artifact's exact error. It qualifies the corrected virtual table, new explicit
continuation, record inspection and return to Chat without historical tool replay.

## Qualified private pilot — October 16, 2026

Importer **787c301a** and Trajectory correction/application **48dfd15a** are tested
with Pi 1.1.0/product 0.2.13. Private unselected release
**20261016-114926-035cf359** verifies **24,555 sealed / 1,072 compiled** entries;
its seal is `5f201670a2d7bf07f0e8407103497cd7f6434af71e992dfdaff58880108a6eca`.
Source and exact staged runtime pass **29/29 across seven focused files**, two
workers, unchanged bounds and no skips/failures/cancellations. Four exporter, seven
licence, two private-source and seven notice-assembly cases pass.

The private whole-store backup verifies 96,988 regular files and preserves 63,556
hard-link paths. Its project/profile restore verifies 138 files. Postflight checks
109 original project files and seven original parent/child-session files against
the backup without changes. One parent conversation retains all 631 source events
and 126 historical completed calls; both historical children remain archived. The
continuation has 137 native context messages with bounded tool excerpts. No parent
attachments are present, so attachment conversion is not qualified.

Actual staged local Qwen recalls the saved historical decision, distinguishes
current project files from historical versions and reads the current files. A
fresh validation marker survives graceful restart without replay. Stop settles an
explicit test generation. A separate scratch write/read matches the exact new
contents; the file and conversation persist across another cold restart, and the
qualification permission returns to Read Only. This is real owner-data inference
conducted privately; no owner export is a public fixture or CI input. Memory
processing/capture availability warnings occurred during qualification; this pilot
does not qualify memory service health or migrate existing memory banks.

The clean owner profile contains the import and its ordinary bootstrap metadata,
with no qualification messages or copied qualification memory journal. Original
Chat and virtualized Trajectory open with 50 rendered rows and zero initial
console warnings/errors. Its empty post-restart paused queue is inspected and
resumed with zero messages/actions. Owner QA submits no prompts/audio. Earlier
review, selected installation, DSH originals, model/GPU configuration and original
Node/dependency/component bytes remain preserved. No public binary, installed
activation, merge or DSH retirement follows.

[Portable evidence](../release/harness-dsh-migration-review-20261016.json) contains
counts and build identities only. Private operator receipts retain the complete
backup path, exact source hash, profile/socket, authenticated link and local
qualification outputs. Those credentials and histories are not published.


## Wider project inventory — October 16

A subsequent read-only API inventory finds **30 projects / 107 project
conversations**: nine single-conversation projects, twenty multi-conversation
projects and one empty project. The source catalogue lists 1,226 conversations;
the other 1,119 are outside these current project memberships and are not inspected
by this project pass. This does not classify them as deleted or safe to discard.
There are no source conversations reported running at the initial catalogue read;
that is not a guarantee of a frozen history cut.

The bounded scan reads **95 stable complete parent cuts**. Nine parent cursors
change during the scan, and three histories exceed the existing 30,000-record /
32 MiB pilot bound; those twelve are **not qualified as complete exports**. The
workspace membership is stable. Across full and partial parent reads, it observes
126,633 records, 248 image parts, 14,348 reasoning parts and 32 historical child
references. Child bodies and the conversations outside current projects are not
scanned. These are observed counts, not exhaustive attachment/child totals.

The overlapping parent flags are: 76 attachment/opaque-content histories,
39 edited/compacted/branched histories and 20 unfinished/no-turn histories,
in addition to the nine changing cuts and three bounded partial reads. These
flags are a format inventory, not the importer's complete validation: exact
tool pairing, malformed messages, source-folder availability and conversion
semantics still require their own checks. Only the **existing representative
pilot** is a single-conversation project with a stable cut and no observed format
flags. The previous pilot qualification remains separate evidence.

This confirms the next migration work: multi-conversation workspace membership
and atomic import first; explicit image/reasoning and edit/compaction/branch
conversion with preserved originals; stable cold exports for changing/oversized
histories; historical child-family archival/links; then a separately scoped pass
for conversations outside current projects. Preserve the backed-up original
stores and never treat a partially scanned history as transferable. No extra
project is transferred and no model work is submitted by this inventory. Owner
acceptance of continuing real work in the pilot is still needed before wider
transfer. [Aggregate inventory](../release/harness-dsh-inventory-review-20261016.json)
contains no project names, paths, source IDs or conversation content; detailed
source metadata and digests remain private.

## Multi-conversation projects — October 16

The offline exporter/importer now handles **one project with zero to 128 distinct
parent conversations**. An empty project registers its existing folder without
inventing a conversation. Each parent gets a separate native Pi history, title,
continuation model selection, display journal and source-sequence provenance.
Old tool-call IDs may repeat between chats without sharing execution state.
Workspace membership, exact relative pin order and archived membership survive;
archived chats are excluded from ordinary pinned/visible lists. No original
project file is copied over or changed by importing its folder registration.

All parents and organization/model mappings validate before a destination is
staged. The project is published through one directory rename only after every
native writer and cold-context check succeeds. Failure leaves no published
partial conversations. The destination must be a new private state directory;
this does **not merge into a running or existing profile**. Existing single-parent
callers retain the pilot receipt fields (with an added explicit selection).
Multi-parent/empty receipts use `augmentor-dsh-project-import/2` with a `sessions`
array mapping every source ID to its native ID and selected continuation model.
The original `augmentor-dsh-project-export/1` bundle already contains a sessions
array and stays compatible; its raw bytes are archived once for the whole project.

The exporter rechecks every parent/family cursor, workspace membership and final
parent running/catalogue state. Repeated child references must have the same
parent/mode; a child cannot alias a root or silently move between parents.
There are at most 32 archived related conversations per bundle. The existing
30,000-record per-history and 32 MiB whole-export bounds remain. A cumulative
byte check now limits collection before all parent/family records accumulate;
formatted output is checked again. No bound, provider/inference budget or native
tool-excerpt limit is increased. Old child histories remain archived rather than
being started as jobs. Current request context, permissions, queues and automatic
memory do not reactivate historical actions.

Continuation uses an explicit currently configured default model. An optional
private source-ID mapping selects different current models for individual chats;
it accepts only provider/model IDs, not credentials or provider configuration.
Unknown source IDs, blank models, duplicate/foreign membership and malformed
organization fail before staging. Legacy source model metadata stays in the raw
archive rather than automatically choosing a future provider.

```sh
python3 scripts/export-dsh-project.py --project EXACT_WORKSPACE_ID \
  --output /absolute/private/project-export.json
node scripts/import-dsh-project.mjs /absolute/private/project-export.json \
  /absolute/private/new-state EXACT_EXPORT_SHA256 CURRENT_PROVIDER CURRENT_MODEL \
  --session-selections /absolute/private/model-choices.json
```

The optional JSON maps source conversation IDs to objects such as
`{"provider":"current-provider","model":"current-model"}`. Its regular-file bound
is 1 MiB. Without the option all chats receive the explicit default; their later
model-picker choices remain independent. The import command does not open a
runtime or submit model requests. It does not create the surrounding provider/
companion configuration or activate an installed application.

Source qualification passes **50/50 Node cases across nine files**, including
four actual Chromium files, plus **29 Python cases** (13 exporter and 16 licence/
private-source/notice checks). The exporter tests also pass all 13 cases with
Python site packages disabled, as shared helper imports need only the standard
library. The common import/runtime/export contracts are registered in the existing
three-OS SDK workflow; hosted results and other-OS artifacts are separate gates.
The implementation uses the existing shared Node/Python/SDK paths, with no new
OS helper, dependency or supplier source. MX is the qualified local platform.

The controlled earlier sealed build rejects the new three-chat test at its
single-parent restriction. Current actual Host tests check per-chat routing,
zero historical replay/capture, one explicit new turn and cold restart. Original
GUI tests switch Alpha/Beta in the unchanged workspace sidebar, keep archived
Gamma hidden and continue Beta through the actual composer with exactly two
synthetic provider calls. Its request contains Beta history without Alpha/Gamma;
Alpha's imported prefix stays exact. First opening may append normal current SDK
model/thinking settings, and a later Beta turn leaves the initialized Alpha file
unchanged. The existing 140-tool Trajectory regression remains. No real owner
conversation or model is used by these synthetic checks.

The running owner's representative pilot remains on its existing build/profile;
no extra project is transferred by this implementation. Image/reasoning and
edit/compaction/branch conversion, changing/oversized cuts, child navigation,
multi-project consolidation into one profile, existing companion data and wider
owner acceptance remain required for full migration. New source/staged evidence
must not be read as completed bulk migration. Private unselected artifact **20261016-170525-c772392c**, application
**4a7ef0a8**, passes the same **50/50** Node cases against its exact
target, plus all **13** exporter cases without Python site packages. All
**24,566 sealed / 1,072 compiled** entries verify after
qualification; production Node/dependencies/components match the prior baseline.
Both owner reviews keep their same PIDs and roots; **32 protected files** and the
installed selection remain exact. No extra owner project, conversation, provider
request, voice request or running-review update is performed by this qualification.
[Portable evidence](../release/harness-dsh-multichat-review-20261016.json).


## Reasoning and stored images — October 16

The offline importer now accepts plaintext assistant `reasoning` blocks and
content-addressed PNG/JPEG/WebP/GIF image references in completed parent histories.
The formats were checked against the already selected public MIT DSH baseline
[`d7432673` message schema](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/llm/llm/src/message.ts).
The existing MIT attachment store/decoder and original GUI gallery/reasoning
components are reused. The Harness projection now retains assistant image blocks,
including image-only answers, in the supplier gallery and Trajectory; no new dependency or supplier-source edit is introduced.

Exports optionally contain a deduplicated `attachments` list of
`{attachmentId,bytes,data}` with canonical base64. Only image hashes actually named
by captured parent/archived-child messages are read from the explicitly selected
DSH home. Descriptor-relative reads refuse linked directories/objects, mismatched
sizes and changed digests. Image collection is inside the existing whole-export
32 MiB budget and precedes the final cursor/catalogue checks. This store-export
path is qualified on MX Linux; other OS deployment remains deferred.

Import verifies every declared hash/encoding/reference and fully decodes parent
images against the existing pixel/dimension limits. Exact stored bytes are
published through the existing immutable store, without recompression, and only
the parent that referenced an image receives its receipt. Child-only objects stay
in the raw archive. Missing/corrupt/unsupported media refuses the whole project;
failed asynchronous admission removes the entire staged state. The public
`importDshProject` helper is now asynchronous: callers must `await` it. CLI arguments
and the existing single-/multi-conversation receipt shapes stay compatible.

Plaintext reasoning appears in the original Think disclosure and is labelled
historical data in continuation. Opaque reasoning/provider signatures and model
replay state are never supplied as live provider thinking; their exact source
stays archived. Reasoning-only assistant records are retained. Historical tool
text remains bounded and old calls never become executable proposals.

Native history retains compact supported Pi custom messages with checked durable
image references. A lifecycle-owned public Agent `transformContext` hook resolves
only the active messages against the current conversation's attachment authority
at request time, after SDK context transforms and before request observation.
It is composed/unwound with the existing execution/reasoning/Stop/reload hooks;
there is still one SDK AgentSession. A missing receipt, changed object or text-only
current model stops before provider dispatch. Repeated images cannot inflate the
saved native JSONL; an active request exceeding 20 MiB or 64 imported inline images
is explicitly refused, without silently dropping data.

DSH `image/offload` targets are checked in sequence against earlier user/tool
messages. Strict increasing indexes and unique targets prevent ambiguous removal.
Derived history keeps the selected images offloaded and provides their authorized
read-only stored path instead of putting them inline again. The exact raw export
remains unchanged. The gallery loads the source's stored image; pre-normalization
camera uploads are not invented, and imported-image composer Edit recovery is not
qualified by this increment. Old edited/compacted/branched source histories,
generic files, historical child navigation and full effective-context recreation
remain separate work.

Source build and **126/126 Node cases** across twenty files, including six
actual Chromium files, pass with two workers and unchanged deadlines. The source
also passes **35 Python cases**: nineteen exporter and sixteen licence/private-source/
notice cases. Actual Host/provider requests contain the exact image bytes after
cold reopen, preserve historical reasoning, omit opaque replay data and execute
only the new fixture tool. Original GUI image lightbox, reasoning disclosure and
composer continuation pass with no page/HTTP errors; foreign conversation access
is refused. Initial GUI-driver observations (click before thumbnail loaded; React
boolean attribute serialized as `true`) are retained in private logs; the final
driver waits for decoded pixels and asserts the observed disclosure state. A later
image-only regression driver exposed a quoted-selector syntax error; it now builds
the selector as JSON data, retaining the actual gallery-count assertion.
These are independently authored synthetic histories, with no owner-data model
requests. Private unselected candidate **20261016-174458-49f743c2**, application
**6579f09c**, passes the same **126/126** Node cases against its exact
packaged modules and all **19** exporter cases without Python site packages.
All **24,570 sealed / 1,075 compiled** inputs verify after testing.
The test-only source vendor assertion path maps to the byte-identical actual
packaged vendor directory; its initial source-layout failure remains recorded.
Production Node/dependencies/components and supplier sources/licences stay exact.
Both owner PIDs/roots, **32 protected files** and installed selection stay unchanged.
No extra owner import, provider request or review restart occurs.
[Portable qualification](../release/harness-dsh-rich-history-review-20261016.json).


## Source replacements, compaction and inherited history — October 16

The previous importer appended every recognized message into continuation context.
That is wrong for a DSH `surfaceOp: {op: "replace", startSeq, endSeq}`: the original
message stays in the human transcript, while the replacement occupies its old
position in model input. A controlled preceding sealed build reproduces a real
provider request containing both an overwritten human prompt and its replacement.
The corrected importer supplies only the replacement at the original position.

This independently authored adapter follows the public pinned DSH
[`surface.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/session/src/surface.ts),
[compaction/checkpoint contracts](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/compaction/compaction/src/types.ts)
and [fork seed](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/session/src/fork.ts).
Public source reads are pinned and Git-blob verified. No private repository code,
owner logs or owner project contents become public fixtures. No new dependency or
supplier-source edit is introduced. MX is the deployment qualification target;
common pure/SDK cases enter the existing three-OS workflow without claiming other
OS artifact acceptance.

The converter folds the ordered message surface from the complete bounded source
prefix before staging any conversation. Version-four messages require explicit
surface operations; earlier synthetic fixtures without a version retain the
legacy append convention. Replacement boundaries must still be current, citations
must include all shadowed nodes, and a tool-result rewrite may change only its
single original result's content. The source system head remains protected.
Ranges follow *surface positions*: a high-sequence summary can stand before a
lower-sequence later conversation, so numeric `startSeq > endSeq` can be valid.
Unknown required event types, unrecognized versions, malformed lineage, missing
citations and unsupported opaque formats are refused. Explicitly ignorable
unknown records remain archived without affecting context.

Completed `compaction/start` / `summary` / checkpoint / `end` sequences retain their
source lifecycle/command identity, exact plaintext checkpoint, source range and
shadow price. Summary/checkpoint and prune/replacement adjacency must match. A
source `session/end-seed` boundary ends inherited incomplete compaction brackets;
an incomplete bracket at the live source tail is still refused. Source parent ID,
inherited cut markers, replacement ledger and effective source sequences are
retained in a non-context native `augmentor.dsh-surface.v1` audit entry and import
receipts. They do not manufacture Pi parent sessions, running Fleet jobs, old
permissions or a new compaction request. Unknown-outcome calls remain refused.

Native continuation uses the final source message order with current Augmentor
instructions, historical-data labels, existing bounded tool excerpts and lazy
image admission. Compact checkpoints are labelled historical user-role data, not
new human requests. Tool excerpt counters now explicitly cover **effective source
tool results only**; shadowed originals stay in the raw archive. Images shadowed
by a summary stay available in their original gallery but never re-enter a new
provider request merely because migration retained the original bytes.

The Chat transcript retains append-origin human/assistant/tool rows. Replacement
copies remain source history instead of duplicate human messages or tool endings.
Compaction checkpoints use DSH's existing **CompactionNodeView** and expandable
summary, preserving the original layout. Every display event retains one-based to
zero-based provenance, source surface operation and citations. The exact archive
remains unchanged; no historical records are recaptured as new automatic memory.
The source's `forked` closure is labelled as an ended historical cut, not a newly
completed action. Native branch-family restoration and historical request-context
reconstruction remain distinct unfinished work.

Source build and **150/150 Node cases** across twenty-three files/seven actual
Chromium files pass with two workers and unchanged deadlines. **35 Python cases**
pass, including the nineteen exporter cases and sixteen licence/private-source/
notice checks. Authored fixtures cover nested summaries with decreasing numeric
range endpoints, tool pruning, ordinary message edits, source cuts, malformed
range/lifecycle/citation/version/identity refusal and whole-project atomicity.
Actual Host/provider/cold-reopen tests prove that superseded text/media stay out
of input while history/gallery bytes remain inspectable. The original GUI opens
both nested summaries and continues through its existing composer with no page
or HTTP errors. The previous sealed build fails the ordinary replacement assertion
at the observed stale provider input. An initial test wrongly expected a bracket
ended by a source seed cut to remain pending; it now independently covers both a
completed inherited lifecycle and a genuinely unresolved tail.

A read-only inspection of the already backed-up owner pilot confirms source
header version four and 248 append surface markers; no extra owner project is
exported or imported and no owner inference is submitted. Wider real-source
acceptance is not inferred from synthetic evidence.

Private unselected MX **20261016-180145-0db955b0**, application **c3d45c47**,
passes the same **150/150 Node cases** against actual packaged modules and all
**19 clean-Python exporter cases**. All **24,574 sealed / 1,078 compiled**
inputs verify after qualification. Production Node/dependencies/components and
supplier sources/licences stay exact. Both owner PIDs/roots, **32 protected files**
and installed selection stay unchanged; no additional owner import, provider
request or review restart occurs. [Portable qualification](../release/harness-dsh-source-surface-review-20261016.json).


## Multi-project consolidation into a cold profile — October 16

The batch importer adds multiple DSH projects to **one new or cold existing Harness
state at its original path**. Existing native conversations, their JSONL bytes,
metadata, queues, drafts, uploads, observation data and archive files are copied
unchanged, except the two shared workspace/organization catalogues. Configuration,
credentials, prompt libraries and companion-service roots outside `state` stay at
their original locations. This is state adoption; the existing full-backup and
owner-pilot acceptance procedure still precedes wider owner transfer.

`prepareDshProject` retains the validated single-project conversion contract; its
private materializer writes new parents into a shared stage with final paths to
the original state location. Up to 128 project exports / 256 MiB of source bytes
are admitted, retaining the 32 MiB/project, 128-parent/project and 30,000-event/history
limits. The resulting catalogue is bounded at 5,000 conversations/1,000 workspaces.
A complete state snapshot is bounded at four GiB/100,000 filesystem entries.
Export metadata is charged before loading every project into memory.

Existing workspace titles/order, pin/archive preferences and explicit model routes
win for retained conversations. Newly imported projects follow manifest order,
with their own saved pins/archive state and models. Removed workspaces, duplicate
workspace/source identities and existing native paths into another owner are
refused. A source conversation already imported into this profile is retained
only if its verified original archive, cursor, folder and complete event cut match.
All its newer Harness work stays byte exact. If DSH has diverged, the tool refuses
instead of overwriting Harness or silently hiding newer DSH work.

This increment preserves **one existing native profile** while adding DSH exports.
It does not yet combine two independent existing native profiles: imported paths,
original-upload references and companion ownership need explicit relocation for
that separate operation. Neither current owner review is merged or restarted by
this qualification. Existing conversation bodies are not rewritten to make them
appear portable; backups restore to the original state path and are not active
profiles. Starting a generated backup/staging tree directly is refused.

### Ownership and recoverable publication

POSIX runtime startup now holds a profile lease outside the replaceable state
folder, independently of its chosen socket. Node opens the private regular lock
file and passes that same open file description to a small Python `flock` helper.
The helper exits without unlocking; the actual Node descriptor retains kernel
ownership until close/process death. This avoids depending on a helper PID or a
stale lock-record interpretation. The lease covers SDK shutdown/drain and is taken
before creating profile journals. Both different-socket and simultaneous-owner
regressions use actual processes.

The Linux consolidation command takes that same lease and refuses live legacy
Harness descriptors, active sockets, links/unsupported state objects, malformed
metadata and incomplete earlier migration. Stop the old owner before migration
and keep older runtime versions closed until it finishes; an old executable does
not know the new maintenance protocol. Copied configurations with native paths
into another owner require explicit relocation first.

A private copy is hashed against the cold original, including file/directory
modes; copied modes are restored explicitly because Node `cpSync` did not preserve
private directory modes in the initial experiment. New imports/catalogues validate
inside that copy. After flushing the staged tree and rechecking the original
identity/content, a durable external journal fences startup across the two
same-parent renames. The original whole state becomes a private backup; the built
state takes its original location. A completion record removes the startup fence.
The source, backup and new state never share writable file inodes.

A process failure between renames leaves the journal, backup and built candidate.
Starting Harness refuses the unresolved migration **without creating an empty
state directory**. Explicit recovery hashes all copies before finishing publication
or restoring the original. Recovery never repeats export/conversion, model work,
commands or tools. Changed/ambiguous copies are preserved and refused, never
selected by filename or a presumed operation outcome.

Use the qualified immutable MX application and a private manifest, for example:

```json
{
  "schema": "augmentor-dsh-project-batch-input/1",
  "projects": [{
    "sourceFile": "/private/project-export.json",
    "options": {
      "sourceSha256": "SHA256_FROM_EXPORT",
      "selection": {"provider": "CONFIGURED_PROVIDER", "model": "CONFIGURED_MODEL"}
    }
  }]
}
```

```sh
node scripts/import-dsh-projects.mjs import /private/manifest.json /private/profile/state
node scripts/import-dsh-projects.mjs inspect /private/profile/state
node scripts/import-dsh-projects.mjs finish /private/profile/state
node scripts/import-dsh-projects.mjs rollback /private/profile/state
```

`inspect`, `finish` and `rollback` apply only to a pending journal. Keep the reported
backup/completion receipt and the earlier full DSH/config/project backups. Do not
start a backup at its backup path: restore it using the verified transaction.
The existing single-project command still requires a new absent destination.

### Qualification and remaining scope

Source build and **169/169 Node cases** across twenty-eight files/eight actual
Chromium files pass, with unchanged two workers/deadlines and no skips. **35 Python
cases** pass (nineteen exporter, sixteen licence/private-boundary/notice). A real
Host retains one existing native conversation while adding six chats in two
projects, continues both projects independently, preserves configuration bytes
and old automatic-memory counts, and cold-reopens without replay. Earlier imports
with new native turns remain exact; divergence/foreign native paths fail without
publication. The original sidebar uses its existing workspace expansion controls;
the initial driver incorrectly assumed every group was already expanded.

Actual Node process death after the first rename releases the kernel lease while
leaving the durable startup fence. Explicit rollback restores the exact original
and retains the built candidate. Separate second-rename failure/finish, changed
recovery-copy refusal, whole-state mode/hash backup and live-profile refusal pass.
No owner project, native chat, model/audio request, configuration or running review
is adopted by these independently authored fixtures. Artifact qualification follows.

The state transaction is **MX/Linux qualified**. The POSIX runtime lease is shared
source on Linux/macOS; common owner tests enter SDK CI, but macOS artifact/kernel
qualification remains open. Windows keeps its existing named-pipe owner guard and
honors a pending migration fence; transactional consolidation is explicitly refused
until its ownership/recovery adapter is qualified. User-directed voice and later
OS rollout remain deferred. Multi-profile native relocation, prompt/memory-owner
convergence, stable larger exports, other historical formats/child navigation and
owner acceptance remain required before full migration is claimed.
