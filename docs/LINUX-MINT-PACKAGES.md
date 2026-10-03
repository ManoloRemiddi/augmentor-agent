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

The next separate read-only diagnostic instantiates the actual installed
`DshAdapter` once and calls `host.describe` once after HTTP identity matches.
HTTP appears at 60.41 seconds; full adapter readiness is observed at 62.94
seconds. Normal authentication succeeds, both product presets are available
and unbroken, and authenticated preset/catalog reads finish in 0.81 seconds.
The last Node sample records 62.89 CPU seconds at 62.67 seconds elapsed. This
run demonstrates startup beyond the public 60-second budget before a healthy
adapter read; it does not identify the bootstrap loading stage or establish
every earlier run's cause. Zero model/provider requests are counted. Native
audits, five settings, old-account hashes, empty workspace, all three prior
journals and owned-process/no-listener cleanup pass. No public executable or
timeout changes, model turns, session/history operations or installer replay
are made. Connected-product/history and graphical/physical gates remain open.

The maintained proof adds an explicit, separate emulated-VM v3 qualification
for this exact owned installed clean2035 fixture. Its only longer bound is
120-second startup; default/public startup and each role turn remain 60
seconds. The fixed new journal binds the source, artifact, selected runtime,
five settings, unchanged empty workspace and all four preserved qualification
records. Altered hashes, pending/unknown outcomes, model traffic in read-only
diagnostics or a preexisting v3 journal refuse before model-server binding.
New run-owned Linux/Browser sessions each receive one journaled prompt; strict
restart/history and no-replay checks remain. Reports explicitly record both
budgets and emulated qualification, keeping original/full and public60 proof
flags false. Polling checks occur between bounded reads; v3 rejects a successful
read observed after 120 seconds before any further role mutation. Default
behavior is retained, but a 60-second pass label requires both actual measured
starts to be ready within 60 seconds. Seven added cases cover the v3 bounds,
late successful reads, preservation, single-dispatch unknown outcomes and
prior-record refusal; all 24 proof cases pass. Published v3 execution then fails:
first authenticated startup takes75.35seconds within120, and the Linux role's
single prompt completes with its expected reply. The two model requests cover
the response and first-prompt title. Browser and restart/history checks are not
reached. Only `settings.yaml` changes, from387 to403bytes, because shipped
DSH0.1.5-rc.1 saves the model selection and YAML2.9.1 reserializes eight sequence
indentation lines. Parsed values remain exact; the maintained byte guard refuses.
No run, prompt, setup, settings restoration or normalization follows that failure.

The source-only installer correction uses SafeDumper with `indentless=False`
for initial settings. It preserves model values and other serializer defaults.
All18 setup tests pass, including a real lock-integrity-verified Node/YAML2.9.1
Document roundtrip that reproduces the old formatting change and proves the new
output byte-stable. This dependency is explicit in
`AUGMENTOR_TEST_YAML_MODULE`; the case skips if that exact version is unavailable.
The selected2035 bundle remains unchanged. Qualification needs a reviewed fresh
clean artifact and fresh ordinary account, with all prior failures retained.

The run-created detached memory service initially survives Node cleanup.
Exact PID/start/argv/private socket/Unix peer binding and read-only state show two
completed transcript events, no inference jobs and no configured backend.
Approved one-shot idle maintenance prepare/commit closes it normally in0.25seconds,
without signals. Both earlier guard refusals precede socket creation/RPC and remain
recorded. Final native audit, leases, old-account hashes, five current settings,
all prior/failed journals and no-process/socket/listener checks pass. Overall v3
remains FAIL; the original full proof and public60-second claims remain false.

The source-only fresh/post-install proof correction now arms companion ownership
before its first DSH launch, refusing an existing socket/process. Its adjacent
`release/owned-memory-companion-proof.py` is bound by a fixed source checksum and
must accompany any external proof staging. A new idle service can receive only
one journaled maintenance prepare/commit after exact executable/source/argv,
UID/PID/start, DSH home and private Unix socket/peer checks. Active, foreign,
replacement or unknown outcomes stop the proof; attempted cleanup is never
repeated or escalated with signals. It waits at most20seconds for normal process
and socket closure. External after-proof checks establish native lease closure;
the running proof itself holds a runtime lease.

Nine synthetic real Unix-server tests and26 maintained proof cases pass. They
include live owner/inode replacement after status, busy/preexisting peers, lost
commit replies, source/start mismatches and refusal before model binding or SDK
dispatch. This is source/protocol qualification, with fresh installed acceptance
pending. No new bundle, installation, VM run or settings normalization is made.

## Clean16bcb build and fresh-account proof scope

The [fresh candidate checkpoint](../release/qualification/next-targets/20261003-mint16bcb-fresh-emulated-proof.json)
records exact clean16bcb native, Browser and complete builds with streamed payload
inspection PASS. The detached builder preserves the finite reviewed public
wheel/source-Qt cache and original Handy BUILD receipt; no Handy rebuild or
private source export is introduced. At least4GiB free space was retained before
each allocation. Artifact hashes and manifest/setup identities are recorded.
This is build evidence; native adoption and fresh connected-product acceptance
remain false.

Read-only inspection finds `augmentor-corrected-proof` UID/GID1002 and its home
unused. Both existing accounts, UID1000's ten protected files and failed
UID1001's thirty settings/journal/history/memory files, remain unchanged. The VM
still has clean2035 native packages and an idle verified runtime. A future
approved transaction must repeat host/QEMU/marker/root/idle and protected-hash
guards, preserve signed APT metadata and an actual dry-run, then use normal
same-version APT `--reinstall` for exact16bcb bytes. Repeat unused name/UID/group/
GID/home checks before creating a locked ordinary account with home0700 and no
admin membership. Do not rename stamps, alter old settings or adopt receipts.

The [fresh emulated proof contract](COMPLETE-INSTALL.md#fresh-mint-emulated-proof-admission)
adds a separate fixed16bcb/UID1002 entry and exclusive one-run journal. It uses
the unchanged complete installer and verified source-Qt environment, two measured
120-second authenticated startups and60-second turns, refusing successful reads
crossing either respective bound before another mutation. Default public60
behavior and the old clean2035/UID1001 post-install admission remain unchanged.
Unknown installer/SDK/companion outcomes are preserved without replay. Exact
settings bytes, both new role histories, no restart model replay and normal
owned idle companion cleanup must pass; external native lease/process/socket/
listener readback and both earlier-account hashes are required afterwards.
Focused synthetic tests verify these fences; no fresh VM product run, account
creation or native adoption has occurred. Desktop/browser/lock/audio/legal gates
remain open.

The first fresh transaction attempt stops at host admission before SSH: the
published guard expected absolute disk/QMP strings, but the exact retained QEMU
boot record uses `file=guest.qcow2,format=qcow2,if=virtio` and
`unix:qmp.sock,server=on,wait=off`. Its daemonized cwd is `/`; an absolute disk FD
proves the owned fixture file. The maintained correction pins the retained boot
argv and explicit startup directory, parses only the two permitted same-directory
path forms and checks kernel listener ownership plus one bounded Unix peer read.
It sends zero QMP protocol bytes and requires unchanged PID/start. Original
pre-SSH refusal stays recorded.24 fresh source tests,26 existing proof tests and
9 real Unix-companion tests pass; corrected publication and the actual native/
account/installer/connected-product run remain pending.
