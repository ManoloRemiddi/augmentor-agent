<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Linux Mint 22.3 source-runtime candidate

The explicit package target is `linuxmint22.3-amd64`, restricted to
`ID=linuxmint`, `VERSION_ID=22.3`, x86-64 and `/usr/bin/python3.12`. Its
[`mint223-cp312-x86_64-source-qt-voice` policy](../release/linuxmint22.3-python-source-qt-voice.json)
requires the reviewed source Qt runtime. Other Mint versions, LMDE, a Noble
package relabelled as Mint and a system-PySide fallback remain refused.

The candidate reuses the exact seven reviewed Noble-built wheels, Qt 6.8.2 native
stage and original PySide6 `augmentor2` derivation receipt. It does not claim
those inputs were compiled on Mint. The 18 Qt libraries, 67 regular native/plugin/
QML files and 18 SONAME links keep their original hashes and provenance. The
source contract is enforced by [the finite native verifier](../scripts/linux-source-qt.py).
The new target/profile gives Mint a distinct policy hash and immutable runtime
identity; its environment is prepared at its final ordinary-user XDG path.
Never copy or relabel an existing Noble virtual environment or its receipt.

The [Debian-format builder](../scripts/package-debian.py) requires `--source-qt`
and the exact reviewed wheel/native input cache for Mint. It supplies a separate
runtime and matching desktop `.deb`, preserves upstream notices and keeps their
root-owned inputs readable to the preparing user. The system recipe supplies
Python 3.12 venv, GI/GTK4/AT-SPI, GStreamer with its Python overrides and GstApp/
GstAudio typelibs, Secret Service, CFFI/NumPy, ICU 74 and the measured native Qt/
Handy dependencies. Bundled Node 24.19 remains the application runtime.

Both dpkg preinst hooks check the exact host before creating maintenance state.
Desktop preinst also checks the installed runtime's target and version. Existing
active-component leases, pending interruption recovery and user-data retention
apply. The [complete assembler](../scripts/package-complete.py) rejects
cross-target Debian-format inputs even when package names and versions match;
setup checks the installed clean source, target and complete runtime contract.
Its managed profile cannot fall back to online pip or system Python. Desktop,
component, startup and Node/voice selection share the immutable runtime and
verified source-Qt library/plugin/QML environment.

The existing [installed Mint session report](../release/qualification/next-targets/20261002-mint223-installed-session.json)
proves normal signed-ISO installation on an ext4 disk, detached-ISO boot,
password login, lock/unlock and reboot. It records Cinnamon 6.6.4 and an X11
session with no Augmentor installed. These facts do not qualify the new package.
Real installed runtime imports, GUI rendering, full Desktop/Browser/Handy setup,
shortcut/Stop and lock/reboot integration, native transactions and physical audio
remain separate tests. Record exact post-install system packages: admitting the
dependencies can update Python, libc and PipeWire from the original ISO baseline.

The focused source tests cover exact target/ABI refusal, Python/Node identity,
native manifest binding, managed-runtime fallback refusal, both preinst host
checks, same-version cross-target desktop refusal, source input verification and
loader paths. They are synthetic checks, not installed-product acceptance.
The policy retains `qualified`, `licenseReviewComplete` and
`embeddedSourceCoverageComplete` as false. Public release and recipient source/
licensing obligations remain open; no source-builder, recipient-control or license
files are changed by this adapter. See the [rollout ledger](LINUX-DISTRO-ROLLOUT.md),
[source runtime entrypoints](LINUX-SOURCE-RUNTIME-ENTRYPOINTS.md) and
[Cinnamon adapter contract](LINUX-CINNAMON-ADAPTER.md).

## October 3 installed qualification and startup bound

[The installed checkpoint](../release/qualification/next-targets/20261003-mint-native-install-runtime-startup-bound.json)
records exact clean368 native packages and bundle in the dedicated persistent
Mint22.3 VM. Authenticated APT install/audits and all seven managed wheels,
Qt6.8.2/PySide6.8.2.1, QML and23-library/plugin closure pass. Cinnamon, Muffin,
screensaver, kernel, Mesa, PipeWire and libc are preserved by the transaction.
The prepared runtime is verified; no Desktop selection exists yet.

Complete setup fails on its second DSH startup after integration installation,
with an empty startup log and retained preparing receipt. An independent
unchanged launch becomes ready in55.86seconds; this explains the tight margin
but does not establish the exact earlier cause. The maintained setup deadline
now allows120seconds for each owned start. Early exit, token/host verification,
identity/integrity, cleanup and no replay remain intact;16 setup and7 native
complete cases pass. New matching artifacts and safe explicit partial recovery
remain required. The exact Fedora clean368 bundle also uses60seconds; the earlier separate120-second
interpretation was incorrect. New Fedora artifact acceptance and Cinnamon
input/shortcuts/audio remain open.

