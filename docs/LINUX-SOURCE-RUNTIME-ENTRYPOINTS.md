<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Noble source runtime: artifact and launch contract

The `noble-cp312-x86_64-source-qt-voice` profile is a separate engineering
candidate for Ubuntu 24.04, x86_64 and `/usr/bin/python3.12`. It does not extend
support to Mint, Fedora, another Ubuntu release or another Python ABI. Existing
vendor/system runtime profiles and their identities remain separate.

The [source policy](../release/ubuntu24.04-python-source-qt-voice.json) locks the
independently rebuilt, derived **PySide6** wheel and source-built shiboken6 wheel.
The package retains the `PySide6` metadata identity, version and original wheel
bytes; it is not relabelled as PySide6-Essentials. Pygments, keyring, sounddevice,
ONNX Runtime and protobuf retain the existing Noble voice wheel records.

Two bindings are offline reviewed inputs. `download` requires them, the Qt tree
and derivation receipt already present; it can fetch only the other unchanged
PyPI records. The existing PyPI URL rule is not broadened. The generator wheel
and full producer SDK are not runtime inputs.

## Inputs and immutable preparation

The package input directory contains exactly the locked wheel filenames, plus:

```text
python-wheels/
  source-pyside-derivation.json
  source-qt/
    stage-inventory.json
    lib/
    plugins/
    qml/
```

The [native verifier](../scripts/linux-source-qt.py) pins the manifest and
derivation receipt to the actual reviewed reconstruction. The manifest binds
67 regular files, their sizes/hashes and 18 local SONAME links. It rejects extra,
missing, changed, duplicate or unsafe members, directory symlinks, special files,
hardlinked regular files and altered link targets. Verification completes before
system-Python/venv execution or runtime-store creation. An unreviewed
`LD_PRELOAD` or `LD_AUDIT` is refused before the system-Python ABI subprocess.

The runtime identity includes the native contract as well as the seven wheels.
Qt is copied into `<immutable-runtime>/qt/{lib,plugins,qml}` and verified again.
Preparation creates only a new final-path runtime; failure removes only that
new directory. A prior runtime or destination is preserved, not repaired.
Runtime receipts bind the native contract and complete file/link inventory.

## Entry points and native paths

One verified pre-exec environment supplies:

```text
LD_LIBRARY_PATH=<runtime>/qt/lib
QT_PLUGIN_PATH=<runtime>/qt/plugins
QT_QPA_PLATFORM_PLUGIN_PATH=<runtime>/qt/plugins/platforms
QML_IMPORT_PATH=<runtime>/qt/qml
QML2_IMPORT_PATH=<runtime>/qt/qml
```

It replaces ambient Qt/QML locations and excludes an external platform theme
or generic plugin request. It preserves display/session variables, application
`PYTHONPATH`, Node selection and the desktop's existing platform decision.
Only the import probe forces offscreen/software mode. Actual source bindings
retain their producer RUNPATH bytes; the native environment must therefore be
set before Python loads them.

Desktop launch, the runtime/Browser component wrapper, deployment preflight and
setup children use this same helper. The declared-runtime DSH user-service
command uses system Python and `run-component.py` before Node, so speech children
inherit verified paths and a package lifetime lease. Startup bootstrap remains
system Python. Source-profile staging preserves and verifies the original wheel,
Qt and derivation inputs before creating a candidate inventory.

The fast Node selector matches Python's native-plus-wheel identity. For this
profile it checks the native receipt/manifest and requires the exact pre-exec
environment. Full native file and import verification occurs at the cold Python
wrapper. This keeps periodic Node selection synchronous without launching a
second Python/import process on its event loop.

The import probe checks all eleven built bindings, exact PySide/shiboken/Qt
versions, managed origins in the venv, GI outside it, QML component creation and
mapped Qt/plugin/QML libraries under the verified prefix. It records source Qt
as managed Qt. The probe's explicit plugin/import-path replacement does not
establish full product rendering or desktop-session confinement.

## Package candidate and system closure

```sh
python3 scripts/package-debian.py --target ubuntu24.04-amd64 \
  --source-qt --wheelhouse /path/to/reviewed-inputs --out /path/to/new-candidate
```

This opt-in builds an unqualified candidate. The default Noble vendor profile
and other package targets retain their existing recipes. The source option is
refused for another target before any build step. The package carries the finite
verified native inputs, not a builder venv/SDK. Wheel/native inventory and artifact
review account for that payload separately; they do not permit arbitrary new ELF
files in the application tree or certify corresponding-source/license coverage.

The separate dependency recipe explicitly supplies system **ICU 74**, rendering,
image, TLS, Wayland and XCB libraries. It does not claim the vendor wheel's ICU 73
notice collection covers this system dependency. System packages retain their
distribution-provided licenses and source obligations. The complete bundle also
copies the native-contract helper used by its distribution validator.

## October 2 actual evidence and limits

