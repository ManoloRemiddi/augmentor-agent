<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Linux DSH integration installation

## Preserved custom integration stage — October 17

Source **3777cc92961fc3d21c84cf3a1390970fcea851cb** adds `scripts/stage-dsh-preservation.py stage` and `verify`.
They prepare and verify a private review directory; they do **not** install,
execute a profile, start/stop DSH, update launchers or modify an owner file.
Activation is deliberately absent from this command. It still requires an
immutable qualified incoming artifact, full cold backups, matching clients and
transaction/reverse acceptance; this preparation is not a replacement for them.

The stage binds the exact modern CLI/SDK metadata, original package provenance,
owned/active Browser code, peer edits, owned preset files, profile/settings/token
inputs and incoming integration bytes. An active compatibility Browser copy must
match the recorded owned code. Original package metadata must match the recorded
supplier hash; existing edits must be confined to peer dependencies explicitly
supporting the tested modern SDK. Those peer values are retained in the candidate
package while incoming public package metadata/version/code supplies the upgrade.
Unrecognized code, metadata or preset edits refuse rather than being discarded.

Custom YAML is parsed as bounded nodes only: no `!!js` construction/evaluation,
no YAML 1.1 value conversion and no full-document serializer. Only identified
owned module-name scalar spans are replaced. Comments, Unicode, prompts, custom
settings, `off`, expressions, Browser overrides and other plugins remain exact.
Aliased/duplicate/ambiguous structures refuse. Both existing declarative role IDs
must remain present. New preserved ownership records the deliberate migration,
not a forged historical insertion or reset of an edited-file checksum. Normal
setup refuses overwriting that ownership and requires another reviewed migration.

The output contains a candidate patch, small plugin files and a private plan with
concrete module edits, input/output hashes and retained module references. It must
be an absent directory outside the application/profile; output files are private.
`verify --sha256` checks the reviewed plan hash, staged assets and current inputs.
A changed profile, supplier, staged asset or newly created optional configuration
refuses. Partial output is removed only from the newly allocated owned stage;
existing output and all input bytes are preserved. Use the disposable build
workspace for rehearsal; do not retain another full application per checkpoint.

### Actual profile evidence and remaining graph qualification

The actual profile currently loads Browser code from a separate compatibility
folder. Its code matches the owned expected hash, and its package matches the
owned edited package; the original supplier package satisfies the recorded hash.
The actual preservation stage succeeds against **28 bound inputs**, proposes
**two module-reference changes**, and keeps peer settings exact. No real profile
is executed or owner file changed. The temporary stage is removed afterward;
small private plan/receipt evidence is retained outside GitHub.

The existing role definitions also reference **21 retained literal module paths**
across older/other adapter roots. They are preserved, not silently rebased to
unqualified replacements. Those dependencies and any dynamic expressions need
separate runtime/companion qualification before activation. The stage's input
checks are not whole-graph, model/tool, old-bank or historical acceptance. Existing
roots must remain available; no DSH retirement or original-project transfer occurs.

Focused **85 Python tests** pass: 11 preservation cases plus nine modern setup
cases and the existing setup/readiness/leases/deployment checks. Preservation
covers exact edits/peers/private output, actual CLI staging/verification, untracked
active code, non-peer edits, provenance/preset changes, aliases/duplicates, mixed
SDK/ranges, stale input/new credentials, tampering, links/overlap and late change
cleanup. New tests use independently authored profiles/code only. The Linux SDK
workflow now installs a hash-pinned PyYAML inspection wheel and runs these cases;
no new production dependency or binary publication is implied.
[Portable evidence](../release/harness-dsh-preservation-20261017.json).

Earlier Linux SDK **39042645605** succeeds at 0ca81395 / runtime 6a82cf82.
Earlier full validations **39041187997** (f640ce8c) and **39041724378** (14e3c523 /
runtime c6653b75) finish their application checks and fail at the retained **Office
public source/exact-engine-rebuild packaging gate**. Source-boundary/Home/component
jobs pass. Those are terminal results, superseding earlier live observations;
neither is restarted, and no whole-workflow/package approval is claimed. New
preservation source still needs its own hosted qualification.

## Modern setup qualification — October 17, 2026

