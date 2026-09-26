<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

Mac setup update (26 September): current source has a separate
[managed runtime/model form](MACOS-MANAGED-SETUP.md) for fresh bundled desktops.
External DSH setup below remains available. Basic setup, chat and restart passed
an isolated real Mac/DSH fixture; the public signed app, additional plugins and
complete feature parity are not yet qualified.
# Feature ownership and compatibility · Augmentor 0.2.9 development

DSH personal surfaces now share the agent, tools and speech engine; see [shared surfaces and evidence](SHARED-SURFACES-2026-09-24.md).

Current source/ref and qualification: [agent handoff](AGENT-HANDOFF.md).
Dated candidate sections below retain their original version-specific evidence.

Release scope: DSH is the full-featured target; Pi is a supported subset.
Additional Pi extensions and Windows are deferred. The Linux evidence below does
not establish macOS feature qualification. See the cross-platform release ledger.

This maintained checkout is the development source for both surfaces. The legacy repository paths and launcher IDs remain compatibility locations. Do not develop another UI fork there.

| Feature | Shared owner | Linux Pi | Linux DSH | Browser Pi | Browser DSH |
| --- | --- | --- | --- | --- | --- |
| Prompt records, stable IDs, rename/delete, revisions | `services/prompt-library` | Yes | Yes | Yes | Yes |
| Prompt editing inside Augmentor | Shared service; one editor per surface | Yes | Yes | Yes | Yes |
| Literal `[clipboard]`, one snapshot, no automatic send | `packages/templates`, parity fixtures | Yes | Yes | Yes | Yes |
| Copy/check, labels, SVGs, 14px icons, 1500ms feedback | `packages/design`; generated bindings | Yes | Yes | Yes | Yes |
| Branch through a completed reply with real tool context | Shared DSH boundary / Pi SDK adapter | Yes | Yes, closed turn | Yes | Yes, closed turn |
| Edit latest input and resubmit on a child branch | Shared DSH boundary / Pi SDK adapter | Yes | Yes, closed turn | Yes | Yes, closed turn |
| Model selection, streaming, Stop, history | Common surface controller, engine adapter | Yes | Yes | Yes | Yes |
| Guided endpoint check, explicit save and approval mode | Pi setup / shared DSH integration; surface forms | OpenAI-compatible text/image check | Checked DSH integration; models configured in DSH | Same Pi check | Same DSH integration |
| Browser navigate/snapshot/type/click | Browser executor + harness tool bindings | — | Yes, connected extension | Yes | Yes |
| Consented desktop capture, click, keys and ASCII text | `services/desktop`; shared Pi/DSH tools | KDE Wayland preview | KDE Wayland preview | — | Same consented executor |
| Bounded desktop specialist with isolated context and evidence | `packages/computer-use`; Pi lifecycle adapter | Development preview; same selected image model | Unavailable | — | — |
| Optional manual memory library and data controls | Separate Hindsight 0.9.2 provider and tool binding | Yes | Yes | Yes | Yes |
| Automatic relationship/project memory | Hindsight 0.10.0 and transcript companion | Lifecycle fixture | Local adapter active | Lifecycle fixture | Shared adapter active; controls in source |
| Private support report preview/export | `services/support`; surface dialogs | Yes | Yes | Yes | Yes |

Additional current native/browser capabilities:

| Capability | Desktop | Browser |
| --- | --- | --- |
| Resonant Voice on DSH | Hold/release, slide-lock, voice selection; optional hands-free preview | Same shared engine: hold/release, lock, hands-free and primary voice settings |
| Independent second conversation | Named second window, separate chat/settings/voice profile; KDE shortcut | Separate sidebar/session workflow |
| Skins and activity animation | Futuristic plasma; Blossom lake/butterflies; validated import/export | Native skins are not applied to Chromium |
| Startup and recovery | Shared selected release, supervised login, guarded recovery | Matching companion and explicit extension load/reload |
| Complete fresh-user installation | Guided Debian 13 amd64 bundle with pinned DSH/plugins | Matching extension and native host in the same bundle |

See [complete installation](COMPLETE-INSTALL.md) for optional engine provisioning
and platform limits, and [the distribution audit](DISTRIBUTION-AUDIT-2026-09-20.md)
for the distinction between installed artifacts and source. Voice, acoustic
quality and memory quality remain separate from installer success.

DSH uses `services/dsh/branch.py` from both surfaces. Branch selects a final reply in a closed turn; Edit retains preceding turns, and editing the first input starts a clean child. Mid-turn replies and steered inputs that cannot be isolated are refused. Durable operation records prevent unknown fork outcomes from being replayed. Original chats and model selection are preserved.

