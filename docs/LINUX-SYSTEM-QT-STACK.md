<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Arch and Leap candidate Python/Qt drift boundary

Current-main integration additionally preserves the bundled dictation component
and its Debian dependencies alongside these runtime contracts. See
[the actual working-merge report](../release/qualification/next-targets/20261002-main-dictation-distro-integration.json).
The earlier runtime-only proofs below do not qualify that combined product;
matching dictation now has [actual native loader/startup evidence](LINUX-HANDY-NATIVE-CLOSURE.md).
Complete packages and full product/native-session/audio acceptance remain required.

The two existing system-Qt voice profiles now bind a separately reviewed distro
Python/Qt inventory into their immutable runtime identity. An existing runtime
refuses changed registered package versions, inventory, bytes or fresh import
results. Verification does not rewrite its receipt or repair the system.
This is a candidate cold-launch boundary. Full application packages and complete
install adapters for these targets are still absent.

The [actual checkpoint](../release/qualification/next-targets/20261002-system-qt-stack-runtime.json)
records working source based on clean `42c8c51`, exact executed file hashes,
ordinary UID1000 fixtures and retained raw evidence. It is not a clean installed
product qualification. Existing dated runtime-overlay and package-guard reports
remain historical evidence for their original policies and synthetic payloads.

| Target candidate | Python | Qt/PySide | Registered package scope | Verified members |
| --- | --- | --- | --- | --- |
| Arch 20261001 x86_64 | 3.14.7 | 6.11.2 | Python, PySide, shiboken and four Qt packages | 6,434 files, 170 links, 498 directories; 271,911,126 regular-file bytes |
| openSUSE Leap 16.0 x86_64 | 3.13.14 | 6.9.1 | 23 explicit Python/binding/Qt packages | 2,305 files, 24 links, 139 directories; 139,646,467 regular-file bytes |

The scope includes package-registered `/usr/bin`, `/usr/lib` and `/usr/lib64`
members, excluding bytecode caches. Headers, docs and unrelated dependencies
are outside it. This does not prove a coherent whole Arch repository snapshot,
complete native dependency closure, authenticated repository metadata or a
live dependency-maintenance boundary. Every manifest keeps those qualification
flags false. Native dependencies outside the selected package set can still
change without a file-hash refusal; fresh imports detect only observed changes.

## Policy, inputs and startup

[`linux-system-qt.py`](../scripts/linux-system-qt.py) queries installed package
identities and registered paths using fixed absolute package-tool executables.
It hashes regular files through no-follow descriptors, checks root ownership
and permissions, preserves exact links and refuses registration changes during
the walk. `LD_PRELOAD`, `LD_AUDIT` and `LD_LIBRARY_PATH` overrides refuse before
the query tools execute. The two finite package sets are explicit in the module.

Each policy's `systemQtStack` contract records the published inventory's exact
SHA256/size, manager and expected Qt version. The policy identity includes that
contract in both Python and Node. Noble vendor and source-Qt identities and
their loader behavior retain their existing contracts. Node now admits only the
two exact system profiles, host identities, ABI, wheel sets and native manifest
contracts. Its fast selector checks the private runtime receipt and import
versions, rejects loader overrides and leaves the full installed-package/byte
verification to the cold Python wrapper before exec.

Preparation verifies the pinned system inventory before the ABI/import child
Python executes, then creates a separate private runtime at its final path and
installs only the hashed offline wheels. It copies the manifest into that
runtime and verifies again before writing the receipt. Cold verification checks
the runtime inventory, system package inventory and fresh dependency/import
report against the saved receipt. Successful imports alone no longer allow
drift. The receipt's explicit `systemQtStack` must also match the policy.

Copy the matching inventory into a target wheelhouse as
`system-qt-inventory.json` before preparation:

```sh
# Arch candidate; use only its matching, separately provisioned fixture.
cp release/system-qt/arch20261002-inventory.json WHEELHOUSE/system-qt-inventory.json
python3 scripts/linux-python-runtime.py prepare \
  --policy release/arch20261001-python-voice.json \
  --wheelhouse WHEELHOUSE --store /absolute/new/private/runtime-store

# Leap candidate uses the explicit interpreter; /usr/bin/python3 need not exist.
cp release/system-qt/leap20261002-inventory.json WHEELHOUSE/system-qt-inventory.json
/usr/bin/python3.13 scripts/linux-python-runtime.py prepare \
  --policy release/opensuse-leap16.0-python-voice.json \
  --wheelhouse WHEELHOUSE --store /absolute/new/private/runtime-store
```

