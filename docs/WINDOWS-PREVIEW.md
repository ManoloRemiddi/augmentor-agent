<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor Agent for Windows — 0.2.13 preview

First public Windows preview. Windows 11 **25H2 or later**, build 26200 or later.
Choose **x64** for Intel/AMD PCs or **ARM64** for Windows on ARM.
Find your processor type in Settings → System → About → System type.
Windows 10 and Windows 11 24H2 are not supported by this installer.
RTX Spark hardware has not been tested; ARM64 compatibility is not hardware certification.

## Before downloading

This preview is **unsigned**. Windows may warn about an unknown publisher or block
it under Smart App Control or your organisation's security policy. Only download
from [augmentoragent.com](https://augmentoragent.com/#windows-download) or the
[official release](https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v0.2.13-windows-preview.1).
If SmartScreen offers **More info → Run anyway**, proceeding is your decision after
checking the source and checksum. If Windows policy blocks it, wait for a signed
release. Do not turn off Defender, Smart App Control or organisational protections.

## Install and connect

1. Download the installer matching your System type and open it. Install as your
   normal Windows user. Python, Node, PowerShell, DSH and required plugins are
   bundled; no separate developer tools or system runtime installation is needed.
2. Leave **Open Augmentor** selected when installation finishes. Afterwards open
   **Augmentor Agent** from the Start menu. There is one installed application.
   Login startup is optional in the installer.
3. Open the three-dot menu → **Agent setup** → **Install and start DSH**. After it
   starts, choose **Add or change model**. Enter your own provider, API key and
   model, or a compatible model server connection. Accounts, credentials and model
   weights are not included; paid providers may charge for usage.
4. Send a short message and confirm you receive an answer. Close and reopen the
   desktop to check that your conversation is preserved.
5. To add Browser, choose **Browser setup** and select the installed Chromium-based
   browser you want to use. You can browse to its `.exe`; it is not restricted to
   a fixed brand list. Setup opens its extension page and supplies the extension
   folder. Enable **Developer mode**, choose **Load unpacked**, select that folder
   (paste the supplied path), and pin the extension. Use the matching bundled
   extension, not an older separately downloaded copy. Browser stores and enterprise
   restrictions may limit developer-mode extensions. Comet on Windows has not been
   physically qualified.
6. Press **Ctrl + Alt + Space** to show or hide Augmentor. The default second-window
   shortcut is **Ctrl + Alt + Shift + Space**. Change shortcuts in settings if
   another application uses them. Appearance → App size adjusts the entire UI.

## Preview limits and updates

The preview focuses on the shared desktop, DSH setup/chat and Chromium companion.
Native x64 and ARM64 builds and installed development candidates have automated
Windows runner evidence. **Physical PC acceptance starts with this public download**;
we do not claim RTX Spark testing, every browser/provider, or complete OS parity.

Automatic update notifications and one-click updates are **not enabled**. Do not
install a different version over this one: cross-version manual upgrades are not
implemented. Future releases must supply a supported upgrade procedure. To repair
this exact build, first finish active tasks and close all Augmentor windows/browser
work, then use Installed apps → Augmentor Agent → Modify or rerun this same installer.
Do not delete conversations or settings to bypass a refused repair.

Local voice and memory engine provisioning, desktop automation, Pi and Codex
integration are not qualified for Windows. The source contains shared controls and
adapters; their presence does not establish that those features are ready here.
No account from the developer's machines is included.

## Remove or report a problem

Use Settings → Apps → Installed apps → Augmentor Agent → Uninstall. Finish active
work and close Augmentor first. App removal retains conversations and settings.
Personal data is stored under `%LOCALAPPDATA%\Augmentor`; installed program files
are under `%LOCALAPPDATA%\Programs\Augmentor Agent`. Do not manually remove data
unless you intend to erase it. Repair/recovery copies also consume disk space.

When reporting feedback, include x64/ARM64, Windows version/build, whether setup or
first launch failed, the exact visible message and browser name. Share a screenshot
if useful. Keep API keys and private conversations out of public issues. You can
[open an issue](https://github.com/ManoloRemiddi/augmentor-agent/issues) or send feedback
to the person who provided this preview.

## For maintainers

Build from one committed shared revision with **Windows public preview build**.
Both architectures use hash-locked private runtimes and the explicit profile in
`release/windows/public-preview.json`. Staging compiles launchers without development
qualification switches, seals all files, and the build verifies native public
launcher rendering and the complete inventory before packaging. Inno compiles
normal per-user Known Folder paths and refuses disposable qualification locations
in public mode. Publish installers, SHA256SUMS and this guide together. Unsigned
public preview is distinct from future signed/stable delivery. Hosted rendering is
not a physical acceptance test; x64's hosted Server runner does not install this
25H2-only public Setup.