## Home development preview

[Home](HOME.md) uses the shared DSH lifecycle, model layer, prompt service and
action-outcome helpers. Its loopback API supports persistent household sessions,
Stop, durable request recovery and scoped HA Assist MCP tools. The configured
provider is fixed at process startup. The family model picker, existing UI
connection flow, voice and person-scoped long-term memory are not enabled on
Home. Device discovery/protocols remain Home Assistant responsibilities.

## DSH 0.1.5 compatibility update

The 0.2.8 adapter targets DSH 0.1.5-rc.1 and Model Picker Augmented 1.1.2.
The current source integration advertises `exactFork: 1` and creates an exact
completed-turn seed through the pinned DSH host services. Linux/macOS desktop
adapter tests and the Mac browser UI test verify that Edit excludes the replaced
queued input while preserving parent/tool history. Older integrations lacking this
capability continue to refuse ambiguous forks before mutation. The new integration
is included in macOS development candidate 8. Its installed desktop adapter and
bundled Python passed the real DSH setup and Cocoa interaction fixture: questions,
one-time approval, rejection, cancellation, exact Edit continuation and refusal
to replay a lost child-creation acknowledgement. Native approvals and questions
use authenticated session leases. Linux source checks also verify cancellation
during a pending approval and refusal of a late answer. These checks use a
deterministic local model and do not certify all DSH plugins, external models or
desktop-control permissions. Debian package candidate 4 also passes these DSH
checks through `/usr/lib/augmentor` in a clean Debian 13 container as an ordinary
user. The container uses a read-only pinned test host and isolated model/state.
This supersedes
the historical 0.1.1-rc.2 evidence below; it does not certify every DSH release.

Mac candidate 8 also passes the Pi companion fixture with its installed extension,
native host and bundled runtime in Chrome for Testing 153.0.8010.36. Both configured
and fresh-model setup runs verify actual page navigation/type/click, shared prompt
conflicts, macOS clipboard interaction, branching/editing, private support export
and reconnect without replay. This uses the real Pi SDK with a deterministic
local model. Optional memory was not exercised in these runs, and this is browser
qualification rather than macOS desktop input/capture qualification.

Mac development candidate 10 now passes optional memory through its installed
native app, bundled runtime and Pi/DSH bindings. The Cocoa form performed
check/save/retain/view/disable against an isolated real Hindsight 0.9.2 service;
recall scope isolation, export, remote deletion and local source purge passed.
Both harnesses received real recalled content in desktop and browser role
sessions (eight deterministic harness-model requests). Hindsight used a local
Qwen model. A separate headed Chrome for Testing 153 run also passed the installed browser
memory DOM controls: retention, document viewing, disable, deletion, downloaded
fact export and independent companion recall. That browser run used Pi; the
DSH memory binding is covered by the role checks above. The installed app
retained its valid signature afterward. Evidence:
`outputs/cross-platform/mac-installed10-memory.json` and the matching log.

## Version boundaries

- Product/native-browser adapter handshake: `augmentor/1`.
- Independent prompt service: `augmentor-prompts/1`; incompatible requests fail before mutation.
- Pi worker: existing `augmentor-pi/1`; Pi SDK/core/AI packages pinned at **0.85.1**.
- DSH: **0.1.5-rc.1**, pinned in `release/dsh/package.json` and checked by the setup service against the installed CLI and host. Current qualification uses its authenticated public API and plugin hooks. Earlier 0.1.1-rc.2 results below are historical. Each session stays owned by its engine; there is no automatic cross-engine conversation conversion.
- Browser extension, bundled DSH plugins, host/native app and shared settings adapter: **0.2.9** (current source). The companion requires an exact matching release before starting a harness or changing shared data. Node **24.19.0** is bundled. Linux browser evidence includes Chromium **152.0.7977.75**; current Mac browser evidence uses Chrome for Testing **153.0.8010.36**. Artifact-specific qualification and remaining gates are in [cross-platform release status](CROSS-PLATFORM-RELEASE-STATUS.md).
- Optional manual memory: [Hindsight 0.9.2](MEMORY.md) is tested through its HTTP API. All four combinations share the same service and explicitly selected user/project bank. The active scope is a global user preference, not inferred from each chat's working directory. Memory is disabled until configured and retention is explicit.

