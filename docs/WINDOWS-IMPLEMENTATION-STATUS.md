<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Windows implementation evidence

September 27, 2026. The owner authorized autonomous implementation and will
connect a Windows machine for joint physical testing afterward. Follow the full
[implementation plan](WINDOWS-IMPLEMENTATION-PLAN.md); this ledger does not narrow
its outcome. No Windows customer release or installed-product claim exists yet.

## Baseline and environments (W0)

Implementation branch `feat/windows` starts from reviewed `main` `b8e36a4` plus
the planning commit `8565172`. Product 0.2.12, DSH 0.1.5-rc.1, Pi 0.85.1,
schema 1 and the current protocol versions remain unchanged. Unrelated open
source work and existing Linux/Mac installations are preserved. Reconcile new
reviewed changes before release; do not copy unreviewed local overlays.

The unchanged baseline passes TypeScript check/build, 182 Node tests and 538
native tests (three skips) in isolated Python 3.12.13 / PySide 6.8.2.1.
The initial system-Python attempt lacked QtTest; that was an environment failure,
not waived tests or a product regression.

| Environment | Availability/evidence | Boundary |
| --- | --- | --- |
| Linux x64 development | Available; baseline suites pass | Existing personal processes untouched |
| macOS ARM64 | Existing Mac 14/26 CI and authorized network Macs | Candidate dependency upgrade still needs testing |
| Windows x64 | `windows-2025` hosted job added; execution pending | Server runner is build/runtime evidence, not Windows 11 client acceptance |
| Windows ARM64 | `windows-11-arm` hosted job added; execution pending | Require native-process readback; no RTX hardware claim |
| Physical Windows | Owner will connect a machine later | DPI, graphics, input, microphone and client installer tests remain pending |
| RTX Spark N1X | No accessible hardware verified | Hardware qualification remains required |
| Signing/publisher | No repository signing secrets or self-hosted runners found | Certificate/identity and browser-store publication remain external gates |

No account credential values were read or copied. Hosted qualification runs have
read-only repository permission and receive no signing or personal-model secrets.

## Runtime candidates (W1)

`release/windows/runtime.json` and architecture-specific hashed requirements lock
the candidates. They are explicitly **unqualified until execution passes**.
Python 3.13.15 is selected for both Windows targets because the inspected standalone
Python 3.12.13 distribution lacks Windows ARM64. Qt/PySide 6.11.2, sounddevice
0.5.6 and PyYAML 6.0.3 supply native ARM wheels missing from the previous pins.
Keep the other pinned native/voice dependencies unless a concrete failure requires
a change. No current Linux/Mac runtime pin is silently upgraded.

The staging tool downloads and verifies exact Python, Node 24.19.0 and PowerShell
7.6.6 archives, installs only hashed binary Python packages and checks dependencies.
The runtime probe requires native execution, imports actual Qt/NumPy/ONNX/PortAudio,
renders a Qt widget, launches private Node/PowerShell and inspects Python PE machine
types. DSH staging uses its existing lock and reviewed preparation script, with
real FFI, search, shell, termination and terminal tests. This does not prove an
installed Augmentor conversation or physical device behavior.

Velopack 1.2.158 is the candidate installer library. The native launcher embeds
private Python without PATH-based DLL resolution. Compilation, two-version
installation/update/removal, busy-work coordination, independent recovery and
publisher trust still require their own proofs; runtime imports cannot select
the installer on their behalf.

## Feature and gate ledger

Each row retains the shared product requirements. Fixture evidence, actual
providers, installed artifacts and physical hardware must remain distinguishable.

| Work | Current state | Required next evidence |
| --- | --- | --- |
| W0 baseline | Local baseline recorded; hosted jobs prepared | Windows job execution and current-source reconciliation |
| W1 native runtime and installer | Candidate locks and runtime probe implemented | Native x64/ARM execution; two installed versions; failure/recovery proof |
| W2 paths, ownership, IPC, locks | Pending | Same-user secure transport and lifecycle, existing-OS regressions |
| W3 managed DSH/model setup | Pending | Clean-user real harness Send, Stop and restored chat; separate live provider |
| W4 desktop, two windows, shortcuts, tray | Pending | Shared interaction suite, actual Windows shell and approved appearance |
| W5 chosen Chromium/Comet companion | Pending | Native host registration and real selected-browser conversation |
| W6 computer control | Pending | Consented capture/input, Stop and Windows privilege boundaries |
| W6 voice/memory/Home/Pi | Pending | Existing feature contracts and configured-engine connectivity |
| W6 RTX inference | Pending hardware | Native compatible backend, measured shared-memory behavior |
| W7 signed install/repair/removal | Pending | Clean ordinary user, one identity, preserved persistent data |
| W8 coordinated weekly updates | Pending | Real N→N+1, busy/draft/settings protection, recovery across OS backends |
| W9 full artifact qualification | Pending | Exact candidate plus physical Windows and separately RTX evidence |
| W10 publication and guides | Pending | Signed public artifacts, anonymous website download, installed update |

G1–G5 remain open. Continue work while physical hardware is unavailable; do not
mark the overall implementation complete based on build or fixture success.

## First native execution, September 28

GitHub run `36353583238` at `f3f6de6` executed native x64 and ARM64, loaded the
actual Qt/NumPy/ONNX/PortAudio/Velopack modules, rendered the widget and launched
private Node and PowerShell. Both correctly failed the subsequent strict PE
inventory: sounddevice includes unused x86 audio DLLs in its x64 wheel, and
PySide6's ARM64 wheel includes an unused ARM32 `vccorlib140.dll`. The staging
policy now excludes only reviewed, individually hashed foreign DLLs and retains
the strict inventory check. The corrected run remains pending. Earlier successful
imports alone do not establish that the complete candidate passed.

