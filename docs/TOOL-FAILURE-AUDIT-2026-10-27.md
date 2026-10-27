<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Browser and Desktop tool failures — 27 October 2026

## Finding

The inspected failures are real, but they do not show a general loss of tool calling or a single Pi defect. The two primary examples have different immediate causes:

- A DSH Browser document-formatting attempt encountered an unsupported rich editor, unavailable screenshot permission and the desktop backend's single-monitor restriction. It then continued through dozens of shell and GUI workarounds without verifying the requested document change.
- A Pi Desktop conversation successfully read, wrote and edited files, but two attempts to open generated HTML kept foreground shell tools occupied until the user stopped them. The deployed shell tool has no default deadline. Its supported browser opener also excludes local files, and the pilot's desktop environment resolution is broken by its private runtime directory.

Capability gaps, inconsistent deployment and inadequate failure recovery explain these examples better than “the model cannot call tools.” A provider/model defect, an overall failure rate and the date of a regression have not been established.

This is a diagnostic report and proposed repair sequence. Application code, installed releases, running sessions, documents and model settings were not changed.

## Inspected installation and evidence boundary

| Component | Observed identity | Meaning |
| --- | --- | --- |
| Canonical checkout | `main`, `f353c52b`, with substantial pre-existing modifications | Older source checkout; preserved, not treated as the running application |
| Selected Desktop and running Browser native bridge | `20261021-110654-8ad67ae5`, compatible product `0.2.11` | Actual legacy product deployment; includes the DSH Browser path |
| Chromium extension registration | Existing `browser/0.2.11` folder | Its service worker and observation module differ from the selected release's extension files |
| Running Harness migration pilot | `20261025-191212-2ea08039`, recorded source `ab7f1665`, product `0.2.13`, Pi SDK `1.1.0` | Separate Pi host, state and configuration |
| Newer canonical Harness worktree inspected | `efd85b83` | Reference source and tests; no relevant differences from `ab7f1665` in the execution, reassessment, portal and browser observation paths compared |

The Chromium registration and files on disk were inspected. The browser's currently executing service-worker bytes were not independently extracted, so this report does not equate registered files with a live-byte attestation. The saved permission error is direct evidence of what the failed tool returned.

Private conversations, account configuration, document identifiers and raw payloads remain outside Git. Findings below summarize those records; they are not copied into public fixtures.

## DSH Browser: document formatting

The 27 October attempt used the explicitly saved `deepseek-official/deepseek-flash` selection with high reasoning; the request catalog agrees with that selection. Across approximately eleven minutes it made **85 tool calls**, including **47 shell calls** and **15 image reads**. The requested saved document change was not verified; the user stopped the attempts. This does not establish that no partial edits occurred. Document version history was not inspected by this audit.

### Rich-editor support was missing

The connected browser snapshot returned the Google Docs toolbar and navigation, with 429 characters of page text, rather than the document's canvas body. The DOM click/type driver can interact with ordinary controls, but that does not establish that it can edit or verify this rich editor.

The loaded `google-docs-browser` skill explicitly described that limitation and instructed the agent to call `browser_capabilities`. That tool was **absent from the actual 110-tool request catalog**. A preserved legacy policy module defines it, but that module is not wired into the inspected product configuration; its skill folder is still wired in. This is a concrete skill/tool contract mismatch.

The old module also restricts the entire agent to browser-only tools. Restoring it wholesale would remove capabilities intentionally shared by the current product. Reuse its useful capability contract only after reconciling it with current ownership and permissions.

### Screenshot permission failed, and the registered extension lacks an existing correction

The screenshot tool returned an `activeTab` permission error and no image. The registered extension folder still uses automatic `openPanelOnActionClick: true`. The selected release's service worker instead handles the explicit toolbar action and disables automatic opening, with a comment documenting the screenshot permission requirement.

Both the registered worker and observation module have different hashes from their selected-release counterparts. Therefore updating the native application or its version label did not establish adoption of the matching browser behavior. The correction already exists in source/release material; first qualify deployment and the real toolbar/tab permission flow before inventing another screenshot implementation.

Whether the required toolbar gesture occurred in that particular failed session is unproven. Even the corrected worker cannot manufacture a missing user gesture. Replacing its bytes alone is therefore not a demonstrated repair of the recorded attempt.

A screenshot correction will restore observation only. It does not supply a Google Docs editing driver.

### Desktop fallback was deliberately unavailable on this setup

The desktop connection tool returned “This preview requires one connected monitor. No sharing session was opened.” The deployed portal checks `len(observed['screens']) != 1` before requesting OS consent. The failure session's display diagnostics show multiple connected outputs.

This is an explicit implementation restriction, not a tool transport crash. Removing the check alone is insufficient: the input token, selected screen, window geometry and screenshot coordinates must remain consistent across offsets, scaling and rotation.

A read-only current topology check found three enabled outputs: DP-5 at scale 1, rotated, origin (0,0); HDMI-A-1 at scale 1.75, origin (720,664); DVI-I-1 at scale 1, origin (2183,664). This describes the inspection-time topology, not a reconstructed full snapshot at the earlier failure. The running desktop service's portal file has the same hash as the selected product and Pi pilot portal file, including the single-monitor guard.

