<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Selected public DSH GUI

Source: [DeepSeek Harness d743267](https://github.com/deepseek-ai/deepseek-harness/tree/d743267388641bc76f17c45ce8b4c231aed1d32c), public 0.2.1-alpha.2 baseline. The root MIT notice remains in LICENSE. CosmoKit/Schemastery carry their upstream notices where selected. SOURCE.json records every selected source hash, original public path and any adaptation. These supplier files retain their own licensing; Augmentor's resale restriction does not relabel them.

The actual AppFrame, sidebar, conversation shell, composer, model chooser, chat, Trajectory, workspace picker, approval/question flows, goal bar, controls and CSS are copied from public upstream. We select presentation dependencies and local type contracts, not the DSH owner, API bridge, account/analytics plugins or backend. InputBar has one nonvisual import substitution to avoid loading Cordis's image service. The small image media predicate is selected verbatim from the public upstream service source. The folder browser's English dictionary in the adapter is derived from ui-directory-picker-browse/src/client/index.ts at this same public ref.

The October 11 session-control selection adds five verbatim public files from ui-workspace/session-actions: PinSession, RenameSession, ForkSession, ArchiveSession and RowActionToast. Together with the previously selected original rename/archive dialogs, pin-order helpers and view filters, they retain the supplier menus, hover controls, confirmation and notices. The session-control selection has 345 hashed files; all preceding 340 records and supplier bytes remain unchanged.

The separately authored dsh-app.jsx/controller/projection/payload files translate Pi Host data into public component props. Pi's existing AgentSession is the only execution owner. This source selection is not a complete DSH backend or a claim of complete feature parity. See docs/DSH-GUI-ON-PI.md.

The attachment follow-up adds thirteen verbatim ui-attachment files (cards, rail, drop overlay, historical images, labels and CSS), bringing the GUI selection to 358. The preceding 345 records/bytes remain unchanged. A separate twelve-file pure public storage/codec selection lives in packages/runtime/vendor/dsh-attachment, retaining MIT licensing and original/adapted hashes. Its only changes are local import paths and NodeNext suffixes; no supplier service owner is copied.