The new immutable identities are:

- Arch: `3f7167c59f5eed9fe7d24b51cc807219d57c85414bd8a1ca545d2860e94d6659`.
- Leap: `7991a5ef322dfa02aa228bbb36a4cde5ddc0673b02645d7ba4f0a5c3f5782bed`.

Do not migrate or edit old receipts to these identities. A changed package stack
requires a separately reviewed inventory/policy and fresh qualification. Do not
hold selected Arch packages back to preserve an old receipt: the
[pacman manual](https://man.archlinux.org/man/pacman.8.en) documents full upgrades,
dependency resolution and registered-package queries. Whole-system upgrade and
running-process protection need their own demonstrated maintenance contract.

## Actual owned-fixture evidence

[`prove-system-qt-stack.py`](../release/prove-system-qt-stack.py) accepts only the
two marked existing owned containers, UID1000 and a new confined proof directory.
It copies the verified wheels into new inputs, prepares a fresh runtime, reuses
the byte-identical receipt and verifies prior runtimes/receipts remain unchanged.
It changes synthetic expected-manifest copies to exercise real package-version
and same-version file-byte refusals; installed system files are never changed.
A modified receipt import report is refused, restored in `finally` and reverified.

The fresh Arch runtime has 890 members and the Leap runtime 919. Offline
preparation takes 3.023s/2.803s respectively; reuse takes 1.159s/0.781s in these
fixtures. These are fixture observations, not release performance promises.

Both pass synthetic QtTest text entry, SVG red-pixel rendering and QML component
creation. Fourteen mapped Qt libraries in each child resolve under `/usr`.
These offscreen controls do not prove native desktop sessions or plasma shader
rendering. Both execute the pinned Silero 6.2.1 VAD model
`1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3`
through the public `SileroVad` implementation: 64 synthetic frames, deterministic
reset, CPUExecutionProvider only and one intra/inter-op thread. This improves
the earlier 115-byte ONNX Identity proof; ASR/TTS, microphones, human speech and
minimum-CPU qualification remain open.

Eleven focused synthetic drift tests pass, alongside 14 runtime and 14 source-Qt
cases, four Node identity/refusal cases, the TypeScript check and build. The
checkpoint retains exact raw proof/log hashes. The final Arch native suite runs
798 cases:796 passes and two Mac-only skips. An earlier partial source refresh
left the old Qt permission helper and failed; that795-case attempt and corrected
797-case prior snapshot are retained separately. All release, installed-product,
dependency maintenance, licensing and embedded-source gates remain false.

## Actual Node and Browser selection

[The additional checkpoint](../release/qualification/next-targets/20261002-system-qt-node-admission.json)
records new UID1000 source-only fixtures based on `cbcce18`. Both execute the
actual cold Python wrapper and checksum-pinned Node24.19.0, then agree across
explicit/implicit runtime discovery, component environment and Browser voice
Python selection. Both refuse an explicit system interpreter, three loader
overrides and a modified native manifest; `finally` restores the manifest and
the runtime receipt stays byte-identical. This is discovery/verification evidence,
not Browser rendering, a microphone, installed product or package-lifetime lease.

Five focused Node cases include20 malformed policy variants across the two
profiles. TypeScript checking and compilation pass. An earlier private driver
used the wrong receipt key after successful Arch preparation; that attempt is
retained separately and the corrected proof uses fresh app/runtime paths.
[`probe-system-qt-node.mjs`](../release/probe-system-qt-node.mjs) records exact
compiled/source hashes and accepts only marked UID1000 source fixtures. Complete
installer/package/maintenance and recipient-source qualification remain open.

## Next complete-package work

Add explicit target contracts and generic declared-runtime checks to the complete
installer; use
Leap's `/usr/bin/python3.13` bootstrap in every generated wrapper. Build a
distinct Leap RPM and Arch application PKGBUILD with full target receipts and
matching policies/wheels/system inventory. Keep Arch's guard installed in its
own completed transaction before the application. Verify registration, inventory
and pending maintenance state independently of package-manager exit status.

Then qualify ordinary-user installed entrypoints, graphical Browser, credentials,
voice, package upgrades/removal/recovery and real GNOME/KDE sessions. The current
app-only lifecycle hooks do not protect a running application while the system
Python/Qt dependencies are replaced. The pending 22-file license decision and all
five rollout points remain active; this checkpoint grants no new license and
changes no owner selection, service, GPU, model setting or physical device.
