<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Linux reply completion

The reported DSH answer was present both in saved history and in the Linux
QTextDocument, but Qt assigned its final text block zero lines and zero height.
Formatting the user-message tables after `setHtml` left later blocks with stale
layout in a long, narrow transcript. Incremental streaming displayed the reply;
the full rebuild at completion hid it. Reopening the same history reproduced the
failure. Fresh short chats and assertions against `toPlainText()` missed it.

The transcript now invalidates and recalculates the document layout after
formatting its bubbles. The exact affected history page, replayed at the user's
window size and display scale, has visible final text and a reachable copy icon.
A synthetic multi-paragraph regression reproduces visible streaming followed by
zero-height final text before the fix, and also covers reopening the history.

Two additional reproducible gaps in completion handling were also fixed:

- An empty final live message clears the streamed text, with no saved-history
  check at turn completion to recover it. A missing final frame leaves an
  uncommitted partial reply.
- A history page deferred while the scrollbar is held can overwrite messages
  received after that page snapshot, including a completed answer.

The shared Linux controller now reads saved history at the end of a connected
turn and reconciles overlapping events, retaining older pages and newer live
events. It never resends a prompt. A read is ignored if its session, connection
generation or controller changes before it returns. Deferred page rendering
uses the current controller cache and rejects callbacks for a different chat.
Both Linux harness adapters use this controller.

## Evidence

`tests/test_reply_completion.py` exercises the real Qt transcript with empty and
missing final frames, normal completion without duplicates, delayed pagination,
chat changes before and during the history read, and a newer stream arriving
during reconciliation. The original four regression tests failed before the
fix. All seven completion tests pass after the fix; the full native suite passes 91 tests.

`scripts/dsh-reply-proof.py` creates a separate DSH session with a configured
local model. It exercises both healthy streaming and deliberate removal of the
final live content, while preserving the real saved answer. In both runs it
checks the rendered answer, clicks Copy through Qt mouse events, verifies the
clipboard and unchanged scroll position after tick expiry, and checks that the
prompt was not replayed. This proof passed against the running DSH host.

Local proof artifacts are in `outputs/dsh-reply-completion-proof.json` and
`outputs/dsh-reply-completion.png`. Captures of the user's original conversation
remain private in ignored outputs and are not regression fixtures.

## Deployment

Version 0.2.5 is installed, including the prepared Settings update and the final
transcript layout correction. The installed controller, window and transcript
were compared byte for byte with the tested source. Both Debian packages, the
browser extension and the DSH browser integration report 0.2.5. User data was
preserved through the maintenance backup and coordinated reload.

The original affected conversation was reopened in the installed Linux app.
Its final answer is visible. A desktop mouse click on its Copy button copied the
exact saved 3,435-character reply; the transcript stayed in place during copying
and after the confirmation tick expired. The previous clipboard was restored.
The seven completion regressions also passed against the installed code.

Private local evidence: `outputs/recovered-original-proof.json`,
`outputs/recovered-original-installed.png`,
`outputs/recovered-original-copy-tick.png`, and
`outputs/installed-reply-regressions.log`. The runtime package SHA-256 is recorded
in `outputs/debian-0.2.5/artifacts.json`. The browser's unsent URL draft is backed
up in `outputs/reply-install-backup/browser-draft.txt`; the final extension reload
cleared it, and it was left backed up when the user resumed keyboard activity.