[The actual report](../release/qualification/next-targets/20261002-noble-source-runtime-entrypoints.json)
records a fresh pinned-public-base container with 374 installed package rows,
no compiler/CMake, UID1001, no network/devices/host mounts, Docker init, two CPUs,
2GiB memory, 256 PIDs, dropped capabilities and no-new-privileges. Its build
uses the runtime recipe, not the reconstructed 410-package compiler image.

Actual offline preparation verifies a 1,768-file/link environment. All eleven
bindings import; the probe maps fourteen Qt libraries and the offscreen platform
plugin under its own prefix, creates a QML component, and retains the speech and
GI/GTK/GStreamer/Atspi/Secret Service dependencies. Separate `ldd` checks resolve
all 57 native Qt objects without missing dependencies; ICU is 74.2-1ubuntu3.1.

The [public owned-fixture proof](../release/prove-noble-source-runtime.py) runs
the real setup, cold Browser selector, startup installer with service enabling
disabled, deployment preflight/stage/activate/rollback and desktop launcher.
The desktop launcher captures a real offscreen preview. Qt-library corruption
is refused before the component executes; prior receipt/selection bytes remain
unchanged and the restored native inventory verifies. This is a source artifact
entrypoint proof, not an installed complete-product qualification.

The initial root ownership change after Docker cp failed because the restricted
fixture has no CHOWN capability. It was preserved, then the same inputs were
extracted into a fresh home directory by the ordinary user; no capability was
added. Both actual proof scopes/source hashes and later checks are retained in
the report. Local full Node attempts with missing test prerequisites are recorded
as failures, not passes; hosted checks must qualify the committed source.

Full package installation/upgrade, matching DSH and live model/speech, native
Wayland/xcb, GNOME/KDE consent/control, graphical Browser, physical audio,
minimum CPU, complete compiled-file notices/source delivery/replacement and legal
acceptance remain open. All source/runtime/release flags stay false. The
[22-file license proposal](RECIPIENT-SOURCE-CONTROLS-LICENSE-PROPOSAL.md) remains
pending; no license grant changed. See [source/rebuild evidence](LINUX-LGPL-SOURCE-RUNTIME.md)
and [the full five-point rollout](LINUX-DISTRO-ROLLOUT.md).

## Root-owned package input permission correction

The first clean42f065a private source-runtime package builds and verifies67
native files/18 links, seven wheels/19 wheel ELF members and original notice
bytes. The byte/notice review did not establish installed-user readability:
actual Debian metadata shows the source-Qt input directory owned by root with
mode0700. That candidate is explicitly unqualified for ordinary-user preparation;
[the preserved failure](../release/qualification/next-targets/20261002-noble-source-package-permission-failure.json)
records exact artifact/metadata/refusal identities.

The builder now normalizes only the finite verified **packaged inputs** to
0755 directories/0644 files. Private immutable user runtimes remain0700. Artifact
review checks root ownership, user read/traversal permissions and absence of
world-writable regular files/directories; Linux symlink mode bits do not control
access, while the finite verifier owns their exact local targets. Fourteen source
payload/path/permission synthetic cases pass. A new clean artifact and actual
ordinary-user package installation proof are still required. No failed candidate
was activated or promoted; source entrypoint evidence above retains its original
actual tool/source hashes.

## Installed ordinary-user acceptance of clean7b6df59

[The installed-package report](../release/qualification/next-targets/20261002-noble-source-package-startup.json)
records matching clean7b6df59 runtime/desktop packages and their exact hashes,
source/native contract and notice review. The corrected package input permissions
pass artifact review, then an actual fresh image configures Runtime before Desktop
and satisfies both package identities. A separate normal-user, offline container
runs the installed `/usr/lib/augmentor` code with no host devices or mounts.

Actual setup prepares the root-owned inputs as UID1001 into the private immutable
runtime; repeat preparation preserves its receipt. The cold component wrapper
checks the installed package lifetime lease and selects the same Python in runtime,
platform and Browser. The installed desktop launcher captures an offscreen preview.
All eleven source bindings import; owned synthetic text, SVG red pixels and plasma
component creation pass, with all fourteen mapped Qt libraries inside the runtime.
The real installed CPU VAD processes64 synthetic frames with deterministic reset,
finite probabilities and one intra/inter thread; no microphone, TTS or live model
service is used. This does not establish minimum CPU or complete speech acceptance.

The [exact installed probe](../release/probe-installed-noble-source.py) intentionally
requires the dated clean7b6df59 package identity and marked UID1001 fixture. The
[recipe](../release/noble-source-package-fixture.Dockerfile) uses the previously
verified local runtime-fixture image; verify its image identity against the report
before building. It is an installed-package fixture, distinct from the source-only
fixture above. The local image-ID registry-reference failure, combined `dpkg`
Pre-Depends refusal and first probe's incorrect QML path are retained. The QML path
was corrected in a separate probe/output; no installed app source was patched.

