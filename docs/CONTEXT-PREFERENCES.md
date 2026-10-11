<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Original Context plugin preferences on Pi

Settings → Plugins now contains the original dsh-context preference card, alongside the existing MCP control. Its headings, rows, menus, text areas and CSS come from the pinned public [0.68.1 source](https://github.com/bowenliang123/dsh-context/tree/2c8095c34da3fcef729a01437d2df65c83e08499). The newly selected `settingsCard.tsx` has verified Git blob `b9527ef13b3438381075f5e857e0ef0d466fc30f` and original SHA-256 `605120ff915f3bcd3c736d0ba39c2aa5f2c770a2d9c3be273241f5c3c0cfea61`. Its small, marked adaptation gates unsupported fields; original markup/CSS are preserved. The selection is now 99 files: 87 verbatim and 12 marked adaptations. Original Copyright 2025 bowenliang123 and Apache-2.0 remain applicable, separately from the MIT DSH shell and authored Augmentor source.

Seven preferences are connected:

| Original control | Saved choices | Effect |
| --- | --- | --- |
| Context Insights entry | Show / Hide | Original sidebar entry visibility; hiding closes the current Insights panel. Settings remains available to show it again. |
| Trend Chart · Granularity | Step / Turn | Original Context view mount default. |
| Trend Chart · Display | Total / Delta | Original Context view mount default. |
| Trend Chart · Duration curve | Show / Hide | Recorded model-duration overlay mount default; the existing timing coverage note remains applicable. |
| Context Browser · Diff baseline | prev step / prev turn | Original Context browser mount default. |
| Tool Schemas · Sort | By size / By calls / By name | Original tool browser mount default. |
| File Activity · Sort | Most active / Latest / By path | Original file activity mount default. |

View-local toggles do not change the saved defaults. Close/reopen Context or the original slash modal to apply changed defaults. Placement remains Tab and Fleet remains Hide. Those two controls and the empty Prefix/Suffix text areas are visibly disabled, with a note that Fleet, sidebar placement and prompt wrapping are unconnected. These fields cannot alter model input. This increment does not establish Fleet, delegated-child usage, persistent composer/answer drafts or right-sidebar parity.

## Private settings contract and lifecycle

The existing operator-only `settings.describe` accepts `{ns:"dsh-context"}` and returns only that namespace, without querying the prompt-library companion. The legacy unfiltered response adds this namespace after its existing two namespaces. A snapshot contains `ns`, a global settings `revision`, normalized `value`, and `writableFields`. The seven connected scalar choices are the only writable fields. Unsupported/corrupt stored values degrade to safe display defaults; they are not promoted into prompt injection or supplier services.

`settings.mutate` accepts exactly one `set` operation with a one-element field path and exact `expectedRevision`. The Host validates supported choices, atomically writes private profile `settings.json`, then publishes its new in-memory settings. A failed file commit leaves the old settings/revision unchanged. Another operator or settings control changing the global revision makes a stale write fail; refresh before making another choice. A write never changes model selection, routing, permissions, native history or provider payloads.

The browser binds the original `createContextSettings().attach` face to independently authored Pi glue. Controls become read-only during a pending write. Transport/CAS/confirmation failure restores the last served values, exposes the error, disables writes and requires an explicit **Refresh Context preferences** read. Unknown writes are not replayed. A late read/write cannot publish across epoch changes, loss of readiness, read-only revocation or disposal. Inspection links do not fetch private global settings and show disabled schema defaults; the server refuses both settings reads and writes from an inspector token. Separate tabs do not receive live preference pushes: each reads on connection or explicit refresh, and revision checks prevent silent overwrites.

No model request, tool execution, extra AgentSession, supplier Host, registry/price/skill lookup or telemetry endpoint is added. Preferences are in the isolated private preview profile and therefore survive normal immutable preview artifact updates and Host restarts. Shared JS/runtime behavior applies across platforms; this turn qualifies MX Linux only. Further platform packaging remains deferred for owner feedback.

## Qualification

Final source qualification passes **251/251 cases across 38 files**, zero failures/skips/cancellations, prepared QtTest, two workers and unchanged deadlines. Build/type/provenance gates pass. Ordinary bundled qualification and installed roots/history proofs follow separately. The original Context tab/modal wait for the initial preference read before mounting their defaults; pending writes do not remount an open view. Original supplier textarea sizing is retained by excluding those fields from the earlier Augmentor extension-wrapper override. The rendered original card stays within 513- and 1440-pixel test viewports. Tests use independently authored fixtures and the actual public Pi SDK/Host. They do not import private supplier source or production histories.

The first focused browser run used incorrect expected text (`Turn` rather than the original `prev turn`, and shortened sorting labels); it failed without source GUI changes. The second run reached all preferences/default/restart checks but caught a still-open old-origin events poll after deliberate Host shutdown. The fixture now navigates away before stopping its idle owner, then uses the new descriptor. The next focused run passes 8/8. The initial broad run has 249/251 passes: the component-only interaction fixture had not served the new namespace, and the atomic-failure fixture lacked Host busy-state seats. Their independently authored fixtures are completed; the failure check now requires ENOTDIR/EEXIST, not an arbitrary rejection. Subsequent complete 251-case runs pass, including failed atomic commits, invalid success-shaped replies, supplier textarea/viewport checks and the initial-preference mount fence. No deadline or concurrency relaxation is used. Logs remain local under `/tmp/augmentor-context-settings-*`; they are not public fixtures. This is not a full Harness completion claim. All outstanding migration P0/P1 and platform/live/privacy/package gates remain active.