## Clean2035 setup and separate proof-loader failure

[The clean2035 checkpoint](../release/qualification/next-targets/20261003-mint2035-installed-setup-proof-loader.json)
records the same owned ISO-installed VM with a fresh locked synthetic UID1001,
private home and no administrator groups. UID1000's preparing receipt, model
settings, product token, integration ownership and presets retain their hashes.
Signed Mint/Ubuntu repository checks pass; normal APT reinstalls only the exact
matching runtime/Desktop packages, with idle component leases and native audits.
Cinnamon, Muffin, screensaver, libc and PipeWire versions remain unchanged.

The unmodified clean2035 complete installer succeeds and selects its verified
Mint source-Qt runtime. The full public proof subsequently fails when its direct
preview Python invocation cannot load `libQt6Core.so.6`; it has not reached the
separate 60-second connected-runtime checks. A read-only audit verifies the
selected immutable runtime and imports QtCore/Gui/Widgets with Qt6.8.2 using
the production runtime environment. Owned setup/runtime processes have exited.

The maintained proof now delegates loader paths to that verified environment
for the preview and inherited Node/Python workers. Six focused cases include an
actual child ELF-loader regression, source/native environment behavior and
inventory/preload/linked-policy refusal. They do not replace the retained failed
VM proof. Its installed setup must not be replayed with new synthetic ports or
silently adopted as another bundle. Full proof, graphical Cinnamon/Browser,
shortcuts/lock/reboot, physical audio and public licensing gates remain open.

The maintained post-install entry is now implemented for only this existing
clean2035 fixture. It binds the saved loopback ports and all five settings
hashes, checks the exact native installation/immutable selected runtime, and
refuses enabled/active/uncertain login services. It reads and preserves the
actual `dshService: augmentor-dsh.service` field. Before starting anything, it
requires the hash-bound initially empty workspace store; persisted or extra
session data is preserved and refused to prevent accidental startup recovery.
Its exclusive one-run journal prevents adoption of interrupted/uncertain runs.
Nine added protocol cases cover state/history preservation, stale run refusal,
single-dispatch unknown outcomes, 60-second failure cleanup, changed restart
history, occupied ports and source/account/target refusal.

The reviewed external post-install proof now runs against unchanged installed
clean2035 bytes. Its native offscreen preview succeeds, then DSH misses the
unchanged 60-second readiness limit before any SDK mutation or model turn.
Cleanup verifies idle owned processes, clean native audits, all five settings,
the original account's ten hashes and the unchanged empty workspace. The
94-byte child log records a denied `.env` read in the inherited SSH account
working directory. Installed DSH catches that read failure and returns; the
warning does not establish the timeout cause. The original full proof remains
failed and the successful installer remains distinct.

The maintained proof now explicitly places preview and owned DSH children in
the verified synthetic home. Two additional cases check real child cwd and
parent preservation, and the narrow proposed `post-install-proof-cwd-v2` route
with the exact preserved initial failed journal hash. It refuses prior pending
requests, unknown outcomes, altered records or a preexisting second-run journal.
The exact published `b12af5e` correction has now run once against installed
clean2035. Preview succeeds; DSH again misses the unchanged readiness budget
before SDK mutations or model turns. The child cwd is correct and its log is
empty, so the denied `.env` warning has been removed. Read-only samples show
37.79 CPU seconds at 38.91 seconds elapsed, and 61.56 CPU seconds at 63.51
seconds elapsed. These samples establish activity during startup, not its
loading stage or ultimate cause. Both journals remain preserved; cleanup,
native audits, both accounts' settings and empty workspace pass. No connected
product/history/model proof is claimed, and no second-run replay is allowed.

A separate authorized readiness-only diagnostic observes matching product HTTP
version/home identity at 56.43 seconds with zero counted model/provider requests.
It uses unchanged installed clean2035 bytes, one owned Node process and HTTP GET
only. This is narrower than the full adapter's authentication/preset/SDK
readiness checks and does not turn either retained 60-second failure into a pass.
Its own result remains failed: the immediate final port-bind check reports
`EADDRINUSE` after owned process/server closure. Subsequent read-only checks find
no target-port listener or kernel socket entry, idle owned processes, clean native
audits, unchanged five settings and old-account hashes, unchanged empty workspace
and both preserved journals. The immediate bind-refusal cause was not captured.
No diagnostic or failed proof is replayed; the maintained executable is unchanged.
