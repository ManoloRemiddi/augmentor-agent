<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Windows and RTX Spark: research and analysis

Research date: September 27, 2026. Status: recommendations for the next planning discussion, not an implementation plan or a claim of Windows compatibility. No product code, dependencies, installations, repository commits or releases were changed during this research. No Windows or RTX Spark runtime tests were performed.

Corrected after the user supplied NVIDIA’s RTX Spark product page: the requested hardware is RTX Spark N1X, a Windows on ARM platform. The previous substitution of another product and the resulting additional Linux ARM64 workstream were incorrect and have been removed. This corrected report supersedes that hardware recommendation.

Implementation planning now lives in [the Windows implementation plan](WINDOWS-IMPLEMENTATION-PLAN.md).

## Recommended direction

Keep one Augmentor product, repository, maintained Qt desktop, browser extension and release version. Build separate packages for each supported operating system and CPU architecture. Put operating-system mechanisms behind explicit adapters and keep feature behavior and regression tests shared.

Target supported Windows 11 releases with two builds of the same application: x64 for Intel/AMD PCs and native ARM64 for RTX Spark and other Windows ARM PCs. RTX Spark is an explicit target of the Windows work, not a separate operating-system project. Keep Linux and macOS within the existing shared product. Prefer a signed per-user Windows installer with bundled runtimes. Velopack remains a candidate for evaluation; final packaging selection belongs in the later implementation plan.

## Evidence inspected

Application source was inspected at canonical-repository commit `b8e36a44f6fc58c1a1a491040c81a21c17e82bb7`, in its existing clean worktree. The primary checkout is older and contains unrelated uncommitted Mac work; it was preserved. The current handoff, architecture, parity audit, Mac preview-3 release record, packaging metadata, Windows-sensitive modules and CI were reviewed. Dated older release ledgers were not treated as current capability claims.

The current product metadata identifies 0.2.12. Mac packaging pins Python 3.12.13, PySide6 Essentials 6.8.2.1, Qt 6.8.2, Node 24.19.0 and DSH 0.1.5-rc.1. Existing release targets are `debian13-amd64` and `macos-arm64`.

Public upstream documentation and package metadata establish availability, not runtime compatibility. Several exact DSH 0.1.5-rc.1 package archives were read in memory and checked against the repository lockfile's SHA-512 integrity values. They were not installed or executed.

## Windows support policy

Use release support and actual capability requirements, rather than rejecting computers by purchase age. An older Intel/AMD computer that officially supports our chosen Windows release can remain a valid target.

| Windows target | Recommendation | Reason |
| --- | --- | --- |
| Windows 11 25H2, x64 | Primary baseline | Current broadly applicable Windows release |
| Windows 11 25H2, ARM64 | Native ARM qualification target | Existing Windows ARM machines need coverage |
| Windows 11 26H1 on eligible new hardware | Include in the ARM hardware matrix | Device-specific release; not a universal upgrade requirement |
| Windows 11 24H2 | Do not make it a new long-term consumer baseline | Home/Pro support ends in October 2026 |
| Windows 10, 32-bit Windows, Server and LTSC-specific deployments | Outside initial support commitment | Extra scope without matching the requested modern consumer experience |

