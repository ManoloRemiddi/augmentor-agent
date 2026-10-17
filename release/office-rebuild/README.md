<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

## Packaged cleanup contention correction — October 17

The first 24,743-input sealed carrier **20261017-115954-59433a62**, application
`76ace249`/runtime `4c86603d`, retains its exact inventory but fails managed
active/queued disposal (297 pass/one failure). It is unactivated and not accepted.
Normal concurrent helpers could hold the journal directory lock briefly; the
fallback's nonblocking attempt turned that contention into `unavailable`.
A real independently held metadata lock reproduces the old premature refusal.

Journal metadata transactions now wait for cooperating writers. Root leases
still use nonblocking exclusive acquisition, preserving held or foreign roots.
Node's existing ten-second exec deadline now sends SIGKILL, including to a stopped
helper. The helper's kernel parent-death hook remains. Deadline delivery needs
a running Node event loop; do not infer metadata timeout progress while both
caller and helper are stopped. New tests hold/release an actual directory flock
and stop an actual named helper, verify termination at the deadline and recover
the unchanged private copy afterwards. There is no conversion/action replay.

The final source cohort passes 300 Node/43 Python (45 files/19 Chromium, no skips),
and a read-only/networkless 3 GiB/zero-swap/one-CPU/128-PID container passes 21,
with its actual-user-manager case explicitly skipped. The host cohort includes
real manager checks. The 0644 negative file is explicitly chmodded/stat-checked,
independent of packaging's 077 mask. Recovery uses DejaVu Sans from CI's declared
`fonts-dejavu-core`; an absent Liberation font is a truthful diagnostic, not a
renderer failure or reason to suppress missing-font metadata.

