<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor Harness web client

Reasoning settings use the authenticated Pi Host: saved Manual/Adaptive mode and supported effort per conversation; profile enable/text-only/preset controls and exact model/tier mappings. Neutral defaults have no mappings. Revision conflicts preserve the draft; Reload explicitly discards it. Settings do no inference, and active chats prevent saves. Context displays each request's requested effort, saved level, classification, applicable route and request-only contribution. See [qualification](../../docs/AUGMENTOR-HARNESS.md#adaptive-reasoning-and-effective-thinking-controls); Native/Browser controls and live-provider acceptance remain open.

A local operator interface for the existing Pi runtime, served by `packages/runtime/src/harness-server.ts`. Build first, run an isolated configured runtime profile, then use `npm run harness` with the same environment. `npm run harness:proof` provides a disposable synthetic-provider demonstration.

Chat, Trajectory and Context use the real host read models. DOM content is rendered as text; retained image blocks use approved data image types. No external fonts, scripts, analytics or CDNs are loaded. Full diagnostic payload capture is off by default and applies to future requests when enabled.

Composer/model/history actions wait for startup and selected subscription/history/model readiness; Enter during selection preserves the draft without inference. Ordinary/FIFO and steered input use approved Pi handlers, skills and templates while Chat/Edit retain original submissions. Extension-consumed input produces status, and interrupted ordinary preparation remains unknown without replay; arbitrary trusted handlers may still need to settle. Full command/resource composition remains required.

Prompt library reuses the Browser picker/editor and shared service. Stable rename/delete and revision conflicts preserve drafts; Refresh preserves editing and Reload selected explicitly replaces it. Enter/Tab/click inserts a saved prompt; another Enter sends. Clipboard selection reads one snapshot and cannot send while pending or replace a different conversation's draft. Library failure preserves the alias on Enter. Shared improvement instructions are editable; Pi prompt improvement is explicitly unavailable. Editor operations perform no inference and create no separate store.

The responsive conversation drawer, bounded ledger rows and accessible real buttons retain their behavior at narrow widths. Durable queue/identified steering, latest-input Edit/persisted-reply Branch and shared prompt editing have real SDK/service and isolated Linux Chromium qualification with synthetic inputs. Branch performs no inference; Send edit creates an exact native child and submits through the queue. Selected conversation identity survives tab reload; composer/editor drafts remain in memory. Pi prompt improvement, full command/resource composition, voice, richer source provenance and all remaining service/platform/installed migration gates remain open. Existing Native and Browser surfaces keep their approved layouts.

Read [the implementation and test record](../../docs/AUGMENTOR-HARNESS.md) before claiming workflow or installed parity.
