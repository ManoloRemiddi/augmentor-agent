<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Improve a draft

In the Linux app with the Augmentor DSH integration selected, type a draft and click **✦ Improve prompt** inside the input. The selected model rewrites it using the separate **Prompt library → Improve prompt** instructions. Letters roll while the request runs, then settle into the replacement in 700 ms. The result remains an editable draft; it is not sent to the conversation. After a rewrite, the same ✦ button becomes ↶ Undo; clicking it restores the previous wording. Editing the draft returns the button to ✦.

Click **×** or press Escape to dismiss the pending improvement. Editing the draft also discards the pending result. Dismissing the preview does not necessarily stop the already-started model request. A failed rewrite or a request for clarification leaves the original intact and displays its explanation on the button. The rewrite uses a separate, tool-free model call and cannot execute the draft's instructions. Other harnesses do not yet expose this button's model operation.

The editor accepts drafts up to 6,000 characters, subject to the local request-size limit. Open **More → Prompt library → Improve prompt** to edit the instructions, preview their formatting, save changes, reload, or restore the default. The setting is shared with the browser library and DSH settings. Existing installations seed it once from `/prompt`; later edits or deletion of that shortcut do not change the setting. Concurrent saves are revision-checked. Only the approved improvement instructions ship as the default; personal saved prompts stay in the local database and are not bundled in source or releases.

Regression checks: `tests/improve-prompt.test.mjs` and `tests/test_prompt_improvement.py`.

## DSH composer

The DSH web UI also exposes ✦ at the top-right of its composer through the public `conversation.input.overlay` slot. It uses DSH’s selected model and the same shared instructions, with rolling letters, Cancel, and an Undo arrow in the same icon position. Refresh the DSH page after updating the plugin. Draft revisions guard late results; attachments remain intact. Improve plain text before adding structured reference chips, which are deliberately not flattened by a rewrite.

Build the client with `node scripts/build-prompt-library-client.mjs`. Composer behavior is tested in `apps/browser/test/dsh-improve-composer.test.mjs`; the model request uses the same tested helper as the Linux app.
