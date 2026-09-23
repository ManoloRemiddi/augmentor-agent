<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor productization plan

Assessment: 2026-09-06, against the unified 0.2.0 checkout at `69137fc`.
This is a proposed release plan, not evidence that its release gates have passed.

The product gate is that another person can install Augmentor, connect their own
model, complete useful tasks, recover from failures and update it without the
developer repairing their machine. Retain the accepted architecture: one product,
two surfaces, replaceable harness adapters, shared prompts and shared optional
memory. The next work is to make that architecture independently usable.

## Findings from the current implementation

| Area | Present evidence | Remaining release gap |
| --- | --- | --- |
| Common product | Native and browser surfaces use Pi/DSH adapters and the independent Prompt Library. | Common behavior requires tests in both renderers; DSH Branch/Edit remains unavailable. |
| Installation | Built archive, staged replacement and one previous application directory. | Installer requires existing Node/npm, Python/PyQt6/GI; archive installation fetches npm dependencies. Desktop integration assumes KDE. |
| Model setup | Models/providers editor and a local endpoint setup script. | Guided first run independent of the developer's local Qwen server, provider naming and model limits. |
| Browser delivery | Extension and registered native messaging host work in isolated Chromium acceptance. | Separate setup commands, unpacked loading and manual reload; no unified public distribution/update path. |
| Linux role | Shell/files, system inspection and desktop observation. | General desktop mouse/keyboard control is not implemented. |
| Memory | Hindsight selected; provider interface recorded. | No Hindsight connection, retention or recall is implemented. |
| Verification | Real clipboard, browser actions, branch context and recovery checks exist. | Clean-prefix installation was on this PC. Root install proof still names 0.1.0; imported workflows remain under `apps/browser/.github`, with legacy paths. |
| Lifecycle | Pi task check, separate state directories and manual rollback material. | Coherent update/removal of native UI, both adapters, browser host and shared services; migration rollback compatibility. |

Sources in this checkout: [installer](../scripts/install.py),
[installer proof](../scripts/install-proof.py), [local setup](../scripts/setup-local.py),
[browser registration](../scripts/install-browser-host.py),
[uninstaller](../scripts/uninstall.py), [feature matrix](FEATURE-MATRIX.md),
[recorded acceptance evidence](IMPLEMENTATION.md).
This was a targeted implementation review, not a completed security audit or a new
clean-machine test run.

## Proposed first release boundary

Start with a private beta for individual Linux users who bring their own model
credentials or local endpoint. Record exactly which provider/model combinations
support the demonstrated tasks, including image input for screenshot-based work.
Make model costs and any separate memory-service costs visible in setup.

Use one initial certification target. Candidate: Debian 13, x86_64, KDE Plasma,
Wayland with the native Qt app through XWayland, and a conventional Google Chrome
installation. This is a proposed target to validate, not a claim of existing
support. Pin the exact desktop/browser versions in the acceptance record. A Debian
package is the initial packaging candidate. Expand to GNOME, other distributions,
browser variants and Snap/Flatpak browser installations after their own checks.

Bundle the tested Pi runtime. Offer DSH as an optional supported connection with
explicit version detection and setup; never assume the developer's existing DSH
profile/plugins. Keep both adapters in the product. DSH remains preview until its
promised common capabilities pass the same checks as Pi.

Support installing the Linux UI, browser companion, or both. A browser-only install
must not require PyQt or an open desktop chat window. Both choices use the same
local prompt and memory services. Chromium native messaging requires a registered
native application; an extension download alone does not supply our current
backend ([Chrome native messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging)).

Keep shared prompts local to the user's machine initially. Cross-device prompt
sync, Augmentor accounts and managed model billing are separate product decisions.
Hindsight can have its own remote connection; it does not synchronize the Prompt
Library or convert harness-native conversations.

## Delivery sequence and acceptance gates

### 1. Portable installation and first successful task

- Build versioned artifacts from a clean checkout. Include application runtimes
  and locked dependencies, or declare OS packages resolved by the installer;
  users should not run npm, compile code or edit configuration files.
- Split desktop dependencies from the companion. Generate product/component
  versions from one manifest. Preserve existing installations through explicit
  migration rather than renaming live paths blindly.
- Add first-run setup: select harness, connect provider, validate credentials and
  model capabilities, explain permission mode, offer optional memory, run a small
  check and show actionable errors. Preserve existing Models/providers controls.
- Detect unsupported desktops/browser packaging, absent dependencies and shortcut
  conflicts. Allow shortcut recording; the developer's Ctrl+Fn+Space emission is
  specific to that keyboard.
- Place mutable files in per-user data/config/state directories. The DSH browser
  pipe currently puts trace files inside its application directory.

**Gate:** a fresh VM and a second Linux user account, with no source checkout,
developer model server or copied credentials, install the packaged Linux app and
complete chat plus a bounded local-file task using their own model. Uninstall and
reinstall preserve data as documented. Repeat with the companion alone and a real
browser page task. Begin root CI with this milestone, not at release time.