Automatic memory instead uses [Hindsight 0.10.0](DUAL-MEMORY.md), separate
person and person/project banks, automatic transcript capture and knowledge pages.
See [operations](MEMORY-OPERATIONS.md) for binding, pause and retention limits.

## Product requirement clarified by the user

Augmentor Agent is one product with a Linux application and a Chromium extension. Each surface independently selects an available harness. Both DSH presentations use the same personal-agent instructions and tools; floating/sidebar presentation does not restrict task capabilities. Desktop input is a limited KDE Wayland preview; see DESKTOP-CONTROL.md for its actual scope.

Use the single shared personal-agent definition. Common UI features such as Copy/check, Edit and Branch should be delivered and tested across both renderers, subject to explicitly recorded harness capability gaps. A change to one renderer alone does not automatically update the other. Shared long-term memory also does not convert a harness-native conversation into another harness's session.

The neutral API is introduced at the adapter boundary; existing Pi and DSH wire envelopes remain explicit. Further normalization can proceed incrementally behind these adapters. No replacement agent loop or speculative plugin marketplace was introduced.

## Rule for adding a feature

1. Change its shared owner and behavior fixtures.
2. Add the Qt and DOM rendering bindings where applicable.
3. Declare adapter capabilities. Preserve native session IDs, event cursors, model choices and unknown-outcome semantics.
4. Update this table and run the applicable contract, interaction and installed acceptance checks. A screenshot or test count alone is insufficient.

`npm run build` generates both surfaces' icons, labels, timing and browser clipboard rule. Commit generated bindings with their source so an unpacked extension can be loaded directly. A design change must not edit the generated files alone.

## DSH Branch/Edit evidence, 2026-09-06

The isolated DSH proof uses the installed CLI 0.1.1-rc.2 and its public API
(host version reports 0.0.1). The inspected source revision is
`b8f772c6574f959daaa591948c62596c6e5b3ab0`. Both adapters pass actual model-context
checks, source-history preservation and deduplicated branching. Real Qt pointer
clicks also branch and edit/resubmit through its controller. This fixture makes
nine requests to a deterministic local model server, with no developer keys.

The real Chromium 152.0.7977.75 extension proof additionally uses the local
Qwen3.8-27B-UD-Q6_K_XL model through DSH: browser navigate/type/click updates the
actual page; rendered Branch/Edit buttons preserve tool context and resubmit once.
Pi's companion proof retains eight deterministic fixture model requests, external
clipboard checks, tick expiry and an idle refresh without a scroll jump.
These are development-checkout checks, not a claim about every DSH release.

OpenCode is retired from the supported product. Existing user data is retained;
it is not migrated into Pi or DSH conversations.

## September 2026 development additions

| Feature | Desktop DSH | Browser DSH | Pi |
| --- | --- | --- | --- |
| Hindsight relationship pages + project semantic memory | Implemented; local adapter activated | Shared adapter activated; controls in source | Lifecycle integration tested with fixtures |
| Resonant Voice hold/lock and saved voices | Native preview installed; [buffered capture, echo guard and gestures](HANDS-FREE-IMPLEMENTATION.md#buffered-activation-and-playback-echo-protection--19-september-2026) | Source integration and fixtures | Voice unsupported |
| Hands-free VAD and echo cancellation | Optional native preview; room acceptance pending | Deferred | Deferred |
| Skins, backgrounds, named second window and shortcuts | Native development implementation | Surface-specific appearance only | Same native UI where applicable |
| Fedora RPM | Container preview qualified; real desktop pending | Attachment pending | Bundled runtime subset |

See [the development ledger](DESKTOP-UPDATE-2026-09-19.md). Historical package
qualification above applies to the recorded package, not automatically to this
new development snapshot.

## DSH terminal response validity — September 21

Augmentor Linux/browser DSH presets recover reasoning-only or blank terminal
responses within the shared truncation budget and visibly report incomplete work
when that budget fails. Valid answers and tool-concluded handoffs are preserved.
No task-domain rules or semantic completion claims are added. Pi parity and the
broader evidence-backed task checkpoint are not implemented by this increment.
See [contract and qualification](BOUNDED-EXECUTION-RECOVERY.md).

## 0.2.10 recovery scope

Both DSH Augmentor presets include [action-aware recovery](BOUNDED-EXECUTION-RECOVERY.md#action-aware-recovery--0210-preview). Exact duplicate changes and uncertain/background outcomes are guarded during automatic recovery; normal explicit tasks retain their behavior. Pi and delegated agents are outside this adapter. This is execution protection, not semantic task verification.