Source **6a82cf8209a7e6783efba41b15d0d8c4282043b0** supports explicit existing DSH **0.2.0-rc.2** on Linux, alongside
the existing **0.1.5-rc.1** path. The complete-runtime download/install lock still
ships the legacy family; this change does not upgrade that lock or an owner service.
The CLI manifest selects the exact SDK family. Modern setup requires CLI/base/tools/
preset/preset-registry 0.2.0-rc.2, Cordis 4.0.4 and Schemastery 3.18.4. A missing or
mixed family refuses. The dependencies are rechecked between connection inspection
and installation. Modern setup is refused on macOS/Windows until qualified there.

The modern profile receives two declarative agent-preset registrations, preserving
the existing Linux/Browser role IDs and their common personal-agent composition.
Only the modern composition changes workflow-worker-thread to workflow-ptc; tools,
persona, compaction, memory, desktop/browser controls and enabled Ralph remain.
Legacy preset files remain owned/snapshotted, and legacy installation emits its
original composition. Package/model/provider/voice settings are not rewritten.

Existing profile text is retained byte for byte around the owned insertion. Setup
never evaluates custom YAML expressions or rewrites a reasoning key named `off`.
The owned insertion is replaced only if its exact ownership checks still pass.
Edited package metadata, preset bytes or owned composition are refused and left
intact. Existing external prompt-library integration is retained without adding
a second one. Interrupted owned updates restore the previous plugin and presets;
the integration token remains stable. These checks do not automatically migrate
the actual owner's hand-edited integration.

## Evidence

Focused **73 Python cases** pass; **18 overlapping setup cases** also pass with the
exact new Linux SDK workflow command after the final locator assertion. Eight
independently authored modern cases cover fresh install/reinstall, exact custom
text/token preservation, legacy-to-modern owned upgrade, changed/missing SDKs,
edited package/composition refusal, existing Prompt Library, rollback and platform
refusal. The SDK workflow now runs setup qualification on Linux before later Office
checks; this does not waive the public Office packaging gate. Manual SDK dispatch can use `platform=linux` for the
current MX scope; default/pull-request dispatch still tests the full platform matrix.
This Linux result cannot establish macOS/Windows readiness. Earlier f640ce8c SDK
run 39041187982 passes Linux, fails macOS on the existing unsupported import/export
path, and cancels Windows; those platform gaps are retained rather than waived.

A separate actual installed upstream **0.2.0-rc.2** CLI/base/tools/web-app test uses
current public source against a new authored profile. It installs, restarts,
registers both non-broken presets, creates both real owned roles, matches the
0.2.13 product handshake, and reads the selected authored shared prompt library.
After another cold restart both saved role histories retain every original event.
The only header difference is DSH's documented persistence default
`delegationDepth: 0` when that field was previously absent. The upstream persistence
writer explicitly uses that default; no history event is dropped or replayed.

All three traced process trees make **zero INET connect calls** during the bounded
proof with telemetry disabled, and no model request occurs. This proves fresh
role creation/blank-history cold read, not full historical sessions, tool execution,
model continuation or complete DSH feature parity. The owner's instance and profile
are never copied into the fixture. Only the small plugin install and authored data
live in the managed scratch workspace. Its two scoped test companion processes are
stopped at the end and scratch is removed. The guard correctly retained the first
attempt's scratch until those verified fixture-only processes were reaped.

The first real comparison exposed an incorrect test-library marker, then the
upstream header default. Both were investigated using authored evidence; the
source installer and history were not weakened to conceal them.
[Portable qualification](../release/harness-dsh-modern-setup-20261017.json).

## Existing owner installation

The actual installation has edited package peer metadata and custom modern
composition, so normal install must still refuse its automatic replacement.
Next prepare a deliberate backed-up migration retaining those edits, all current
role definitions, model/provider routing, plugins and settings; qualify matching
product/Browser clients and immutable artifacts before selecting anything.
Shared-store adoption then requires fresh full cold backups, the busy-work veto,
existing-bank/history/budget preservation, restart and reverse acceptance.

Both installed MX reviews remain unchanged; pilot feedback still gates additional
project transfers. Voice and other platforms remain deferred. See
[shared-profile adoption](HARNESS-SHARED-PROFILES.md),
[desktop deployment](DESKTOP-DEPLOYMENTS.md) and
[storage retention](HARNESS-BUILD-STORAGE.md).