Upgrade/removal, matching live DSH/model/full speech, native Wayland/xcb and
GNOME/KDE sessions, graphical Browser, physical audio, compiled-content notices,
recipient source/replacement delivery and license/public-release acceptance remain
open. All five rollout points remain active. Existing owner/guest selections and
model/GPU/audio settings remain unchanged; the22-file license proposal is pending.

Both tested7b6df59 hosted checks pass: [Linux37060945796](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37060945796)
and [Mac37060945741](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37060945741).
Debian13, Ubuntu26.04 and Fedora43/44 each run787 native tests:785 pass and two
Mac-only skips. The Node SDK suite runs517 cases:515 pass/two skips. These are
configured hosted source checks; they do not replace the separate installed Noble
fixture or establish its remaining native-session/product/license gates.

## Explicit recipient runtime selection: source candidate

The new [selection helper](../scripts/linux-recipient-runtime.py) is a source-only
engineering candidate for the existing Noble and Mint source-Qt profiles. It
does not change their official policy, wheel hashes, native manifest, preparation,
staging or stored Desktop selection. With no explicit recipient selection,
the original official verification applies. No modified Core, PySide or shiboken
build or real product entrypoint has yet been qualified with this new path.

An ordinary user can choose a separate private runtime at its final path:

```sh
/usr/bin/python3 /path/to/app/scripts/linux-recipient-runtime.py select \
  --app-root /path/to/app --official-python /path/to/official-runtime/bin/python3 \
  --recipient-root /path/to/separate-private-recipient-runtime
```

Selection intentionally executes the recipient's QtCore/PySide/shiboken version
probe after checking its files. Choose only code you intend to run. The runtime
must retain the official file/link set, interpreter links and every non-Qt/binding
hash. Only existing `qt/`, `PySide6/`, `shiboken6/` and their exact versioned
metadata-directory regular files may differ. The candidate must omit bytecode
caches: `-B` prevents cache writes but does not prevent Python reading an existing
unbound `.pyc`. Roots are private, user-owned ordinary directories; changed file
types, special files, hardlinks and writable file/directory metadata refuse.

The measured versions must remain Python3.12, Qt6.8.2, PySide6/shiboken6 6.8.2.1,
with QtCore and both bindings originating in that recipient prefix. This is a
finite compatibility gate; equal version strings do not establish that every
possible modification preserves ABI or application behavior. Actual marked
modified-library rebuilds and full Desktop/Browser acceptance remain required.

The separate `augmentor-recipient-runtime.json` binds the application absolute
root, exact `release.json` and Python policy bytes, official runtime receipt/hash
and lock identity, recipient inventory, executable and versions. It preserves
the official receipt and records recipient hashes independently. Normal native
package/deployment identity and lifetime guards still apply; these application
identity markers do not replace their full application inventory audit.

An exclusive fsynced selection under
`$XDG_DATA_HOME/augmentor/recipient-runtimes/selection-<app-path-sha256>.json`
pins that receipt. Each actual application root has its own explicit selection;
a native Browser root and a managed Desktop root require separate choices when
their roots differ. Receipt or app updates are refused, never silently adopted.
To retire a selection, including an app-stale selection, use:

```sh
/usr/bin/python3 /path/to/app/scripts/linux-recipient-runtime.py clear --app-root /path/to/app
```

Clearing removes only the private choice, preserving both runtimes. Selecting a
new modified inventory requires a new recipient prefix/receipt. No user UI,
models, settings, installed files or official artifact are rewritten by launch.

The shared `launch()` returns executable and environment together. Desktop
service/menu/shortcut launch, shell Desktop pre-exec, deployment import checks,
native Browser's leased component wrapper and embedded Browser apply that pair
before Python/Node starts. The component wrapper substitutes the verified
recipient Python for an official Python command argument. Node's fast selector
checks the exact selection/receipt/app/official-base identities and native paths;
it refuses a direct Node launch lacking the cold verified environment. Full
recipient byte validation and the bounded version probe occur in the Python
pre-exec guard, with changed inventory refused before recipient code executes.

Focused synthetic Python/Node cases cover fresh explicit choice, wrong versions,
malformed/stale/changed receipts, selection changes during validation, non-Qt and
link changes, unsafe metadata/cache bytes and actual shell launch routing. These
are source tests, not modified-library or installed-product qualification. The
[frozen 22-file license proposal](RECIPIENT-SOURCE-CONTROLS-LICENSE-PROPOSAL.md)
and root LICENSE remain unchanged; no permission or legal acceptance is inferred.

## October 4 recipient validation correction

[Hosted run 37199257072](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/37199257072)
failed four existing environment tests at bf6c50a after running 1,424 Python
cases (39 skips). Those synthetic fixtures still patched `resolve` after launch
moved official verification to `resolve_official`; the production verifier was
not replaced by their mocks. Both complete-proof and Mint fixtures now patch the
correct official boundary while preserving loader, inventory-refusal and
unchanged-environment assertions. All 85 related source checks pass locally.
Dependent package jobs were skipped in the failed run; fresh hosted validation
is required. Source tests do not qualify installed recipient replacements.