The earlier hosted process failures also reproduce with an authored non-reaping
PID1. Both unchanged cases pass when only Docker init is added. The workflow now
requests [`container.options`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idcontaineroptions)
`--init`, whose [Docker purpose](https://docs.docker.com/reference/cli/docker/container/run/#init)
includes signal forwarding and child reaping. No exit/reap assertion or existing
timeout is relaxed. The previous hosted failure is retained; new full hosted,
fresh ordinary/sealed/package and installed acceptance remain open. No old seal
is patched, no owner app/data is changed and public Office packaging stays gated.
[Exact source/control evidence](packaged-cleanup-contention-qualification-20261017.json).

## Managed Office scratch recovery — October 17

The actual Host passes its private state directory to
`createLinuxManagedOfficeConverter(options, stateDirectory)`. The new
`office-scratch-state.ts`/`office-scratch-journal.py` bridge prepares only
`stateDirectory/office-scratch/v1/{data,records}`. Mode/UID/shape checks and bounded
receipts precede admission; state is explicit, and neither `/tmp` nor another
profile/workspace is swept. `createLinuxOfficeScratch(state)` retains its separate
cleanup process, now recording root dev/inode and owner PID/start/boot identity
before publishing readiness. The no-state native/unmanaged seats are preserved.

Root leases and a journal-directory lock serialize cooperating cleanup. Recovery
uses nonblocking exclusive root leases and preserves a still-held renderer root.
Live owner tokens are skipped, including across concurrent converter instances;
a stale PID number alone grants neither liveness nor signaling authority. Cleanup
never signals a discovered PID. An external atomically published deleting receipt
precedes descriptor-anchored content removal. An absent deleting root can retire
its receipt; an absent ready root remains unknown. Nested symlinks are unlinked,
and replaced root contents are not traversed. Unknown record/allocation names,
partial writes, invalid schemas/duplicates/links/permissions or identity mismatch
preserve evidence and refuse managed Office admission. Ordinary chat/default
Office remain available through their existing paths; no automatic fallback is
selected for a refused managed conversion.

After `npm run build`, run:

```sh
AUGMENTOR_MANAGED_OFFICE_TEST=1 node --test --test-concurrency=1 \
  tests/office-scratch-recovery.test.mjs \
  tests/office-process-managed.test.mjs \
  tests/harness-office-managed-chromium.test.mjs
```

The ten recovery cases use actual independent owners/helpers and private authored
data. The admitted original entry startup is stopped before owner loss; it is not
claimed as an independently traced Wasm-open/CPU-stage boundary. Kernel process
tokens confirm all admitted actors are gone before cold recovery. Separate
deleting-phase cases author valid phase receipts with data present/absent; they
qualify restart interpretation, not power-loss or a killed real deletion syscall.
Authored PID-reuse/prior-boot controls are separate from actual process death.
Outside symlink targets and replaced/unknown roots stay exact. The full source
cohort passes 298 Node/45 files/19 Chromium, focused Python passes43 and changed
shared-helper native compatibility passes24, without skips/failures. Existing
engine assets are reused; no heavy rebuild or installed change occurs.

The journal is converter-initialized, often at first Office use after a cold
restart. Normal completion removes data and receipts. Force loss can retain
plaintext private copies until verified recovery; full profile backups can include
them. This is not encryption, filesystem/network isolation or guaranteed recovery
from every bootstrap/publication/power-loss window. Unverifiable pre-ready
allocations are preserved, never guessed. Exact ordinary/sealed/installed package
and rollback qualification, wider corpus/security/source/public packaging gates
remain. [Data policy](../../docs/DATA-AND-SUPPORT.md#managed-office-recovery-copies--october-17)
and [exact source/evidence](managed-scratch-recovery-qualification-20261017.json).

## MX managed Office resource limits — October 17

`AUGMENTOR_OFFICE_BACKEND=linux-managed-wasm` selects an additional, uninstalled
Linux x64 candidate. The earlier `linux-process-wasm` seat remains a separate
diagnostic/source option; unset/default `pinned-kit` is unchanged. This candidate
requires the existing MX systemd user manager, `/run/user/UID/bus`, cgroup v2,
`systemd-run`, `systemctl` and `busctl`. Tested version: **257.13**. No packages
are installed, no system service enabled and no model/speech setting changed.

`office-process-scope.ts` starts a private random `augmentor-office-*.scope` with
fixed arguments and a private local user bus. Scope execution preserves the
supervisor PID, parent relationship and input/output descriptors. The effective
limits are `MemoryMax=3221225472`, `MemorySwapMax=0`, `OOMPolicy=kill`,
`TasksMax=128`, `CPUQuota=100%`, runtime `timeoutMs+2000` milliseconds and
`TimeoutStopSec=2s`, group termination and final SIGKILL. Environment expansion is
disabled. The Python helper checks its exact cgroup name/membership and reads
effective kernel limits before renderer admission. It confirms manager identity,
termination policy and raw microsecond deadlines over the local user bus.
Rejected/absent/weaker controls refuse admission; there is no automatic fallback.

With an actual MX user session, after `npm run build`:

```sh
AUGMENTOR_MANAGED_OFFICE_TEST=1 node --test --test-concurrency=1 \
  tests/office-process-managed.test.mjs \
  tests/harness-office-managed-chromium.test.mjs
```

Without explicit opt-in these platform tests skip, rather than impersonating a
user manager in generic CI. An explicit opt-in requires the real manager; missing
capabilities fail. Six process tests plus the original GUI pass. Kernel controls
are independently read by the Node observer; fixtures use real scopes/helpers.
The manager terminates work while owner/supervisor/renderer are stopped; after
the owner resumes, cleanup completes. A 64 MiB authored allocation control
produces manager `Result=oom-kill` and whole-group termination. It is separate
from successful actual Wasm conversion at 3 GiB. Active and queued real-Wasm
disposal and distinct fresh-converter recovery also pass. Initial fixture
assertions incorrectly dereferenced an already-reaped identity and assumed the
guard must exit nonzero on a manager SIGTERM; those failures remain recorded.
The guard correctly returns failure metadata after graceful termination; only
successful conversion metadata is prohibited in that case. Both default and
existing Thin engines pass the actual managed Host/original-GUI proof, using
identical assertions/deadlines. The final source cohort passes **288 Node** across
44 files/19 Chromium files, plus **43 Python** source/notice/packaging/parser
checks, with no skips or failures. [Exact source and evidence](linux-managed-seat-qualification-20261017.json).

This is resource/process supervision, not filesystem/network isolation. Kernel
limits and manager deadlines do not qualify durable recovery if every cleanup
owner disappears. Pre-ready bootstrap windows, durable scratch recovery, exact
ordinary/sealed/installed adoption and broader corpus/security/source/public
packaging gates remain. Both owner reviews remain untouched. Official systemd
[scope execution](https://github.com/systemd/systemd/blob/v257/man/systemd-run.xml),
[scope deadlines](https://github.com/systemd/systemd/blob/v257/man/systemd.scope.xml)
and [resource controls](https://github.com/systemd/systemd/blob/v257/man/systemd.resource-control.xml)
describe the underlying platform; the actual checks above establish this MX evidence.

## Opt-in Linux process converter — October 17

The runtime implementation in `packages/runtime/src/office-process-*` is an
explicit source-only Linux x64 backend, `AUGMENTOR_OFFICE_BACKEND=linux-process-wasm`.
Unset/default `pinned-kit` behavior is unchanged. Do not set this on the owner's
review as a substitute for package/adoption qualification.

The original provider's converter factory runs one unmodified Wasm entry per
renderer. A Python supervisor arms kernel parent-death hooks before admission,
uses pidfds to kill/reap admitted work and enforces an independent deadline even
while the Node owner is stopped. Scratch has its existing separate cleanup owner;
a fresh supervisor lease is acquired after fork. The renderer inherits its
owned directory and parent-created publication descriptors. It renders into a
private nested output, verifies source identity and copies the bounded PDF into
that publication. Matching device/inode/version/SHA-256 receipts are checked again
by the parent after supervisor close. Failure removes only a matching owned
publication inode, preserving a replacement. Request/reply metadata is versioned
and byte bounded, options and font metadata are validated, and persistent font
cache writes are disabled for this seat. Provider queue/cache/reader and GUI
authority are unchanged; no new agent loop or engine dependency is introduced.

After `npm run build`, run the focused faults and actual original GUI:

```sh
node --test tests/office-process-linux.test.mjs
node --test tests/harness-office-process-chromium.test.mjs
```

The ten faults distinguish authored process actors from actual Wasm conversion
races/recovery. Both default and prepared Thin engines pass the original GUI's
unchanged assertions/deadlines. To qualify the source implementation with the
full contained corpus, use a new unselected app containing current `dist`, the
existing Thin engine and the original rich fixtures:

```sh
python3 -B release/office-rebuild/contained-boundaries.py \
  --app "$UNSELECTED_CURRENT_RUNTIME_APP" \
  --thin-app "$EXISTING_PREPARED_THIN_APP" \
  --fixtures "$AUTHORED_RICH_FIXTURES" --supervised-process \
  --output "$PWD/outputs/office-new-supervised-boundaries"
```

`--supervised-process` selects the actual runtime, whereas `--process-boundary`
below retains the earlier prototype. They are mutually exclusive. The diagnostic
observer records real spawn/ready/close events and returns the original child
objects; it supplies no replacement actors. Each run passes ten cases/seven PDFs,
eight Wasm opens, ten renderer closures and ten scratch-owner closures, with
no unresolved trace calls. Baseline/Thin peaks are 1,441,579,008/1,923,006,464 bytes
and 33 PIDs under the existing 3 GiB/zero-swap/one-CPU/128-PID cap. Only the HTTP
positive control connects over IP. Twenty failed NSS Unix-socket probes belong
to closed scratch owners; neither file nor IP access is exempted. The initial
postflight failure is retained rather than relabelled as acceptance.

This supervises processes; it is not a filesystem/network sandbox. The container
cgroup limits are diagnostic and are not installed per-job controls. Pre-ready
and simultaneous owner-loss windows, durable recovery, managed memory limits,
further faults, ordinary/sealed/installed staging and broader fonts/corpus/macros
remain. The earlier same-process Thin OOM remains valid. Full source/third-party
and public packaging gates are unchanged. Neither installed review is replaced.
[Evidence and exact source hashes](linux-process-seat-qualification-20261017.json).

## Retained memory and process-boundary prototype — October 17

[`retention-diagnostic.py`](retention-diagnostic.py) and
[`retention-probe.mjs`](retention-probe.mjs) compare two distinct real-provider
conversions in one process and two fresh processes, using the existing apps,
fixtures and the same bounded container profile below:

```sh
python3 -B release/office-rebuild/retention-diagnostic.py \
  --app "$UNSELECTED_DEFAULT_APP" --thin-app "$EXISTING_PREPARED_THIN_APP" \
  --fixtures "$AUTHORED_RICH_FIXTURES" \
  --output "$PWD/outputs/office-new-retention"
```

All four profiles/eight PDFs pass. `/proc` anonymous/RSS, main-thread JS/V8
statistics, thread counts and cgroup anonymous/file/kernel/current/peak usage are
retained. Closing/idle and forced GC are separately labelled; forced GC is a
diagnostic observation, not application behavior. Thin's native/anonymous memory
remains high with an approximately 14 MiB main-thread heap and the same 11 threads.
Its two fresh-process parent observations stay around 22 MiB anonymous memory.
Exact native allocator/JIT attribution is not proven by these samples.

[`process-converter.mjs`](process-converter.mjs) and
[`process-renderer.mjs`](process-renderer.mjs) form an explicit diagnostic seat
for the original provider; neither is an installed backend. Each child executes
the unchanged original entry once. Metadata is returned only after process close.
The child has the provider-owned nested `TMPDIR`; the parent removes it after
close, including cancellation. The IPC disconnect guard distinguishes normal
terminal completion from parent loss; a kernel-level production death guard and
full bounded/fault protocol remain separate requirements.

Run the full original contained case set with that seat explicitly enabled:

```sh
python3 -B release/office-rebuild/contained-boundaries.py \
  --app "$UNSELECTED_DEFAULT_APP" --thin-app "$EXISTING_PREPARED_THIN_APP" \
  --fixtures "$AUTHORED_RICH_FIXTURES" --process-boundary \
  --output "$PWD/outputs/office-new-process-boundaries"
```

Both engines pass ten cases each, with 14 PDF text/image checks, actual Wasm
startup cancellation and distinct uncached recovery, all temporary prefixes
absent, eight Wasm opens and ten closed renderers per engine. Peaks are
**1,418,690,560 / 1,948,413,952 bytes** at **3 GiB / zero swap / one CPU / 128 PIDs**;
PID peaks are 31. The full case set uses no forced GC. External-file/network
canaries remain untouched; only the calibrated driver IP call connects. This
prototype observes no NSS connects, while the preceding same-process run observed
two failed parent NSS calls. Known closed renderer attribution remains explicit
and does not permit converter IP/file reads. Six parser controls and the focused
source/notice/packaging cohort pass 42 Python tests.

The initial normal-disconnect exit70 and later NSS/scratch-validator issues are
retained. The corrected scratch check includes `libreoffice-kit-`; no attempt
passes merely by ignoring that directory. The original same-process Thin OOM
below remains valid. No cap increase or engine rebuild occurs. Current app,
compiled files, dependencies, GUI and owner services/data remain unchanged.
Production IPC/ownership/death/hang/timeouts/disposal, GUI/package/adoption,
font/corpus/macro and distribution qualification remain open.
[Evidence](process-memory-qualification-20261017.json).

## Contained external resources and memory refusal — October 17

[`contained-boundaries.py`](contained-boundaries.py) runs
[`boundaries-probe.mjs`](boundaries-probe.mjs) through the actual original
Office provider and public-source entry. It uses an unselected ordinary app,
the already prepared Thin app and the independent rich fixture directory:

```sh
python3 -B release/office-rebuild/contained-boundaries.py \
  --app "$UNSELECTED_DEFAULT_APP" --thin-app "$EXISTING_PREPARED_THIN_APP" \
  --fixtures "$AUTHORED_RICH_FIXTURES" \
  --output "$PWD/outputs/office-new-contained-boundaries"
```

Inputs must be private unlinked `outputs/` directories; output must be new.
Node 24.19.0 is taken from the verified app. The immutable builder image, Docker,
host strace/matching loader/libraries, Poppler and Liberation fonts must already
exist. No dependencies are installed. Probe source is snapshotted into the new
tree and mounted read-only. Trace tools are private diagnostic copies with
identities retained; they are not new release components.

Each retained container has **3 GiB memory, zero swap, one CPU, 128 PIDs**, a
256 MiB temporary filesystem, read-only root and input mounts, dropped capabilities,
no-new-privileges and an isolated network namespace. It exposes no owner profile,
document, service, display, GPU or host network. One live internal HTTP canary is
positively calibrated, so lack of document requests is not inferred merely from
network isolation. Outside-file canaries remain readable to the driver but are
not mounted into Wasm MEMFS. Ordinary operator-selected file reads retain their
existing contract; this is untrusted document-link testing.

The current engine passes ten cases and seven PDF text/image checks, actual
Wasm-startup cancellation, distinct uncached recovery and teardown. Both archive
limit failures have the expected invalid-document reason. The initial cancellation
fixture had reused cached bytes; that failure is retained and its corrected case
must observe a successful converter-thread Wasm open before aborting.

Scoped tracing pairs unfinished/resumed calls by thread identity. The baseline
has eight Wasm opens, zero converter canary-file reads and zero document HTTP
requests. Its one IP connect is the driver's HTTP control; two failed parent-only
container NSS Unix-socket lookups are explicit. Five automatic parser controls
reject missing observations, extra connections, converter canary reads and
unpaired calls. These tests are separate from real-engine evidence.

**The recorded command returns nonzero because ThinLTO fails the memory bound.**
The baseline peaks at **2,011,688,960 bytes / 20 PIDs**. The source-built candidate's
post-conversion usage rises through **1,337,466,880 / 2,148,909,056 / 2,678,329,344**
bytes, then its container is OOM-killed with exit 137 in the fourth document.
Successful baseline evidence stays in `progress.json`; failed Thin logs, trace,
inspection and completed-case progress remain. Both handles are verified terminal.
Do not repeat that unchanged failing run or increase its cap as qualification.
Retained-memory attribution is the next task.

No installed engine/sandbox, full macro/font/corpus/security, throughput benchmark
or public redistribution acceptance is claimed. Read-only owner postflight passes.
The installed/current entry and engines retain their existing original licences.
[Qualification](contained-boundaries-qualification-20261017.json).

## Rich document and original-GUI comparison — October 17

### Rich sheets/decks and newly saved files — subsequent checkpoint

[`rich-sheet-deck-gui-probe.mjs`](rich-sheet-deck-gui-probe.mjs) extends the DOCX
case below with XLSX/XLS and PPTX/PPT in the actual original GUI. Use a fresh
unselected diagnostic app containing the
[file-discovery correction](../../docs/HARNESS-FILE-REFERENCES.md#external-file-discovery-correction--october-17),
the same existing Thin engine and a new output directory:

```sh
node release/office-rebuild/rich-sheet-deck-gui-probe.mjs \
  "$UNSELECTED_THIN_APP" "$AUTHORED_RICH_FIXTURES" \
  "$PWD/outputs/office-new-rich-sheet-deck-gui"
```

All four formats pass. Actual isolated spreadsheet Workers preserve saved
formulas, cross-sheet values, literal formula-looking text, merged cells and
hidden-row metadata. The original grid shows both worksheets and is read-only.
Deck previews render three pages, exclude speaker notes and retain original zoom.
Each file is added externally after the previous preview, selected through the
original `@file` menu/chip, then closed in narrow fullscreen mode. Source bytes,
native history and synthetic request logs remain exact. Six actual browser
Workers terminate; Host preview/request counters return to zero. Screenshots
were visually inspected. Scoped kernel tracing verifies two Thin converter
opens plus one driver hash read, zero default Wasm opens or unresolved calls.

The retained initial attempts found the genuine stale file-index gap and driver
focus/async-cleanup timing assumptions; none counts as passing qualification.
The original search/menu source is unchanged. The passing diagnostic has zero
observed browser errors/unexpected HTTP destinations, no owner documents,
inference, installed/default engine update or new engine build.
[Qualification](rich-sheet-deck-qualification-20261017.json).

The following DOCX/provider and hosted-CI statements retain their earlier scope.

The [authored fixture generator](rich-office-fixtures.py) produces DOC/DOCX,
XLS/XLSX and PPT/PPTX using the existing isolated native exporter. Writer files
have three pages, headers/footers, tables, pictures, mixed fonts and accented/
Greek/euro text. Sheets have two worksheets, merged headings, multiplication,
SUM/cross-sheet results, hidden rows and literal formula-looking text. Three-slide
decks have columns, pictures, footers and notes excluded from normal export.
Native LibreOffice produces the fixtures; both preview paths use the actual Wasm
Office provider. No owner document is used.

```sh
mkdir -m 700 "$PWD/outputs/office-new-rich-fixtures"
/usr/bin/python3 -B release/office-rebuild/rich-office-fixtures.py \
  "$PWD/outputs/office-new-rich-fixtures"
node release/office-rebuild/compare-rich-candidate.mjs \
  "$UNSELECTED_THIN_APP" "$UNSELECTED_BASELINE_APP" \
  "$PWD/outputs/office-new-rich-fixtures" "$PWD/outputs/office-new-rich-comparison"
node release/office-rebuild/rich-office-gui-probe.mjs \
  "$UNSELECTED_THIN_APP" "$PWD/outputs/office-new-rich-fixtures" \
  "$PWD/outputs/office-new-rich-gui"
```

Use the already prepared current-GUI Thin candidate and a separate private
baseline app with the original entry/engine. Neither may be a sealed deployment;
read-only diagnostic wrappers are not deployable artifacts. Every output must be
new. Generation needs the existing x64/Debian LibreOffice/bubblewrap/Liberation
payload described below; it installs nothing. Comparison also needs Node 24.19.0,
locked Sharp and Poppler. GUI qualification needs Chromium and the root's locked
SDK. The original GUI/proof fixture source remains unchanged.

All six richer files pass the paired original-provider check across **16 pages**:
exact required text and exclusions, equal text/page/image/missing-font results,
unchanged source bytes, owned cache bytes and identical raw pixels at **96 DPI**.
The DOCX fallback reports the authored missing font in both engines. Rendered
sample Writer/Calc/Impress pages were visually inspected. Raw PDF hashes differ;
the comparison verifies text and rendered pixels rather than metadata identity.
The single sequential pair's timings are observations, not performance acceptance.

The separate actual original-GUI/Thin Host case passes the rich three-page DOCX,
header/footer text layer, original font details, zoom, reload, malformed-file
error/Retry/recovery, narrow fullscreen and close/cleanup. Native history and
the synthetic provider request log remain exact during previews. Scoped kernel
evidence confirms three converter descendant/thread opens of the source-built
Wasm, plus one driver identity-hash read, and zero default Wasm opens. There are
no unresolved target calls. This is not a whole-machine/network audit; the GUI
observer records zero errors/unexpected HTTP destinations. One authored seed is
used, with no real provider inference or document content submitted to a model.

That earlier GUI case is DOCX only; rich Calc/Impress GUI qualifies separately
in the subsequent checkpoint above.
Full custom-font/large-corpus/resource/security, complete source delivery/rebuild/
third-party coverage and promotion/rollback remain separate. Both installed MX
reviews and their data/services stay unchanged; public packaging remains refused.
[Qualification](rich-documents-qualification-20261017.json).

The preceding `90dd25ef` Linux SDK job passes; its full Debian validation remains
in progress at this checkpoint. This operator-diagnostics/documentation commit
uses the CI skip instruction to preserve that existing run. It changes no
compiled runtime, GUI or automatic test and claims no new-head/whole-workflow pass.

## Emscripten runtime source companion — October 17

[`collect-runtime-inputs.py`](collect-runtime-inputs.py) complements the verified
Core/source bundle below. It consumes the exact public Emscripten archive pinned
in [`emscripten-runtime-inputs.json`](emscripten-runtime-inputs.json); fetch that
immutable URL once and verify its SHA-256 before using it. The exporter performs
no network request, engine compile or installed update:

```sh
python3 -B release/office-rebuild/collect-runtime-inputs.py \
  --cache "$BUILT_CACHE" --producer "$TERMINAL_CONTAINER" \
  --source-archive "$EMSCRIPTEN_SOURCE_ARCHIVE" \
  --base-source-inputs "$VERIFIED_CORE_INPUTS" \
  --output "$PWD/outputs/office-new-runtime-inputs"
```

The actual companion retains **16 files / 33,604,823 bytes**: the full public
Emscripten source archive, eleven original notice/contributor files, the final
link response, language configuration and two explicit release overlays. All
**4,890 selected runtime/JavaScript/tool/third-party/root source files** match
public revision `b7dc6e5747465580df5984e723b9d1f10d8e804b`. Runtime library sources,
including musl and LLVM components, keep their original licence files. The Office
entry/engine remain MPL-2.0; runtime components retain their own notices.

The public Git version file says `4.0.10-git`; the installed SDK uses quoted
`4.0.10` and a revision stamp. The pinned SDK installer explicitly rewrites the
release version. Those exact installed overlay bytes are retained separately;
this difference is not treated as an unmodified source-file match.

The retained final response names **15 system-library archives and one startup
object** whose current bytes match the recorded inputs. This establishes link
inputs, not per-symbol attribution after optimization. All three Core submodule
directories are empty in the completed producer. Its actual configuration omits
help/dictionary build types and bundled dictionaries, with only en-US selected;
those submodules supplied no source inputs for this build.

Ten new cases plus the preceding source/Office/notice/packaging checks pass
**34 Python tests**, no skips. Independent postflight verifies all **139 files**
across both exports, the runtime source hashes, original notices, link inputs and
release overlays. Neither source export is selected as an engine or public binary.
[Evidence](runtime-inputs-qualification-20261017.json).

Complete source-delivery/rebuild and third-party coverage review, representative
documents/fonts/resource/security and installed promotion/rollback remain open.
The public Office packaging refusal is unchanged.

## Completed-build source and notice export — October 17

[`collect-source-inputs.py`](collect-source-inputs.py) exports the already completed
ThinLTO diagnostic's source inputs to a new private directory. It checks the exact
terminal producer, engine assets, Core/Emsdk revisions, source diff and resource
drivers before copying anything. No builder restarts, engine adoption, network
fetch or model request is involved. Two small read-only/no-network XSLT containers
use the pinned builder image to reproduce the original generated licence files.

```sh
python3 -B release/office-rebuild/collect-source-inputs.py \
  --cache "$BUILT_CACHE" --producer "$TERMINAL_CONTAINER" \
  --output "$PWD/outputs/office-new-source-inputs"
```

The actual corrected export contains **123 files / 661,286,937 bytes**: committed
Core/Emsdk snapshots, the exact separate Core patch, 65 external files verified
against Core's `download.lst`, 59 unpacked-source receipts, recipe/resource/build
inputs, and the generated `LICENSE`, `LICENSE.html` and `NOTICE`. Both generated
licence files reproduce byte-for-byte using the actual build configuration.

An initial export used `git archive`, which honours Core's `export-ignore` and
omits tracked schema sources. Its directory/log and the failing authored regression
are retained. The corrected exporter streams Git blobs directly. Independent
inspection verifies all **149,173 Core files, including 58 schema files**, and all
**138 Emsdk files** against their committed Git object IDs. The exported patch
applies to restored original files and reconstructs all **33 modified Core files**
exactly. Source/default/installed engines and the completed build remain unchanged.

The new eight-case source-export suite plus existing Office/private-public notice
and packaging checks pass **24 Python tests**, no skips. Shell/Make evaluation,
unsafe identities/paths, linked inputs, changed sources and existing outputs refuse.
Committed source survives export-ignore; generated/uncommitted files are excluded.
[Qualification](source-inputs-qualification-20261017.json).

This is a verified **input export**, not a claim of complete corresponding source
or public distribution approval. Three Core gitlinks are explicitly excluded and
recorded. Emscripten runtime/toolchain source and notices, submodule scope, complete
rebuild/source delivery, representative documents/fonts/resource/security and
installed promotion/rollback remain separate. The public Office gate stays intact.

The repaired low-optimization **full-LTO** attempt is now terminal: exit 1,
OOMKilled=true, exact **8 GiB** peak/zero swap at final link. Its failed tree is
retained. The separate [ThinLTO driver](run-thin-lto.sh) requires a **fresh Core
build directory**, emits a verified LLVM ThinLTO summary and retains normal
`-Oz` optimization. The actual standalone probe returns 42 and resolves the
pinned Emscripten `thinlto` sysroot. Full-LTO objects are not reused.

A first ThinLTO configure fails because global compiler flags included link-only
options under a strict C++ check. The [additional MPL-2.0 build patch](thin-linker-resources.patch)
puts one-thread/cache controls in the Emscripten link rule. Its initial placement
conflicted with an earlier patch's reverse-check context; that failed tree is
retained. The final appended rule passes **all 18 original reverse checks and its
own reverse check** before launch. All original 39 recipe/source files are retained;
the copied experimental recipe adds this one public patch. Its preferred source
change is explicit. No warning check, module, format, runtime thread/memory policy
or application dependency is removed. The final fresh attempt now completes
**compile and package**, exit **0 / OOMKilled=false** at **09:01:32 UTC**, with
**6,951,043,072-byte** cgroup peak under the unchanged 8 GiB/zero-swap cap,
two CPUs, one job/nice 15 and no network. Six actual authored formats through
the original provider match the pinned engine's text, pages, missing-font sets
and all ten pages' raw pixels at 96 DPI. This is basic diagnostic output parity;
representative documents, fonts/performance/security, source/notice distribution,
GUI candidate integration, platforms and public redistribution remain unqualified.
[Exact evidence](thin-engine-qualification.json),
[owning guide](../../docs/HARNESS-OFFICE-PREVIEWS.md#fresh-thinlto-engine-build--october-15).

## Inspect a completed ThinLTO build without changing the app

Use the exact Node **24.19.0**, locked source dependencies and a fresh direct
child of this checkout's ignored `outputs/`. `UNSELECTED_APP` must be an ordinary
private app under `outputs/`, with the current default engine/entry identities.
`BUILT_CACHE` is the retained successful driver's `/office` mount source;
`TERMINAL_CONTAINER` identifies that exited successful builder. These commands
do not restart the builder or use an owner profile:

```sh
node release/office-rebuild/prepare-thin-candidate.mjs \
  "$UNSELECTED_APP" "$BUILT_CACHE" "$TERMINAL_CONTAINER" \
  "$PWD/outputs/office-thin-new-candidate"
node release/office-rebuild/compare-thin-candidate.mjs \
  "$PWD/outputs/office-thin-new-candidate/app" "$UNSELECTED_APP" \
  "$PWD/outputs/office-thin-new-comparison"
```

The builder requires terminal exit 0/no OOM, complete package receipt, pinned
builder/resource/driver/patch/source identities and exact output hashes. It
clones only `dist`, `node_modules`, Node and package manifests, retains MPL and
supplier notices, and gives both experimental engine and entry explicit own
versions. Their preferred source and resource profile are included; the source
closure for public distribution is still a separate gate. Existing outputs and
sealed bases are refused before writes. Failed diagnostic trees are retained.

The comparison runs each original provider in a separate process and uses the
same authored inputs for both. It needs Python/LibreOffice fixture generation,
Poppler (`pdftotext`, `pdfinfo`, `pdftoppm`) and the root's locked Sharp. It
checks exact input bytes/cache ownership/font notices and 96 DPI pixel parity;
`comparison.json`, PDFs and PNGs remain private for inspection. The lower-level
`source-entry-probe.mjs` keeps its default entry mode; `--thin` is explicit and
`--fixtures` copies only the six named authored inputs for paired tests. No
claim of a speed improvement follows from one short diagnostic run.

## Earlier experiments and default entry

The separate [low link-optimization driver](run-low-lto.sh) retains full LTO and existing Wasm runtime/thread/memory flags, but explicitly sets `--lto-O0 --lto-CGO0` alongside the existing one-thread controls. A small authored Wasm function compiles, executes to 42 and shows both flags exactly once in the pinned real linker invocation. The full source attempt uses a separately copied failed cache, the same **8 GiB/zero-swap** cap, two CPUs/one job/nice 15 and no network. It is an experimental build profile requiring its own output, performance and source/licence qualification; it does not update any application dependency or public release gate. The first full attempt fails before link because ccache writes outside the writable mount. Its complete failed tree/logs are retained. The repaired driver uses explicit `CCACHE_DIR`/`CCACHE_TEMPDIR` beneath `/office`; a separate copied cache reaches the real final linker, where both optimization flags and unchanged runtime memory/thread/table/entry flags are verified. The [environment record](environment.json) records the point-in-time process state, not a presumed build success. The source-built entry and public engine gate remain unchanged.

The October 15 default entry is [built from complete public source](../../packages/runtime/vendor/office-entry/BUILDING.md) as `@augmentor/office-entry@0.1.3-augmentor.1`. This replaces the opaque npm JavaScript entry; its default Wasm dependency remains unchanged. The earlier one-thread full-LTO **8 GiB** final-link retry OOMs (exit 1, exact cap, zero swap). The environment record retains all failed attempts separately from the successful ThinLTO diagnostic. Public binary approval remains open; no unchanged retry or memory-cap increase follows automatically.

[Admitted native actor completion](admitted-actor-completion.json) registers monitor/namespace identities before parsing, then verifies kernel exit/reaping before known-root cleanup. Final b3003bd source/ordinary 285-case and both original-viewer proofs pass; supplier/dependency/GUI and owner state are preserved. System Dash carries separate BSD/public-domain/GPL notice records. All-owner/durable/pre-ready/caller-PDF/full-native/distribution/OS and the preceding hosted Search GUI failure remain open; no promotion follows. [Owning scope](../../docs/HARNESS-OFFICE-PREVIEWS.md#admitted-native-actor-completion--october-15).

[Original-provider scratch ownership](provider-scratch-ownership.json) establishes an independent cleanup owner before authorized source copying, while retaining the MIT queue/cache and original GUI. At fc34230, focused 19/19 and both native viewers pass; source 281/282 retains a real guard-loss completion failure, ordinary 282/282 passes. Full qualification and promotion remain false; actor-completion, durable/all-owner and release gates remain. [Owning scope](../../docs/HARNESS-OFFICE-PREVIEWS.md#original-provider-scratch-ownership--october-15).

[Live-owner guard fault qualification](native-guard-drain.json) at edf50db closes stopped/killed guard admission stalls with direct Node supervision and broker death ownership. Source/ordinary 272-case and both original-viewer proofs pass; default/public/installed and full durable/crash/font/security/OS gates remain open. [Owning contract](../../docs/HARNESS-OFFICE-PREVIEWS.md#native-guard-loss-and-bounded-live-owner-drain--october-15).

[Independent native scratch guard qualification](native-independent-cleanup.json) at 8ce4334 adds actual owner/converter-group and stopped-tree recovery, with source/ordinary 270-case and both original-viewer proofs. It preserves the default engine/public gate; guard loss, durable/outer/caller-PDF recovery, fonts/security/native distribution and other OS mechanisms remain open. See [the owning contract](../../docs/HARNESS-OFFICE-PREVIEWS.md#independent-native-scratch-cleanup--october-15).

# Pinned Linux Office engine rebuild

This is a build environment and preparation record, not a qualified replacement
engine or public binary. The exact entry-package preferred source, a completed
engine build, actual output/conversion comparison and remaining notice/release
gates are still required. [Office qualification](../../docs/HARNESS-OFFICE-PREVIEWS.md#isolated-linux-engine-build--october-14)
records the current result. The original GUI and installed engine remain pinned.

The input is the **39 hash-verified source files** already shipped in
`@deepseek-ai/libreoffice-kit-wasm@0.1.5`. Its own scripts select LibreOffice
**bce0998afefdbc355585ca324285661a2170ba77**, Emsdk
**5eb0bde7585670252e8ba05e9d361627bffd08b5** and Emscripten **4.0.10**. Keep the
original MPL/MIT/third-party notices. These components are not relabelled MIT.

`Dockerfile` pins the Debian 13 base digest and installs the host build tools.
`host-packages-debian13.txt` records the actual package versions. Apt repository
contents can change: differing package versions require a new environment record.
This is not a claim of bit-identical image or engine reproduction. The earlier
Debian 12 definition/inventory are retained: GCC 12.2 fails Core's GCC >=13 check.
The successful preparation then uses GCC 14.2 with a fresh build directory.

## Reproduce in a fresh private directory

From this checkout after the locked npm dependencies are prepared, first validate
all real supplier files with the existing identity verifier:

```sh
python3 - <<'PY'
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('office', 'scripts/office_engine.py')
office = importlib.util.module_from_spec(spec)
spec.loader.exec_module(office)
office.validate_inputs(Path.cwd())
PY
```

Provide Node **24.19.0** for this Linux x64 trial and record its actual hash.
Create an empty cache on a filesystem with build space; do not use a selected
release, an existing source checkout or a RAM-backed temporary directory:

```sh
mkdir -p outputs
office_build_root="$(mktemp -d "$PWD/outputs/office-rebuild.XXXXXX")"
mkdir -m 700 "$office_build_root/tools" "$office_build_root/home" "$office_build_root/image-context"
cp -a node_modules/@deepseek-ai/libreoffice-kit-wasm/sources "$office_build_root/recipe"
cp -L "$(command -v node)" "$office_build_root/tools/node"
test "$("$office_build_root/tools/node" --version)" = v24.19.0
sha256sum "$office_build_root/tools/node"
docker build --file release/office-rebuild/Dockerfile --tag augmentor-office-rebuild:local "$office_build_root/image-context"
docker run --name augmentor-office-rebuild-local --init --read-only \
  --cap-drop=ALL --security-opt=no-new-privileges \
  --cpus=2 --memory=6g --memory-swap=6g --pids-limit=1024 \
  --user="$(id -u):$(id -g)" --workdir=/office \
  --env HOME=/office/home --env LANG=C.UTF-8 --env LC_ALL=C.UTF-8 \
  --env PATH=/office/tools:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  --env GIT_CONFIG_NOSYSTEM=1 --env GIT_CONFIG_GLOBAL=/dev/null --env GIT_TERMINAL_PROMPT=0 \
  --mount "type=bind,src=$office_build_root,dst=/office" \
  --tmpfs /tmp:rw,nosuid,nodev,size=536870912 \
  augmentor-office-rebuild:local /bin/bash -c '
    set -euo pipefail
    umask 077
    node /office/recipe/scripts/checkout-wasm.mjs
    for stage in prepare verify configure compile package; do
      nice -n 15 node /office/recipe/engine/wasm-source/build.mjs \
        --stage "$stage" --source /office/recipe/.build/wasm/core \
        --emsdk /office/recipe/.build/wasm/emsdk --build /office/build \
        --tarballs /office/tarballs --output /office/dist --jobs 1
    done'
```

The reviewed trial fetches the same pins directly into `/office/core` and
`/office/emsdk`; its fresh second build is `/office/build-debian13`. These paths
are container-local, so the supplier's no-whitespace path restriction is met even
when the host checkout has spaces. Path/environment differences are captured by
the supplier build identity. The trial's one-job/two-CPU/6-GiB limits are a local
resource profile, not acceptance of upstream automated-release resource gates.

Retain failed logs, directories and container identity. Inspect actual container
state and the build receipt before resuming; a timeout alone does not establish
termination. Use a fresh build directory after compiler/environment changes.
The supplier refuses changed input or incomplete output identity. No copied
prebuilt `soffice.wasm`, changed approval label or successful configuration can
stand in for a successful compile receipt. Keep generated source, toolchain,
external archives, logs and binaries outside Git; publish only reviewed evidence.

The October 14 Debian 13 trial passed configuration and reached final `soffice.js`
linking, but `wasm-ld` received SIGKILL and the container exited 1 with
`OOMKilled=true` under the 6 GiB limit. That profile is insufficient for the
observed final link. Keep its failed state; assess available host resources and
record a separate resource profile before any resumed attempt. No engine receipt
or conversion/rendering comparison is qualified.

## Controlled final-link experiment — October 14

`run-thread-limited.sh` resumes verify/compile/package in a **separate copy** of
the configured Debian 13 trial, preserving the failed original tree and the same
container-local `/office` paths. The driver expects `core`, `emsdk`, `recipe`,
`tools/node`, `tarballs` and `build-debian13` under that private root. Copy these
inputs with their original paths before invoking it; do not run it in a selected
application or the original failed-build directory. Mount the reviewed driver
read-only in the same pinned container, with the preceding CPU/RAM/swap/PID caps.

The actual pinned linker reports **LLD 21.0.0**. `EMCC_CORES=1` and
`BINARYEN_CORES=1` limit compiler helpers; `EMCC_CFLAGS` explicitly forwards
`-Wl,--threads=1,--thinlto-jobs=1` to native `wasm-ld`. Full `-flto`, runtime
Pthread pool and memory flags remain unchanged. Debug intermediates go to disk.
The driver records these extra resource flags separately because the supplier's
existing build identity does **not** capture them. Never infer byte identity or
public approval from that original identity after adding flags.

A tiny authored C++ probe first compiles and runs with both native flags. The
actual full-engine relink also receives both flags, but exits **1 / OOMKilled**
at **18:20:29 UTC**, with a **6,442,450,944-byte** cgroup peak, exactly its limit.
Both original and controlled failures remain retained. Reducing linker threads
alone does not qualify a 6 GiB build or solve the missing preferred-entry source.
See the [environment record](environment.json) and
[Office guide](../../docs/HARNESS-OFFICE-PREVIEWS.md#controlled-linker-resources--october-14).

## Native sandbox feasibility probe

`native-sandbox-probe.py` is an independently authored **Linux x64 diagnostic**,
not a shipped Host helper, automatic fallback or qualified replacement engine.
It requires already installed Debian-compatible LibreOffice Writer/Calc/Impress,
bubblewrap, Liberation fonts, fontconfig, liblangtag, Python 3.13 and Poppler.
It installs no package and refuses an existing output directory:

```sh
python3 -B release/office-rebuild/native-sandbox-probe.py \
  --source-ref "$(git rev-parse HEAD)" \
  --output "$PWD/outputs/native-office-new-attempt"
```

The script creates independent flat ODF fixtures, exports all six required Office
formats, then reads actual converted PDF text. Each command gets fresh private
profile/home/cache directories, a read-only input and bounded read-only system
payload, dropped capabilities, cleared environment and separate network/PID/user
namespaces. No owner home, GPU, display, DBus, service, model or personal document
is exposed. The fixed payload is deliberately x64/Debian-specific; a different
architecture or filesystem layout needs its own adapter qualification.

Synthetic negative checks cover outside-file/host-environment/process/loopback
access, read-only input/system files, bounded Liberation font availability and
owned-process cancellation at startup and after export dispatch. A 1,200-pixel
image at two inches tests actual 192 DPI PDF downsampling. Host deadlines,
per-process address-space/CPU/file-size limits and disabled core dumps bound the
experiment. Those limits are not a full engine cgroup or production archive,
aggregate scratch, admission and font-contract qualification.

Retain failures and their private diagnostics. The cancellation observer walks
children of every thread in the **owned** tree; a main-thread-only list misses
LibreOffice's worker-thread child. No unrelated processes are enumerated or
terminated. Generated profiles/documents/PDFs stay outside Git.

The original MIT GUI/provider/queue and pinned kit/Wasm remain unchanged. Native
integration still requires complete authorized-read/error/queue/cache/font/ZIP/
timeout/disposal semantics, macro/external-resource negative cases, complex
layout and original-GUI proofs, dependency/source/notice packaging and explicit
platform gaps. LibreOffice and its linked dependencies retain their own licences.
The [owning Office guide](../../docs/HARNESS-OFFICE-PREVIEWS.md#native-linux-office-feasibility--october-14)
records exact-source results; this diagnostic never relaxes the packaging gate.
