---
name: google-docs-browser
description: Edit or verify the user-selected Google Doc with the connected signed-in browser and saved export readback.
---
<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

Use the connected browser tools. Preserve the existing model and requested document.
List tabs, then inspect `browser_capabilities`. With several connected profiles,
select the matching executorId and tabId from its returned tabs. Never substitute
an isolated research browser for the signed-in work browser.

A Google Docs toolbar snapshot is not document body text. Read the actual saved
document using `browser_document_read` with txt before editing. For formatting,
request html readback too; it supports a bounded HTML entry in Google's ZIP export.
If an export returns a sign-in/error, size or permission failure, report it precisely.
Do useful independent work; do not claim a saved edit from input acknowledgment.

When trusted input is available, use `browser_observe` on the exact tab. Its
editor selectors and focus identity are actual observations. A canvas centre click
only focuses a location. Observe again and deliberately position the caret or
selection for the user's requested operation. Use Control on Linux/Windows,
Meta on macOS. Never select the entire page until the editor's focus is confirmed.
Enter and text insertion use trusted input; ordinary DOM typing is for forms.
Every trusted input consumes its observation token. Observe before the next
operation and read the saved export afterward. Autosave may lag: repeat the read,
not the edit. Compare content, actual link destinations and HTML styles separately.
Page large exports with nextOffset and the returned contentSha256 as expectedSha256. If the export changed, read again before verification. Do not infer inline-image verification from plain text.

The driver reports live Google Docs qualification separately from input availability.
A canvas fixture pass is not a completed edit of this document. Use an explicitly
labelled new test document for installation qualification; never use unrelated
owner documents as scratch space. Use browser_stop when finished or interrupted.
If the installed extension needs its one-time re-enable/reload, say that directly;
do not cycle through raw shell input or guessed screen coordinates.
