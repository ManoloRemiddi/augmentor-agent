<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor Harness web client

A local operator interface for the existing Pi runtime, served by `packages/runtime/src/harness-server.ts`. Build first, run an isolated configured runtime profile, then use `npm run harness` with the same environment. `npm run harness:proof` provides a disposable synthetic-provider demonstration.

Chat, Trajectory and Context use the real host read models. DOM content is rendered as text; retained image blocks use approved data image types. No external fonts, scripts, analytics or CDNs are loaded. Full diagnostic payload capture is off by default and applies to future requests when enabled.

Composer/model/history actions wait for startup and selected subscription/history/model readiness; Enter during selection preserves the draft without inference. Ordinary/FIFO and steered input use approved Pi handlers, skills and templates while Chat/Edit retain original submissions. Extension-consumed input produces status, and interrupted ordinary preparation remains unknown without replay; arbitrary trusted handlers may still need to settle. This does not complete the shared Prompt Library/editor or full command controls.

The responsive conversation drawer, bounded ledger rows and accessible real buttons retain their behavior at narrow widths. Durable queue/identified steering and latest-input Edit/persisted-reply Branch have real SDK and isolated Linux Chromium qualification with a synthetic provider. Branch performs no inference; Send edit creates an exact native child and submits through the queue. Selected conversation identity survives tab reload; composer drafts remain in memory. Prompt library/editor, voice, richer source provenance and all remaining service/platform/installed migration gates remain open. Existing Native and Browser surfaces keep their approved layouts.

Read [the implementation and test record](../../docs/AUGMENTOR-HARNESS.md) before claiming workflow or installed parity.
