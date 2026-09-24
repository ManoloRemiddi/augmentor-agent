<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Improve a draft

In the Linux app with the Augmentor DSH integration selected, type a draft and click **✦ Improve prompt** inside the input. The selected model rewrites it using the separate **Prompt library → Improve prompt** instructions. Letters roll while the request runs, then settle into the replacement in 700 ms. The result remains an editable draft; it is not sent to the conversation. After a rewrite, the same ✦ button becomes ↶ Undo; clicking it restores the previous wording. Editing the draft returns the button to ✦.

Click **×** or press Escape to dismiss the pending improvement. Editing the draft also discards the pending result. Dismissing the preview does not necessarily stop the already-started model request. A failed rewrite or a request for clarification leaves the original intact and displays its explanation on the button. The rewrite uses a separate, tool-free model call and cannot execute the draft's instructions. Other harnesses do not yet expose this button's model operation.

The editor accepts drafts up to 6,000 characters, subject to the local request-size limit. Open **More → Prompt library → Improve prompt** to edit the instructions, preview their formatting, save changes, reload, or restore the default. The setting is shared with the browser library and DSH settings. Existing installations seed it once from `/prompt`; later edits or deletion of that shortcut do not change the setting. Concurrent saves are revision-checked. Only the approved improvement instructions ship as the default; personal saved prompts stay in the local database and are not bundled in source or releases.

Regression checks: `tests/improve-prompt.test.mjs` and `tests/test_prompt_improvement.py`.

## DSH composer

The DSH web UI also exposes ✦ at the top-right of its composer through the public `conversation.input.overlay` slot. It uses DSH’s selected model and the same shared instructions, with rolling letters, Cancel, and an Undo arrow in the same icon position. Refresh the DSH page after updating the plugin. Draft revisions guard late results; attachments remain intact. Improve plain text before adding structured reference chips, which are deliberately not flattened by a rewrite.

Build the client with `node scripts/build-prompt-library-client.mjs`. Composer behavior is tested in `apps/browser/test/dsh-improve-composer.test.mjs`; the model request uses the same tested helper as the Linux app.


## Browser sidebar

The extension's sidebar uses the same model operation and saved improvement
instructions as Desktop. Its input now also shows a paint-only rolling-letter
preview while waiting, with the same 700 ms settling interval before committing
the rewritten draft. The actual textarea keeps the original text during both
phases. Unicode and punctuation remain readable. The preview follows the input's
size and scroll position, and honors reduced-motion preferences.

Cancel (× or Escape), typing, switching sessions and closing the sidebar remove
the preview and discard late results. Enter and Send cannot submit a draft while
improvement is pending or settling. Failed requests restore the ordinary input;
success offers Undo in the same button position. Rewrites and Undo also update
the saved draft used when reopening the sidebar.

Browser regression coverage in `apps/browser/test/surface.test.mjs` includes
pending/settling draft protection, completion and Undo, Escape/Enter, failure,
typing, session changes and page closure. These DOM tests establish behavior;
they do not substitute for a visual acceptance check in the user's Chromium.