### 2. Complete the advertised agent jobs and shared behavior

Implement Linux computer use behind an environment executor available to both
harnesses: screen/accessibility observation, supported input, target validation,
focus handling and visible Stop. Re-observe after actions and distinguish attempted
execution from a verified result. A changed window must not receive stale input.

For Wayland, prototype the RemoteDesktop/ScreenCast portals on the certification
desktop. The official interface uses a consented session and exposes granted
input devices; actual backend availability still needs testing
([XDG Remote Desktop](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.RemoteDesktop.html)).
Test denied/revoked consent, scaling, multiple monitors and focus changes. An X11
automation test does not establish native Wayland control.

Finish DSH Branch/Edit semantics or retain its preview designation with clear
unavailable controls. Centralize shared base instructions and add environment
instructions/tools through adapters. Test each common feature through both UIs:
clipboard templates, Copy/check feedback, Edit, Branch, model selection, history
and Stop. New features require shared behavior fixtures and both renderer checks.

**Gate:** each advertised surface/harness combination completes its role-specific
fixture tasks. Real clipboard contents, saved file contents, browser DOM state,
desktop application state and preserved branch context establish success.

### 3. Connect Hindsight as shared optional memory

Use one Augmentor memory boundary with user/project scopes across both surfaces
and harnesses. Map the interface to Hindsight's actual retain/recall semantics,
including asynchronous completion, provenance and deletion/export behavior.
Hindsight exposes bank-scoped MCP endpoints; configure authentication for remote
connections and enforce authorized scopes independently of model-supplied bank
names or tags ([Hindsight MCP](https://hindsight.vectorize.io/developer/mcp-server)).

First ship connection to an explicitly configured Hindsight instance with health
checks and instructions. A bundled local server or Augmentor-operated hosting
would require its own deployment, upgrade, backup and cost work. Let users see
what is remembered, control retention, export/delete data and disable memory.

**Gate:** retain a fixture fact in every combination and recall it through the
others in the same authorized scope after restart. Other users/projects cannot
read it. Check deletion against the documented provider semantics. Memory outage
must leave ordinary chat usable and must not create duplicate writes on retry.

### 4. Make releases, recovery and data handling dependable

- Define permissions by available tools and enforced access boundaries. Current
  approval presets are not an OS sandbox. A browser role prompt alone must not
  grant unrestricted shell/filesystem access. Keep routine authorized tasks free
  of repeated prompts; explain exceptional requests where they occur.
- Check browser/native origin validation, private local endpoints and remote
  authentication. Test untrusted page instructions against tool restrictions.
- Review credential storage, transcript/observation retention and diagnostics.
  Existing credential-pattern redaction does not remove all sensitive typed text;
  provide minimal logs, retention limits and a user-reviewed support export.
- Build verified release artifacts and an authenticated update channel; handle
  incompatible component versions before work starts. Update only at a safe
  boundary, keep a working version, and test rollback with data migrations.
- Make removal cover owned launchers, shortcuts, browser host registrations and
  shared services, accounting for components still installed. Offer explicit
  keep-data versus erase-data behavior.
- Prepare a store distribution path for the extension and coordinate its
  independently delivered updates with companion compatibility. Unpacked loading
  remains a development route; Linux also permits packed distribution outside
  the store ([Chrome distribution](https://developer.chrome.com/docs/extensions/how-to/distribute)).
- Inventory redistributed dependencies, licenses and notices. PyQt is GPLv3 or
  commercially licensed, not LGPL. Resolve the intended distribution model before
  bundling; the repository's MIT header alone does not answer dependency licensing
  ([Riverbank licensing](https://www.riverbankcomputing.com/software/pyqt/intro)).

**Gate:** test interrupted updates, incompatible extension/companion versions,
provider failures, expired credentials, stopped/crashed workers and full disks.
Preserve user data and never replay a tool action whose outcome is unknown.

### 5. Independent beta, then public release

Adapt legacy workflows into root CI with pinned harnesses and current artifact
versions. Use deterministic model fixtures for repeatable behavior, plus separately
recorded live-provider checks. Run real Qt and browser interactions; add actual
desktop-session/VM acceptance for capabilities that offscreen Qt/Xvfb cannot prove.

Have 3–5 independent testers install release artifacts using only the supplied
instructions. Record environment, setup failures and completed task outcomes.
Include one update cycle. Every developer intervention becomes a tracked setup or
support defect. Publish a concise start guide, support matrix, data-flow/privacy
description, changelog, known limitations and bug-report route.

**Public release gate:** every declared supported combination passes installation,
role tasks, common UX, Stop/recovery, update and removal. Resolve release-blocking
defects from beta. The first practical milestone is an independently installed
Linux app; extend that same release foundation to the browser, preserving the
user's requested Linux-first order.
