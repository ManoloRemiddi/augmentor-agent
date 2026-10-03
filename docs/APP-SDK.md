<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->
# Application SDK foundation

The separate `augmentor-app-sdk` repository supplies the developer package.
This repository owns the runtime contract `augmentor-app/1`, the maintained
Browser interface, workspace permissions, memory binding and installation.
The released baseline targets trusted single-owner applications on Linux using DSH.
[The October alignment source](SDK-ALIGNMENT.md) adds capability discovery, an
experimental Codex workspace adapter and platform startup/private-path adapters.
Its exact evidence and remaining release gates are owned by that guide. Pi,
multi-tenant hosting and cloud voice remain excluded.

## Connection and authority

An installed SDK profile declares `schemaVersion: 1`, `sdkProtocol:
"augmentor-app/1"` and an explicit policy. `workspace.describe` negotiates
the protocol, workspace and explicitly selected harness before the existing
product handshake. DSH remains the released default. The
product manifest `services/workspaces/sdk.json` is the discovery boundary;
clients must reject older runtimes instead of importing their internal code.

Sessions are still filtered and authorized by preset plus canonical cwd.
Memory remains bound to the workspace's existing person/project identity.
The DSH workspace plugin installs a final monotonic execution guard over exact
tool names. A cooperative allow hook cannot override denial. Missing guard API,
wrong session identity, incomplete installation or invalid policy fail closed.
Permissions are re-read before each tool call, so revocation affects existing
SDK agents. Introducing the plugin to a legacy profile requires a newly loaded
agent; already instantiated legacy agents are not retroactively sandboxed.

The guard restricts model-dispatched calls. Installed JavaScript has the OS
rights of its process, and authorized browser observation may expose the owner's
signed-in pages. This is not an OS sandbox or an untrusted plugin marketplace.
Application APIs remain responsible for ownership, validation, revisions,
idempotency and restrictions on sending/publishing. App context is evidence,
never a grant. SDK workspaces cannot modify shared permission settings, shared
prompts, runtime setup or other administrative surfaces.

## Installation and recovery

Run `scripts/install-workspace-profile.mjs profile.json` from the selected
compatible product. A global installer lock, before-image journal and per-profile
incomplete marker protect preset/profile/registry updates. A caught failure rolls
back all planned files. After a killed installer, run the same command with
`--recover`; it refuses while the recorded installer PID is alive. Recovery
restores the previous state. Private before-images are retained under the profile
directory's `.backups/`; they contain configuration and must not be published.

The installer rejects preset collisions, unregistered preset directories,
identity changes and accidental memory migrations. Existing data and histories
are not migrated or erased. It never restarts shared DSH or any UI. Preference
writes use a SQLite transaction as a process-owned mutex; their existing JSON
format remains canonical and a crashed process does not leave a stale lock.

## Experimental voice

SDK profiles default voice off. Their embedded Settings page exposes an
experimental workspace toggle, stored only in that profile's preferences.
The native boundary enforces it; reopen the panel after changing it to update
the loaded controls. The connection capabilities report the saved choice. Use
Stop to end an already active voice interaction before disabling future starts.
Resonant Voice still uses the host's audio devices and installed dependencies.
This adds no remote microphone, cloud provider or
guarantee of hardware/model availability. Global voice configuration remains
in standalone Augmentor.

## Qualification and release boundary

Run `node --test tests/workspace-sdk.test.mjs tests/workspace-embedding.test.mjs`
and `node scripts/workspace-sdk-dsh-proof.mjs release/dsh/node_modules/@deepseek-ai/dsh`.
The latter executes synthetic tools through real DSH/Cordis, proving grant/deny
behavior and isolation from unrelated agents without a model request.
The pinned DSH `0.1.5-rc.1` passes this proof. CI repeats it after locked install.
Tests additionally cover crash recovery, identity collisions, permission
revocation, shared-administration denial and preference locks after process death.

The shared JavaScript contract introduces no OS-specific behavior. Linux is the
qualified SDK installation target; these checks do not certify Mac installation,
native microphone behavior, real model quality or an independently built app.
The owner will build that third app independently. Fixtures and migrations of
YouTube workspace and Sponsor desk do not substitute for that adoption test.
Source, a staged artifact, the selected release and running processes remain
distinct. Follow [desktop deployments](DESKTOP-DEPLOYMENTS.md) for activation.
