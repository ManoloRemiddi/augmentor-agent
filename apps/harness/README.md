<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor Harness web client

A local operator interface for the existing Pi runtime, served by `packages/runtime/src/harness-server.ts`. Build first, run an isolated configured runtime profile, then use `npm run harness` with the same environment. `npm run harness:proof` provides a disposable synthetic-provider demonstration.

Chat, Trajectory and Context use the real host read models. DOM content is rendered as text; retained image blocks use approved data image types. No external fonts, scripts, analytics or CDNs are loaded. Full diagnostic payload capture is off by default and applies to future requests when enabled.

The responsive conversation drawer, bounded ledger rows and accessible real buttons retain their behavior at narrow widths. The web client is an incremental inspection interface; queue/steering, prompt editor, branch controls, voice and richer context visualization remain open. Existing Native and Browser surfaces keep their approved layouts.

Read [the implementation and test record](../../docs/AUGMENTOR-HARNESS.md) before claiming workflow or installed parity.