### Recovery amplified the problem

After those limitations, the agent tried X displays, KWin scripts, clipboard probes, `spectacle`, `ydotool` and guessed coordinates. Its own observation reported diagnostic typing in the Augmentor composer instead of the document. That observation does not independently prove a window-focus bug; coordinate/target confusion remains possible. Either way, the requested target was not reliably controlled.

This is a misdirected-input finding, beyond slow execution. Earlier diagnostic dialog commands also dispatched Enter. The later command associated with text appearing in the Augmentor composer did not itself dispatch Enter; this audit does not claim that it submitted a new chat message. Raw shell input bypassed the fresh-target checks of the consented desktop backend. Preserve full-access shell work, but require a verified target for GUI input regardless of the dispatch route.

Only three results were flagged `isError`: the two capability refusals and a user abort. Several shell outputs contained command/display/interface errors while their compound commands returned success. Counting error flags alone would miss this failure pattern.

Progress/repeated-output checkpoints were delivered, but they were advisory. The evidence does not support solving this by adding another general “try harder” prompt. Recovery needs to track the target operation and whether a supported route made verified progress, while retaining legitimate shell work and the owner's full-access preference.

## Pi Desktop: local artifacts and foreground tools

The 26 October conversation used the explicitly selected local Qwen model. File reads, writes and edits worked, including a later successful checklist write. The actual model payload exposed **48 tools**, including desktop helpers and codemode. It did not expose the connected extension's `browser_tabs_list`, `browser_snapshot` or DOM input tools on this native surface. Searching codemode did not reveal a tool for opening a local artifact in the requested preview.

### The supported opener did not cover the requested artifact

`linux_browser_open` accepts HTTP(S), while the user wanted generated local HTML opened. The deployed helper rejects `file:` URLs before browser dispatch. Existing Harness preview facilities are not the same as an agent-callable, verified local-artifact opening operation.

The agent fell back to direct Chromium shell commands, including commands piped through `head`, without a timeout. Two recorded shell results ended only when stopped by the user:

| Attempt | Recorded tool duration | Recorded outcome |
| --- | --- | --- |
| Open generated article HTML | 2,924,457 ms — about 48 min 44 s | `Command aborted` |
| Open generated slides HTML | 1,214,760 ms — about 20 min 15 s | `Command aborted` |

Those durations are the tool's own recorded measurements. This investigation did not relaunch Chromium or prove which browser/shell process condition kept each command alive. Browser startup, singleton forwarding, inherited streams and the pipeline are candidates; they remain hypotheses.

A GUI browser remaining alive when started in the foreground can be normal process behavior. The confirmed product failure is allowing that operation to occupy the foreground indefinitely, rather than evidence that Chromium itself crashed or deadlocked.

### Default shell execution is unbounded

The deployed Pi SDK bash schema explicitly says “optional, no default timeout.” Its implementation installs a timeout only when one is provided. Synthetic calls against the exact installed SDK confirm that explicit timeouts and cancellation work.

Augmentor's ten-minute *automatic response recovery* budget does not impose a deadline on an ordinary foreground shell operation. Its ninety-second model-step notice is informational, not a shell cancellation mechanism. These are different boundaries and should not be presented as a general execution timeout.

### The pilot's private runtime directory also breaks desktop discovery

The pilot process retains `WAYLAND_DISPLAY=wayland-0` but sets `XDG_RUNTIME_DIR` to a private profile runtime directory. That directory contains neither the graphical Wayland socket nor the native Desktop singleton lock expected by the desktop helper.

Calling the deployed `desktop_environment()` under the actual pilot environment reproducibly reports that the Desktop app must be opened, even though it is running. Under the graphical user's runtime directory, the same helper resolves its environment successfully. No application was opened during this check.

This is a confirmed setup/integration defect. It is not a sufficient explanation for the two long shell hangs: those commands had already manually selected the graphical runtime directory. Preserve profile state/isolation while separating it from graphical-session environment discovery.

## What is not established

- A general Pi or DeepSeek tool-calling outage. Both paths contain successful tools. Ordinary connected-browser operations also returned results in other sampled DSH conversations.
- A DeepSeek reasoning-history/schema/call-ID defect. The observed session successfully dispatched many tools; this audit did not perform a full transport conformance test. DSH request headers retain configuration/tool schemas, not an independently captured complete provider-wire history.
- A model-quality comparison. The two main cases use different models and tasks. Switching model, precision, context size or harness is not a demonstrated repair.
- A specific regression date or last-known-good Google Docs workflow. Deployment drift is proven; its causal timing is not.
- An orphaned Playwright lock causing these failures. The inspected MCP processes are children of the live Pi host and use isolated browser operation. Their count alone does not establish a leak or relevance to the connected-browser failure.
- Three independent Pi failure sessions. One real conversation contains two distinct long waits; other sampled permission/route errors have separate explanations. No frequency claim is made from that sample.

## Verification performed

Nine isolated tests passed against the registered extension and exact installed Pi artifact/SDK, without model requests, browser launch, OS consent requests or GUI/document input:

