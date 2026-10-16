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
   output. The current exporter deliberately accepts one project conversation.
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

This importer intentionally refuses multi-conversation projects, unresolved tool
calls, sequence gaps, edited/compacted/branched record forms, attachments or opaque
reasoning parts in parent messages. Their originals remain backed up. Historical
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
