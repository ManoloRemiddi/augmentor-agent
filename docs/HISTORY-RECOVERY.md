<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Large chat recovery · Augmentor 0.2.7

A long Pi conversation could appear disconnected even when the runtime and model
were healthy. `session.history` included all streaming deltas alongside the saved
answers. A reproduced history response exceeded the 1 MiB socket limit, so the
transport closed before the UI could restore the chat.

The shared Pi/OpenCode history reader now omits deltas already represented by a
nonempty final answer, removes empty reasoning updates, and pages by encoded byte
size as well as message count. Sequence identifiers remain stable. Incomplete
answers retain their text deltas. Native engine history and the display journal
are unchanged, and recovery never submits a prompt.

The reproduced journal was 7,228,480 bytes. Its corrected history response was
511,766 bytes, with all final replies retained. Regression coverage includes a
48,001-event stream, byte-limited tool history traversed through every page,
incomplete final messages and an explicit error for a single event that alone
exceeds the frame limit. Such an oversized individual event still requires a
separate display strategy; it no longer causes a silent oversized reply.

## Local DSH repair

The locally upgraded DSH 0.1.2-rc.1 failed to import installed plugins that use
`settingsNamespace`. The local installation was restored to Augmentor's tested
DSH 0.1.1-rc.2 and Schemastery 3.18.1 combination. The newer installation and profile
configuration were backed up before replacement. Augmentor's owned presets and
integration were refreshed through its checked setup API.

Updating DSH independently can replace these pinned dependencies. A newer harness
needs a compatibility review with the installed plugins and Augmentor adapter
before replacing this tested configuration.
