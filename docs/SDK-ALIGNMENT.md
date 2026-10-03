<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->
# Application SDK alignment — October 3, 2026

This source candidate extends `augmentor-app/1` without replacing its DSH
contract. It pairs with SDK `0.1.0-preview.4` source in the separate public
[SDK repository](https://github.com/ManoloRemiddi/augmentor-app-sdk). Neither
source publication nor a passing fixture deploys a customer installation.
The two recorded live apps retain their reviewed preview 2 package and runtime.

## Capability and settings ownership

`services/workspaces/sdk.json` advertises available adapters. Before initialization,
`workspace.describe` identifies the registered profile and harness and returns
`capabilitySchema:1`, platform, exact granted tool names, experimental voice state
and a `features` dictionary. Recognized states are supported, disabled, denied,
unsupported and unknown. `readinessVerified:false` is intentional: the descriptor
and API do not certify inference, OS consent, microphone availability or a running
memory engine. No microphone/model probe occurs during discovery.

Desktop/computer tools require explicit exact-name grants, a supported product
backend, an image-capable model and fresh OS consent/target authority. An
advertised API is not a grant. Dictation administration, shared setup, prompt
editing and memory configuration remain installation-owned. Handy is system
transcription into the focused application, separate from optional experimental
Resonant conversational voice. No cloud speech provider is added.

The maintained Browser settings hide shared installation sections for SDK
workspaces, retain workspace appearance and voice opt-in, expose read-only
workspace memory context, and direct prompt administration to standalone
Augmentor. The shared prompt-improvement action is unavailable in app workspaces.
Model settings show the current model and refer to the chat picker; shared
connection editors and provider checks remain in standalone Augmentor. Appearance
help reflects workspace-local storage rather than promising a desktop-wide change.
Standalone settings behavior and the developing native settings redesign are
separate. New shared management routes must be assessed against the workspace
policy before exposing them through the embed.

## Codex application adapter

A Codex profile requires an explicit existing connection ID, role files,
registered application directory, declared tool names and stable memory identity.
Installation writes the workspace registry transactionally and does not compose
or require a DSH preset. Silent harness/connection/role-directory and memory
identity migration is rejected; switching requires an explicit migration design.

`CodexWorkspaces` loads a trusted tool module's `applicationTools(config)` export:
`{tools:[{name,description,inputSchema}],execute(name,args,execution)}`. The SDK
supplies the same input/output validator and private backend client for DSH and
Codex. Execution carries the actual owning session, native stable call ID and
AbortSignal. The app backend remains responsible for revisions, receipts,
uncertain outcomes and any required external-send authorization.

The product forces workspace identity and connection, filters lists, verifies
ownership before history/prompt/cancel/branch/attach, scopes saved chats and
binds memory to the registered person/project. Role instructions and tool
catalogs persist with the conversation. Current registry grants are checked at
each execution, including already-open workers.

Native Codex shell, filesystem editing, web search, image-generation, delegation
and goal tools are disabled in app workers. Only registered application tools
and explicitly granted compatible product tools are advertised. Core
`request_user_input` remains an owner interaction. This is qualified against the
pinned `codex-cli 0.159.2` catalog with synthetic Responses; upgrades require the
same qualification. It is not an OS sandbox for installed JavaScript, a live
provider test, subscription eligibility or a Windows Codex implementation.
Codex's upstream experimental dynamic-tool contract is described in the
[official app-server guide](https://developers.openai.com/codex/app-server).

## Platform bootstrap and service lifecycle

The SDK uses the selected managed descriptor on Linux. Mac/Windows installed
artifacts expose `scripts/app-sdk-runtime.py --describe`; it reads the artifact
contract/bundled binaries and returns platform/configuration paths without
starting services or reading credentials. Mac defaults use Application Support.
Windows discovery verifies the OS local-app-data folder, rather than granting
identity based on environment strings. An explicit installed runtime root is
available for nondefault bundle locations. Old compatible Linux descriptors
remain supported; unsupported platforms cannot use that fallback.

`app-sdk-launch.py native|register|embed` reuses the product's component
configuration and lifetime lease. Windows supervision uses the existing
kill-on-close Job adapter; closing a client cannot leave its owned native bridge
range behind. It does not terminate the shared conversational host. Private
registration credentials/directories use the product Windows ACL adapter.
Windows DSH workspace files inherit their protected owner-only parent ACL.
Windows Codex fails closed before registration because its shared host IPC is
not qualified there.

`scripts/install-embedding.py --plan` performs read-only startup inspection.
Explicit installation uses Linux systemd, Mac launchd or Windows user Startup
with a hidden owned launcher. Windows Startup starts at login and does not
provide service-style crash restart; Linux/Mac restart through their managers.
The startup paths follow the normal selected Linux launcher or stable installed
Mac/Windows app location. Existing different startup files are preserved, and
installation does not silently replace/restart a live embedding service.

An embedding service holds a runtime lifetime lease. Before replacement/removal,
finish dependent application work and stop its owned startup service/range;
follow the product's normal maintenance/update process. Closing one app must
not stop the service used by other apps. App grants and model/voice settings
are not widened by bootstrap. A future native-runtime selector must update this
adapter in the same change; do not infer distro qualification from generic paths.

## Evidence and release gates

Local Linux source evidence: TypeScript check/build, 507 root Node cases
(505 pass/two opt-in skips), 85 Browser cases, 828 native/Python cases
(36 platform/optional skips), four focused Python platform contracts,
and the packed SDK cross-repository proof. The full Node suite used an isolated
Qt interpreter; its initial four failures were missing QtTest, not waived
product regressions. The packed proof uses the actual SDK client, product native
host/bridge, private Codex IPC and pinned Codex binary with synthetic provider
responses and application tools. It verifies a completed tool operation is not
replayed, foreign session/shared configuration denial, grant revocation, native
shell denial and durable reopening. No owner credentials or real model requests
are involved. Later changes require rerunning affected checks.

Hosted platform contracts run Linux, macOS and Windows independently in
`.github/workflows/app-sdk.yml`. SDK CI additionally qualifies its packed
consumer on all three operating systems and uses an immutable paired product
source revision for the native integration proof. Pending hosted results are
not claimed as passed. Full product package/Browser/native workflows retain
their separate gates and artifact provenance.

The first hosted candidate `c583475` passed Linux contracts but failed the Mac
workspace-list fixture and the Windows startup-plan assertion. The Mac fixture
now uses its canonical temporary directory, matching installed profile loading;
the Windows check now parses the quoted command and compares its arguments,
rather than expecting unescaped Windows backslashes in a Linux systemd unit.
The assertions remain enabled on every platform. Passing local reruns do not
replace fresh hosted qualification. The SDK's Windows database cleanup ordering
is corrected separately in its owning repository.

The Mac follow-up reached all three registry/boundary checks, then failed its
engine case and retained an open local fixture server until the job deadline.
Fixture teardown now closes the owned host before removing its state and always
closes the provider server even if host cleanup rejects. This preserves the
original engine assertions and makes failure details observable; the cancelled
run is not passing Mac evidence. Fresh hosted engine/bundle checks remain required.

`scripts/app-sdk-bundle-proof.mjs` checks the actual packaged Mac/Windows bootstrap, private token,
transactional DSH workspace registration/role composition, native frame
description, shared-administration denial, explicit harness and natural owned
bridge exit. It uses synthetic files with no running harness/model or login
registration. Windows requires a disposable-runner opt-in; Linux can exercise
the source path locally. The normal bundle workflows run it before installed
application proofs and retain their seal/signature checks. This proves shipped
adapter presence and startup, not an app conversation or installed login service.

Customer Mac/Windows SDK installation, actual login/background-service behavior,
OS consent, physical voice, Codex account/provider acceptance and installed
upgrade/rollback remain qualification gates. The current public Windows preview
does not contain these new helpers and does not bundle Handy. Existing release
archives/tags are immutable. The owner's independent third app is untouched.
Pi and cloud voice remain outside this SDK extension.
