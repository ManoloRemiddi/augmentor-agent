<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Independent private beta

The beta tests whether someone can install and use Augmentor from the supplied
artifacts and instructions without access to the developer's checkout, credentials
or model server. Automated fixtures are recorded separately from human results.
No testers have been recruited or contacted by this work.

## Candidate and environment

Use the clean CI artifact set linked in PRODUCTIZATION-STATUS.md. Record its
version, source commit and SHA-256 before sharing it. Do not substitute a local
build marked `dirty: true`. Distribution is through the private repository's
authenticated artifact downloads until a reviewed public release exists.

Initial target: Debian 13 on x86_64, KDE Plasma Wayland, native app through
XWayland, and conventionally installed Chromium. The companion alone is valid;
it does not require the native UI. Other distributions, desktops, Chrome/Brave
and sandboxed browsers need their own evidence. Desktop GUI input is a limited
preview: one monitor, accessible target controls, ASCII text, consented sharing,
and a model that accepts images. Check the latest desktop evidence before
including GUI control in a tester's assignment.

Each tester supplies their own model connection. Record the exact provider/model,
model limits, whether image input was checked, and observed task quality. A local
HTTP model fixture passing tests does not certify a commercial provider or its
visual reasoning. Optional DSH requires the supported separately installed CLI;
optional Hindsight requires a separately operated service. No accounts, keys or
model weights are shipped.

## Assignments for 3–5 testers

| Tester | Primary assignment | Status |
| --- | --- | --- |
| A | Fresh native installation, Pi setup, file task and shortcut | Unassigned |
| B | Companion-only installation, Pi browser task and shared prompts | Unassigned |
| C | Both UIs, supported DSH setup, shared behavior and memory | Unassigned |
| D (optional) | Desktop input, scaling, focus changes and Stop | Unassigned |
| E (optional) | Upgrade/recovery, accessibility and installation instructions | Unassigned |

Every assigned tester also performs the update cycle. Keep a sanitized record of
each intervention; an installation that needed the developer to fix a path is an
installation defect, even if the remaining tasks work.

## First installation

1. Follow FIRST-RUN.md and BROWSER-DISTRIBUTION.md using the downloaded packages.
2. Configure a model in the UI. Confirm a rejected key or unavailable endpoint
   produces a recoverable error. Do not include the key in a report.
3. Complete a bounded task in a new fixture directory: create a short text file,
   inspect its contents independently and ask Augmentor to change one line.
4. In the browser, operate a harmless test page and inspect the resulting page
   yourself. Record expected and actual text.
5. Create a Prompt Library entry ending in `[clipboard]`. Paste a distinctive
   sentence to the system clipboard and invoke the prompt on both surfaces.
6. Copy replies and user inputs into a separate editor. Check the text, tick
   feedback and scroll position. Branch a reply and edit the latest input. Check
   the original chat stays unchanged and the revised prompt is submitted once.
7. Stop a deliberately longer fixture task. Inspect the external result, then
   reconnect and confirm the unfinished action is not automatically repeated.
8. Optionally configure Hindsight, explicitly retain a harmless fact, recall it
   through the other interface/harness, export it, delete it and disable memory.
9. Export the Support report, review its contents, and share it only if useful.

## Update and removal

Use two clean versions from the beta artifact list. Keep a copy of the old
extension directory. Follow LIFECYCLE.md to prepare, back up and update. A running
task must refuse maintenance without cancellation. Close the connected DSH host
before replacing the runtime. Recheck/refresh the DSH integration after an update
if its copied browser component no longer matches the new release.

Reopen and compare the same prompts and chats. Test an intentionally mismatched
extension/companion: it must request a matching pair before work can start.
Perform the documented rollback, then update again. Remove and reinstall while
keeping data; verify the fixture conversation and prompt are still present and
owned launchers/shortcuts behave as documented.

## Issue record

Record candidate version/hash, OS/desktop/browser versions, selected harness and
model, exact reproduction steps, expected result, actual external result, and
whether developer help was needed. Use invented fixture text. Screenshots, chats,
logs and copied text can contain private data; share them deliberately. The
Support report excludes those payloads but is still reviewable before export.

A release-blocking defect loses data, runs an action on the wrong target, replays
an unknown outcome, bypasses a role boundary, or prevents the documented install,
Stop, update or rollback. Public release requires resolved blockers, completed
independent assignments and an observed update cycle. This document does not mark
any of those human checks as passed.

## Invitation draft (not sent)

I'm testing a private preview of Augmentor Agent for Linux and Chromium. Would
you be willing to install it using the supplied guide, try a few harmless fixture
tasks, and test one update? You would use your own model connection and keep your
credentials private. Please record anything that needs my help, including setup
failures. The app and optional memory service may send the content you choose to
your configured providers. This is a preview, with the supported environment and
known limits described in the test guide.
