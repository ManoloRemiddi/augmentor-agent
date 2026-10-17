<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Linux DSH integration installation

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
checks; this does not waive the public Office packaging gate.

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