| Check | Result |
| --- | --- |
| Screenshot capture with synthetic permission denial | Returns the permission error; attempts capture once |
| Reassessment after repeated failed shell output | Produces advisory evidence, not a hard stop decision |
| Shell without explicit timeout | Remains active at the observation boundary and cancels on Stop |
| Shell with an explicit short timeout | Terminates with a timeout result |
| Explicit timeout with a synthetic pipeline and background descendant | Retains partial output and stops the descendant as well as the shell operation |
| Portal with 0, 2 or 3 synthetic screens | Rejects before any portal request |
| Portal with 1 synthetic screen | Reaches only the mocked consent boundary |
| Supported browser opener given local HTML | Rejects before launching a browser |
| Desktop discovery under pilot versus graphical runtime | Fails under pilot environment; resolves under graphical environment |

These confirm failure contracts and integration gaps. They do not qualify Google Docs authoring, a physical screenshot permission flow, multi-monitor input or model task reliability. Small private reproduction scripts and reviewer receipts are retained locally; no production source test/build was presented as an installed update.

## Proposed repair sequence and acceptance gates

1. **Bound foreground execution and failed recovery.** Add a configurable foreground-shell deadline using the already working SDK timeout/cancellation path, preserve explicit long operations and partial output, and reuse the existing bounded job subsystem for background work. Escalate a GUI capability failure after bounded attempts that add no verified progress; do not use a universal eight-tool stop, silently change shell pipeline semantics or automatically replay a timed-out change. Require fresh target verification before GUI input, including shell-driven input, while retaining ordinary full-access shell work.
2. **Make capability reporting truthful.** Reconcile skills with the actual registered tools and current surface. Clearly distinguish DOM form input, rich-editor authoring, screenshots, desktop input and isolated MCP browsing. Do not revive the old blanket browser restriction. A skill must not demand an unregistered discovery tool. Add a focused catalog/skill compatibility check using the actual composition rather than assuming every mentioned tool is active.
3. **Repair local-artifact opening and desktop environment routing.** Separate the graphical runtime from private app sockets/state, accounting for Wayland, the native singleton and PipeWire/session dependencies. Prefer exposing generated artifacts through the existing scoped localhost preview and the HTTP opener, with explicit path validation and dispatch-versus-load status. Do not create another preview server or pass unrestricted `file:` URLs through the existing HTTP opener. Opening must return after dispatch rather than waiting for a GUI process to exit.
4. **Qualify browser adoption and screenshot permission.** Reuse the existing toolbar correction, reconcile the actual extension folder with its matched release, and verify capture of the intended tab after the real user gesture, after navigation and after permission loss. Preserve extension identity, conversations and drafts. A copied folder or matching version label is not acceptance; do not broaden extension permissions silently.
5. **Qualify a document-authoring route separately.** A configured native document integration or a tested canvas-aware driver could address Docs. Either requires its own access and verification contract. Screenshots and DOM typing alone do not justify an authoring claim, and this audit did not obtain new account access.
6. **Treat multi-monitor control as a separate implementation.** First investigate the portal's existing single-selected-stream path (`multiple=false`) on a machine with several monitors, before designing a custom multi-screen mapper. Retain the guard until selected-screen geometry, scale/rotation, cross-monitor windows, focus changes, stale tokens, Stop and equivalent macOS boundaries are qualified. Do not disable monitors as a routine workaround.

Acceptance should include a small repeated task matrix across Pi/DSH and the actual installed client: ordinary DOM editing, unavailable screenshot permission, local HTML opening, unavailable rich-editor authoring, foreground timeout/Stop and loss of the target window. Add a real Docs editing case only when an authoring route exists. Measure verified completion and bounded failure, not just successful tool dispatch. Model comparisons come after deterministic integration defects are addressed.

## Independent review and decision

The owner-requested second opinion ran through authenticated Claude Code Max with explicit `claude-opus-5-5`; the returned model-usage record confirms that model and a successful review. No alternative model or invented review service was substituted.

The initial reviewer advised tracing the deployed screenshot and monitor errors before broad diagnosis, collecting actual Pi evidence, treating Docs canvas behavior separately from ordinary DOM tasks, and inspecting recovery, tool payloads and installation drift. The lead accepted those priorities and recorded the decision in [the existing plan](PLAN.md#october-27-browserdesktop-tool-failure-investigation).

The second review also completed successfully on `claude-opus-5-5`. It recommended prioritizing a minimal shell deadline and truthful capability reporting over extension deployment, explicitly recording misdirected input, distinguishing normal GUI process lifetime from a proven hang, testing process-tree cancellation and preferring existing localhost preview support. It advised deferring a new background subsystem and a canvas-specific editor driver.

Lead decision: accept that ordering and the additional verification requirements; the added pipeline/descendant test passed. Reuse existing jobs and preview mechanisms. Preserve uncertainty about toolbar gestures, live service-worker bytes, partial document changes and Chromium lifetime. Do not turn implementation defaults into owner homework or restore the obsolete browser-only restriction. Optional new account access or broader extension permissions would be separate owner decisions if implementation requires them; this audit requests neither. No large implementation or rollout has been started.
