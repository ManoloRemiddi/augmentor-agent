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

Actual private pilot results are recorded separately after qualification. Source
and installed/running application identities must be reported separately: the
importer is an offline operator tool, not a patch to the immutable application.