Microsoft identifies 26H1 as intended for new devices and not an in-place upgrade for existing 24H2/25H2 machines. Requiring only the numerically newest release would therefore exclude supported hardware. Home/Pro 25H2 remains supported into October 2027 and 26H1 into March 2028. Enterprise/Education servicing periods differ; supporting their ordinary desktop behavior does not establish managed-enterprise certification. Sources: [release information](https://learn.microsoft.com/en-us/windows/release-health/windows11-release-information), [26H1 scope](https://learn.microsoft.com/en-us/windows/release-health/status-windows-11-26h1), [Home/Pro lifecycle](https://learn.microsoft.com/en-us/lifecycle/products/windows-11-home-and-pro).

Ordinary Windows 10 support ended in October 2025; ESU and LTSC exceptions are not a reason to extend Augmentor's initial scope. [Microsoft lifecycle](https://learn.microsoft.com/en-us/windows/release-health/release-information).

Recommended ongoing policy: support explicitly qualified, Microsoft-supported Windows 11 releases, normally the current broadly deployed release plus the preceding still-supported release, with an additional lane for device-specific releases. Re-evaluate at release planning time. Insider builds, S mode restrictions and enterprise installation policies need explicit limits rather than implied compatibility.

## RTX Spark: verified hardware and implications

The user’s specified product is [NVIDIA RTX Spark](https://www.nvidia.com/en-us/products/rtx-spark/). NVIDIA lists RTX Spark N1X laptop and desktop configurations with Windows 11, Grace CPUs, Blackwell RTX GPUs, unified memory up to 128 GB and native CUDA support. The page offers availability notifications; it does not establish an exact retail date. No release date is assumed here.

NVIDIA’s [CPU documentation](https://docs.nvidia.com/rtx-spark/rtx-spark-porting-guide/latest/portingandemulation/cpuspecific.html) identifies ARM Cortex-X925 and Cortex-A725 cores. Consequently, the relevant application target is **Windows ARM64**.

| Hardware | Augmentor application package | Qualification focus |
| --- | --- | --- |
| Intel or AMD Windows PC | Windows x64 | Windows integration and graphics compatibility |
| NVIDIA RTX Spark N1X laptop or desktop | Windows ARM64 | Native dependencies, RTX graphics, optional local inference and unified-memory behavior |
| Other Windows ARM PCs | Same Windows ARM64 application target | Vendor-specific drivers and graphics qualification |
| Apple silicon Mac | Existing macOS ARM64 target | Shared behavior plus Mac integration |
| Supported Linux PCs | Existing Linux target | Shared behavior plus Linux integration |

The intended design is one Windows ARM64 application package usable across compatible vendors, with runtime capability detection. This is an architectural recommendation, not a hardware compatibility claim. There is no need to introduce an extra Linux architecture to satisfy RTX Spark support.

NVIDIA explicitly says developers can prepare an ARM64 application on existing Windows ARM hardware before RTX Spark is available, then validate the NVIDIA paths and the finished application on RTX Spark. Its developer page provides Windows ARM resources for CUDA 13.4, Ollama, llama.cpp, TensorRT for RTX and PyTorch. Some supplied paths are preview/nightly software; listing them does not establish a production-ready combination for Augmentor. [NVIDIA developer guidance](https://developer.nvidia.com/topics/ai/local-ai/port-apps).

For this Python/Qt application, native ARM64 is the preferred target. NVIDIA also documents x64 emulation and ARM64EC migration options, but neither is necessary as our default architecture. The currently documented Qt support does not include ARM64EC; avoid introducing that additional binary model without a concrete dependency reason. The exact Windows feature release and driver baseline for RTX Spark must come from its shipping system requirements; Windows 11 support alone does not prove that every feature release is supported.

Two levels of compatibility must be distinguished:

- **Augmentor application support:** desktop, DSH, browser integration, shortcuts, appearance, install and update all work on RTX Spark. Cloud or remote models can exercise the application independently of a local inference engine.
- **RTX-accelerated local models:** qualify a Windows ARM64 inference runtime and its NVIDIA driver/CUDA stack, then connect it through DSH’s provider interface. Keep model execution in the existing engine boundary; do not create an RTX-specific agent core or make the CUDA developer toolkit a prerequisite for basic application use.

Unified memory requires particular care for local inference: its advertised capacity is shared with the operating system and other applications, not automatically all available to a model. NVIDIA documents memory budgets and allocation behavior that differ from conventional discrete-GPU assumptions. These concerns primarily belong to the inference engine; Augmentor should use supported engines and report resource failures clearly. [NVIDIA CUDA/unified-memory guidance](https://docs.nvidia.com/rtx-spark/rtx-spark-porting-guide/latest/uma/umacuda.html).

Graphics qualification should cover the shared Qt effect, transparency, DPI and sleep/wake on RTX Spark. Laptop qualification also needs battery and sustained-power behavior. Hardware acceleration is detected through supported APIs, not by assuming that every NVIDIA GPU is discrete or that every ARM machine has the same CPU capabilities. [NVIDIA emulation and detection guidance](https://docs.nvidia.com/rtx-spark/rtx-spark-porting-guide/latest/portingandemulation/emulationtips.html).

RAM and disk minimums for the finished Windows application require measurement. Local model requirements must remain separate from application requirements.

## ARM64 dependency findings

Direct inspection of the publishers' PyPI release metadata produced the following results:

| Dependency | Currently pinned Windows distribution | Research finding |
| --- | --- | --- |
| PySide6 Essentials 6.8.2.1 | x64 wheel, no Windows ARM64 wheel | 6.10.1 and current 6.11.2 provide ARM64 wheels |
| sounddevice 0.5.2 | x86/x64 Windows wheels, no ARM64 wheel | Current 0.5.6 provides a Windows ARM64 wheel |
| NumPy 2.5.1 | Python 3.12 x64 and ARM64 wheels available | Availability verified; application use untested |
| ONNX Runtime 1.28.0 | Python 3.12 x64 and ARM64 wheels available | CPU package availability does not prove every accelerator or model works |

Evidence: [pinned PySide files](https://pypi.org/project/PySide6-Essentials/6.8.2.1/#files), [PySide 6.10.1 files](https://pypi.org/project/PySide6-Essentials/6.10.1/#files), [sounddevice 0.5.2 files](https://pypi.org/project/sounddevice/0.5.2/#files), [sounddevice 0.5.6 files](https://pypi.org/project/sounddevice/0.5.6/#files), [NumPy files](https://pypi.org/project/numpy/2.5.1/#files), [ONNX Runtime files](https://pypi.org/project/onnxruntime/1.28.0/#files).

Qt itself supports Windows x64 and ARM64, but that does not supply an ARM64 Python wheel for every older PySide release. Prefer a jointly tested dependency baseline over maintaining a private Qt build or an indefinite Windows-only dependency fork. A newer version's availability is not a recommendation to upgrade blindly. [Qt 6.8 Windows support](https://doc.qt.io/qt-6.8/windows.html).

Audit every native component, including Python extension DLLs, PortAudio, Node add-ons, terminal/FFI bindings and installer helpers. DLLs within one process must match that process's architecture. Independently launched processes can communicate across architectures, but any deliberate mixed package needs explicit qualification.

Windows 11 can emulate x64 applications on ARM. This is a useful transitional test lane, not evidence of native ARM support or a substitute for testing. Kernel drivers require ARM64 builds. Installers must detect the host architecture correctly even when running under emulation. [Microsoft emulation documentation](https://learn.microsoft.com/en-us/windows/arm/apps-on-arm-x86-emulation).

## What the current repository needs

The shared interface and product composition are a good foundation. There is no justification from this audit for a separate Windows UI, a new conversational core or an Electron rewrite. The historical `augmentor_linux` module name is not the fundamental problem.

| Area | Observed source evidence | Required architectural boundary |
| --- | --- | --- |
| Paths and executables | `packages/platform/src/index.ts` knows Unix bundle paths and Darwin XDG mapping | OS-specific executable discovery and application/config/cache/runtime paths |
| Local service authentication | `services/platform_support.py` supports Linux peer credentials and Mac `getpeereid`; other OSs fail closed | Windows same-user IPC with explicit identity/access checks |
| Locks and IPC | Unconditional `fcntl`, `AF_UNIX`, `os.getuid()` in runtime, prompt, memory and lifecycle modules | Shared locking/transport interfaces with Windows implementations |
| Updates and process ownership | `services/lifecycle/lease.py` uses POSIX locks and Linux package queries or Mac branches | Shared maintenance state machine; platform process, lock and activation mechanisms |
| Desktop control | `services/desktop/service.py` selects Mac, otherwise imports Linux GI/portal code | Explicit Windows backend; unsupported systems must not fall into Linux |
| Shortcuts | `shortcuts.py` selects Mac, otherwise KDE | Windows global shortcut adapter, both existing named windows and conflict handling |
| Graphics | Shared Qt Quick effect, CPU fallback, shader record already includes HLSL | Preserve the effect; qualify Windows composition and graphics behavior |
| Release tooling | Linux/Mac workflows and OS-specific packages | Windows build/qualification lanes and one release manifest |

Windows named pipes with explicit per-user security descriptors are a strong IPC candidate; default pipe permissions must not be assumed safe. An authenticated loopback transport is another option if consistently protected, but opening an unauthenticated local HTTP port would weaken the existing boundary. Qt local sockets already help with some UI IPC; the Python/Node services still need a compatible transport and authorization contract. [Named-pipe security](https://learn.microsoft.com/en-us/windows/win32/ipc/named-pipe-security-and-access-rights).

Use ordinary-user background processes, deterministic shutdown and Windows process ownership primitives. Do not elevate the whole agent or make a machine-wide Windows service the default just to keep DSH running. Maintain separate application files and user state; do not put model settings, conversations or logs in a replaceable installation directory. Treat Windows ACLs and reparse points explicitly rather than translating `chmod(0700)` literally.

Desktop capture, input and accessibility require their own adapter. Windows input injection cannot freely control higher-integrity applications; UAC's secure desktop is not a normal automation target. This is an intentional capability boundary, not something to bypass by running Augmentor permanently as administrator. [SendInput restrictions](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput).

Use configurable Windows-appropriate shortcuts with conflict detection. Do not promise the Mac Fn+Space combination on arbitrary PC keyboards. Windows reserves or other programs may occupy key combinations. [RegisterHotKey](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey).

## DSH and optional engines

The pinned DSH packages already include Windows process primitives and a PowerShell shell dialect. Integrity-verified `dsh-terminal-bash` 0.1.5-rc.1 supports `shellDialect=pwsh`; `dsh-pwsh-local` resolves `pwsh.exe`, including PowerShell 7 locations. This is more promising than assuming WSL is mandatory. However, Augmentor's current personal-agent composition explicitly includes the Bash tool. Windows needs an intentional shell/provider composition, prompts and cancellation tests, including commands with spaces and Unicode paths. Existing Windows PowerShell must not be assumed equivalent to the required `pwsh` executable. [Upstream terminal contract](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/terminal/terminal-bash/README.md).

The upstream DSH desktop now has Windows code, but it is a different application shell. Reuse supported harness capabilities through the existing Augmentor adapter; do not substitute that UI or assume all of its implementation is in our pinned version. [DSH desktop documentation](https://github.com/deepseek-ai/deepseek-harness/blob/master/apps/desktop/README.md).

A dependency qualification inventory must cover terminal/FFI binaries, every shipped plugin, credential flows, startup, Stop and orphan-process cleanup. Optional voice, local memory servers and model engines are separate qualification tracks. Basic chat should not force users to install WSL, Docker, a compiler or model weights. If an optional engine requires one of these, expose that requirement honestly. Do not claim full parity while silently omitting a feature that exists elsewhere.

## Installation and distribution options

| Option | Fit for Augmentor | Main uncertainty or cost |
| --- | --- | --- |
| Signed per-user EXE installer plus Velopack | Leading candidate for direct website distribution; Python integration, x64/ARM64 targeting and update tooling | Must prove lifecycle coordination, native-host registration, identity, rollback and trust checks |
| MSIX / App Installer | Strong Windows-managed package identity and update facilities | Packaged-app paths, registry visibility to external browsers, plugin execution and background lifecycle need a focused compatibility proof |
| Inno Setup plus a separate updater | Flexible conventional installer with x64/ARM64 support | Does not by itself resolve Augmentor's coordinated update design; more integration ownership |
| Portable ZIP | Useful for controlled development/diagnostics | Poor default for stable browser-host paths, startup, removal and one visible installation |

Sources: [Velopack Python integration](https://docs.velopack.io/getting-started/python), [runtime targeting](https://docs.velopack.io/packaging/runtime), [MSIX runtime behavior](https://learn.microsoft.com/en-us/windows/msix/desktop/desktop-to-uwp-behind-the-scenes), [App Installer updates](https://learn.microsoft.com/en-us/windows/msix/app-installer/update-settings), [Inno Setup](https://jrsoftware.org/ishelp/topic_whatisinnosetup.htm).

A single downloaded installer can unpack an ordinary application directory with bundled runtimes. That achieves a simple user experience without forcing everything into one self-extracting executable at every launch. Avoid the need for a pre-existing Python, Node or separate DSH install. Existing user-owned DSH installations need a clear connect-or-managed choice; do not overwrite them or silently let two installers own one runtime.

Aim for one Start menu identity, one Installed Apps entry, stable taskbar grouping, no console flashes, one owned startup mechanism, and a complete uninstall that distinguishes removing software from deleting personal data. Reinstallation and repair must be idempotent. These are acceptance requirements, not capabilities already verified.

Public Windows distribution should use a consistent authenticated publisher identity, timestamped signatures and protected signing credentials. Azure Artifact Signing is a candidate subject to current account/region eligibility; a suitable CA certificate is another option. Signing does not guarantee an immediate absence of SmartScreen prompts. Microsoft's current documentation explicitly contradicts older updater guidance claiming instant EV/Artifact Signing reputation; Microsoft's guidance governs this decision. [Microsoft SmartScreen guidance](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation), [Artifact Signing setup](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart).

The existing Mac preview's Apple-independent distribution choice does not remove Windows signing decisions. Updater adoption also does not resolve Mac signing/notarization by itself.

Carry forward component notices, source availability and applicable redistribution obligations for Qt, Python, Node, audio and any bundled PowerShell. Assess the chosen Qt modules and distribution mode before finalizing packaging. [Qt licensing](https://doc.qt.io/qt-6/licensing.html).

## Browser integration and weekly extension updates

Keep the shared extension and the new product behavior: discover installed Chromium browsers and let the user choose another application. On Windows, native messaging uses registry registration and an executable host, so the Mac registration implementation cannot simply be reused. Register only owned per-user entries, validate allowed extension IDs, use a stable launcher path, and preserve unrelated registrations. Chrome, Edge and forks can differ in lookup behavior; Comet's Mac compatibility path is not evidence of its Windows path. [Chrome native messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging), [Edge native messaging](https://learn.microsoft.com/en-us/microsoft-edge/extensions/developer-guide/native-messaging).

For general users, store distribution is the smoother long-term extension route: Chrome Web Store, with Edge Add-ons considered where useful. Keep manual Load unpacked for development/explicit preview use. A normal consumer installer cannot promise silent installation of an arbitrary locally hosted Chrome extension. User approval and browser/enterprise policy remain relevant. [Chrome distribution rules](https://developer.chrome.com/docs/extensions/how-to/distribute/install-extensions).

Desktop and browser-store updates arrive independently. A shared version label cannot make them atomic. Define a protocol handshake, minimum compatible versions and an explicit compatibility window so a delayed store review or older running browser does not break an otherwise valid desktop update. Different store IDs must be included deliberately in the native-host allowlist. Requalify side-panel and native-messaging APIs for each supported fork, without turning the chooser into a closed brand list.

## One product and reliable weekly updates

The current Mac preview still has no automatic updater. Linux has useful selection, maintenance and recovery foundations, but these are not a finished universal updater. This work must improve all targets without erasing their native installation behavior.

Recommended release model:

- One product version, reviewed source commit, compatibility manifest and shared feature contract.
- Platform artifacts carry OS/CPU identity, exact runtime/plugin versions, hashes, signatures and qualification evidence.
- Shared fixes are merged once. CI exercises the same product contracts on every supported platform; platform tests exercise the actual OS mechanism.
- Publish a release set only when its promised targets qualify. An emergency platform hotfix may be staged independently, but must record the exception rather than create a permanent OS branch.
- A common update experience and coordinator can call platform-specific installation backends. Using one library everywhere is optional; preserving one lifecycle contract is essential.

Desired user experience: download and verify in the background, show one update notification, then apply after one user action when active work can be preserved. Coordinate all windows, DSH tasks, browser-owned sessions, voice, memory jobs and pending interactions. A settings dialog should explain why it blocks, offer save/close where possible and resume the pending update; it should not leave a mysterious permanent busy state.

Velopack documents automatic application at startup and operations that can terminate still-running instances. Those defaults require deliberate integration with Augmentor's maintenance guard. They must not be allowed to discard work. It also documents that application-directory files are replaced, reinforcing the requirement for separate user data. [Velopack integration behavior](https://docs.velopack.io/integrating/overview).

Update authenticity needs more than a checksum beside an archive: verify trusted release metadata and expected signer, with key rotation and downgrade policy. Stage immutable packages, retain a recoverable prior application, perform bounded health checks and design data migrations for the supported rollback window. Rolling back executable files cannot undo an incompatible database migration automatically. Never replay an unknown-outcome tool action after restart.

Use staged rollout and a way to withdraw a faulty update. Differential downloads are useful, with a full-download fallback; their adoption should follow reliability. At 100,000 installations, an approximately 529 MB full download is approximately 52.9 TB of transfer per release, before retries. A CDN/object-store budget, caching and staggered checks matter at the stated scale; no hosting price was estimated here.

## Qualification evidence the implementation will need

Automated Windows x64 and ARM64 builds are available through current CI tooling; GitHub lists `windows-11-arm` runners. Hosted tests are useful but do not prove normal consumer graphics, devices or installation prompts. [GitHub runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).

The acceptance matrix should include:

- Clean supported Windows images without developer tools; standard-user install, first-run provider setup, browser connection, repair, update and uninstall.
- Physical x64 and ARM Windows machines; Intel/AMD integrated graphics and an NVIDIA-equipped x64 system; actual RTX Spark hardware before claiming RTX Spark compatibility.
- Real first/second-window shortcuts, tray/Start menu identity, no duplicates, reopen/reboot, sleep/wake and network/provider interruptions.
- Flare transparency, proportional app sizing, mixed monitor DPI, display changes, HDR where applicable and Remote Desktop behavior. The existing shader includes HLSL, but that is not a Direct3D runtime test.
- Browser/store ID combinations and real native-host chat, including Comet; company policy rejection must explain the problem.
- Unicode/long paths, multiple Windows users, read-only locations, unavailable microphone, antivirus interference and file-in-use failures.
- An update during active chat, a pending approval, an open settings dialog, low disk space, failed download, interrupted activation and rollback with preserved chats/models/settings.
- Speech and memory as explicitly separate capability results. A deterministic chat fixture does not establish live-provider, audio-device or full desktop-control readiness.

## Decisions carried into the later implementation plan

The corrected research supports modern Windows 11 and two Windows builds of one shared product: x64 and ARM64, explicitly including RTX Spark in the ARM64 qualification target. Linux and macOS remain part of the same product and release process. No additional operating-system target is required by RTX Spark. The remaining dependency and integration findings still need resolution before compatibility can be claimed.

Planning must settle the shared dependency baseline, installer/updater choice after a compatibility proof, signing identity and delivery channel, browser-store strategy, and the first-release feature/architecture acceptance bar. Native ARM prerequisites now have available upstream candidates, but the complete combination is untested. No changes should be described as implemented on the strength of this report.