Separately, candidate Qt/PySide 6.11.2 passes the same 538 Linux native tests
(three skips), preserving existing behavior under this library upgrade. Mac
candidate GUI checks and native two-version installer fixtures are added to CI.

At `89ae133`, the complete x64 runtime probe passes. ARM64 also needs the
individually hashed Shiboken copy of the unused ARM32 runtime excluded. The
shared Windows build exposed CRLF conversion breaking shader provenance hashes;
`.gitattributes` now preserves source bytes across checkouts. Installer compilation
exposed `cmd.exe` quoting in the build harness, corrected without changing client
execution. Mac candidate UI checks passed, but the job ended on a nonexistent
test filename; that test selection is corrected, not treated as a passing job.

The first W2 primitive is a shared/exclusive process lease adapter. Three real
separate-process Linux tests prove shared readers, exclusive maintenance and
kernel release on abnormal process exit. Windows runs the same tests next.
It is not yet wired into product services and does not claim compatibility with
DSH's separate file-lock protocol. Secure paths and transport remain pending.

The next isolated W2 adapter uses pinned pywin32 312 native wheels for Windows
token identity and ACLs. It creates persistent folders under the OS Local AppData
known folder with a protected current-user/SYSTEM allow-list, refuses permissive
existing directories without changing their permissions, and rejects junctions
and other reparse ancestors. Windows tests exercise owner/ACL readback, reopen,
permissive-path refusal and junction redirection. It is not yet adopted by the
application launcher; execution evidence is pending. This adds no global Python
installation and makes no changes to the owner's machine.

At `523fe9a`, run `36354229667` proves the native runtime on both architectures,
the selected Mac Qt behavior tests, and x64 process leases. The **x64 disposable
installer lifecycle passes**: native embedded launch from a Unicode/space path,
install hooks, local feed download, reopen with auto-apply disabled, refusal while
a fixture process is busy, update/reopen, retention of the previous package,
uninstall hooks/native-host registry cleanup and preserved settings. This remains
an unsigned installer-mechanism proof, not full-app or authenticated rollback
qualification. Reports are retained as the run's `windows-evidence-x64` artifact.

The same run finds a Windows ANSI decoding failure while inspecting a DSH npm
manifest. Package metadata now explicitly uses UTF-8; generated design assets
use UTF-8/LF on every OS. Windows build Python runs in explicit UTF-8 mode, and
the native launcher sets isolated Python preconfiguration to UTF-8 before startup
and supplies that mode to ordinary child services. The installer fixture checks
the actual interpreter flag. ARM64 DSH/installer work from this run is still in
progress; a new source revision must not erase the outstanding evidence boundary.

W2 import refactoring now routes Augmentor-owned branch journals, Home pairing,
Pi startup and lifecycle leases through the shared lock adapter. POSIX behavior
still delegates directly to `flock`; no third-party DSH history lock has been
substituted. The complete Linux native suite passes after these import changes
(544 tests, six platform/environment skips). Windows now runs the shared live
zoom, activity and window interaction tests as well as its platform probes;
actual Windows rendering/interaction results remain pending for that source.

The ARM64 installer proof at `523fe9a` also completes successfully, including
all lifecycle assertions above. Both native architectures therefore have evidence
for the selected installer mechanism; G1 still requires the complete DSH payload
and remaining clean-machine/trust checks. The first private-path probe at
`52964ae` finds that pywin32 token handles do not implement Python context
managers; token ownership now uses explicit `finally: Close()` and tests actual
process-token identity. The fixture does not mask failed ACL checks. Independent
DSH and UI probes now continue after an unrelated probe failure to collect useful
evidence; the overall job still fails if any required probe fails.

The isolated Python named-pipe adapter is now implemented for W2 qualification.
It preserves byte-stream framing, restricts the server ACL to user/SYSTEM,
rejects remote clients and pre-created names, and checks both peers through
kernel pipe process IDs and process-token SIDs. Overlapped operations have
timeouts/cancellation; the listening name stays owned between accepts. Tests
exercise repeated connections, clients disappearing before a request, large
Unicode responses, occupied-name refusal, reuse after close and read cancellation.
The adapter is not yet wired into application services. Native execution,
different-user rejection and authenticated Node interoperability remain pending;
do not infer these from the source or from Linux-skipped tests.

At `d13f504`, actual Windows x64 shared zoom/flare/window interaction tests and
desktop preview rendering pass. Native pipe probes expose three incorrect API
binding assumptions: file access constants belong to `ntsecuritycon`, the pipe
identification flag belongs to `win32file`, and pywin32 312 does not export
`CancelIoEx`. The correction uses the published bindings and an explicit kernel
binding for cross-thread cancellation, waiting for pending reads/writes before
freeing their handles. Separate-process framing and close-during-read tests are
added; their native execution remains pending.

DSH staging reaches its license inventory and correctly rejects missing Windows
entries. The four locked x64/ARM64 Sharp/Koffi npm archives were fetched and
verified against lockfile integrity. Exact Windows Koffi 3.2.1 binaries use the
existing matching MIT notice. Sharp 0.35.4 declares **Apache-2.0 AND
LGPL-3.0-or-later**; the inventory now retains that combined expression, the
Apache text, the LGPL supplement and the upstream native-library attribution
table. It does not select away LGPL obligations or mark the distribution review
complete. Corresponding source/replacement evidence remains a W7 release gate.
Six license-inventory tests pass, including missing supplemental-notice refusal.
