<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Home runtime — development preview

Home reuses the family's harness SDK, model provider, tool lifecycle, prompt
service and action-outcome helpers. Existing deployments default to DSH; the
[explicit Pi backend](#pi-backend--october-15) is qualified with authored fixtures
and an isolated Linux image, without changing the live NAS. Application code lives here in `apps/home`
and `adapters/dsh-home`. The private `local-ai-smart-home` companion owns hub
packaging, operational evidence and household-specific configuration. It does
not own a second conversation engine. Existing Desktop and Browser clients now
have a shared Home adapter and pairing settings; installed artifact identity is
tracked separately from source. The NAS access preview is deployed; full V1
qualification remains open.

## Integrate existing homes

Home Assistant owns discovery, device drivers, vendor account linking, areas,
entity names and integrations. Selected-device mode reuses its official REST
services and entity-registry APIs, with a Home-specific owner selection boundary.
The earlier [Assist MCP integration](https://www.home-assistant.io/integrations/mcp_server/)
is retained as an explicit compatibility preview. No custom WebSocket frames,
Zigbee stack, Matter controller, vendor drivers or model tool loop are added.

Prefer attaching an existing Home Assistant installation. A new installation
uses the same HA integrations; install MQTT/Zigbee2MQTT, Matter or Thread
components only when the actual hardware requires them. Existing Google Home
links are not a universal device export. Reuse a supported vendor integration,
local integration or Matter multi-admin sharing where available. Some accounts
or devices need linking again. [Matter requirements and installation support](https://www.home-assistant.io/integrations/matter/)
must be checked for the selected host; standalone Docker is not equivalent to
HA OS with managed apps. Do not promise universal import or zero pairing.

The onboarding target is: connect hub, review discovered devices, choose what
Home can control, test one device. The Home page now provides pairing, device
selection and model configuration. Guided initial HA authorization and fresh-hub
setup remain operator-assisted through HA's existing interfaces.

## Desktop dashboard launcher

[Home launcher](HOME-LAUNCHER.md) adds an optional Qt tray icon that opens the
existing NAS dashboard in an installed browser's app window. The dashboard URL
is remembered per user; no copied API key or agent session is required. Home's
NAS-owned service and conversation capability remain independent of this launcher.

## Product direction and current scope

The main Home service belongs on the always-on NAS. Any connected Augmentor
client should be able to request Home work in its existing conversation through
a shared authenticated capability adapter, with results returned there. The NAS
owns permissions, durable execution and recovery; clients do not bypass it with
independent HA credentials or device loops. DSH/Pi adapters and native/Browser
settings implement the first clients; every installed surface still needs its
recorded deployment and acceptance evidence.

Each household supplies its own devices, model endpoints, subscriptions and API
access. Developer hardware and the tested DeepSeek configuration are examples,
not required product defaults. Model weights need not run on the NAS; inference
can use an explicitly configured cloud or other local endpoint.

The base runtime must be small and CPU-only. Its optional setup/status/basic-chat
web page renders on the viewing phone/computer and must require no NAS GPU,
graphical desktop, Qt/Xvfb or server-side browser. Reuse existing Augmentor clients
for the rich experience. Voice, video, local models and other heavy services are
optional modules. Planned qualification measures CPU, memory, image/dependency
size and client assets on limited-resource profiles and actual modest hardware;
current NAS evidence does not establish a universal minimum specification.

## Authority and uncertainty

Use a dedicated non-administrator HA user; never mount its owner token into the
runtime. The HA credential itself is broader than Home's selected entities, so
confinement depends on this adapter and protecting the credential/container.
Selected mode exposes only constrained reads and on/off/brightness actions for
owner-approved registered devices. Identity changes, unsupported domains and
arbitrary services fail closed. Existing HA exposure is preserved. Review a
switch/helper's connected equipment and existing automations before enabling it.

The legacy `assist-preview` mode advertises HA live context and named on/off/light
intents, using HA Assist exposure rather than Home's exact selection. It retains
the earlier prototype limitations and is not the default for new configurations.

SQLite records each request before execution and each mutation before dispatch.
The same request ID and input returns the stored response. Reusing an ID with
different input or an interrupted request returns 409. An interrupted mutation
becomes unknown after restart; unknown actions block further changes across
sessions until explicitly acknowledged. Reads remain possible. No automatic
mutation replay or provider fallback occurs. This is not distributed exactly-once
execution: HA can act before a connection breaks. Tool completion is an execution
acknowledgement; the agent must read state afterwards to report observed effects.

One active request, 90-second cancellation deadline, 10 model requests and 12 tool
calls bound each turn. MCP calls time out after 15 seconds. Cancellation after
dispatch leaves an unknown outcome. Client disconnection does not cancel an
admitted turn; retrieve its result with the original request ID. At most 16 harness
session handles are retained in memory; durable sessions resume on demand.

The deadline regression test uses actual DSH and a local MCP fixture, waits until
the fixture has received the mutation, then advances Node's test clock. This
exercises cancellation after dispatch and verifies that a subsequent request
cannot repeat the uncertain action, with an explicit denied-tool trace for the
model's retry. Previously a 100 ms wall-clock deadline could
expire before dispatch on a loaded runner: [CI at 3edb570](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/36406785088)
correctly performed zero mutations but failed the test's expectation of one.
The corrected test and all 29 Home tests pass locally on Node 24.19.0. Production
deadlines, dispatch and cancellation behavior are unchanged; this is deterministic
fixture evidence, not a live household/device test.

## Build and configuration

```sh
npm ci --ignore-scripts
./node_modules/.bin/tsc -p tsconfig.json
npm ci --prefix apps/home --ignore-scripts
npm --prefix apps/home test
docker build -f apps/home/Dockerfile -t augmentor-home:preview .
```

Node 24.19.0, DSH 0.1.5-rc.1, Cordis 4.0.2, MCP SDK 1.30.0 and ws 8.21.3 are
locked. The image pins the Node base digest, installs Debian's Python and
python3-websocket for the existing prompt service and compiles shared packages.
Debian package repositories can change: deploy the resulting immutable image ID
or registry digest, retain that image for rollback, and record source revision.
This image is not a published Desktop/Browser release or a public container release.

Required variables: `MODEL_BASE_URL`, `MODEL_ID`, `HA_MCP_URL`,
`MODEL_API_KEY_FILE`, `HA_TOKEN_FILE`, `HOME_AGENT_TOKEN_FILE`.
Credentials are mounted read-only files; the model key is never a command-line
argument. `HOME_STATE_DIR` defaults to `/state`; `PORT` defaults to 8181 and the
server always binds loopback. HTTP off loopback requires explicit
`HOME_ALLOW_LAN_HTTP=1`; prefer HTTPS for remote connections. Use a private
HTTPS gateway to reach the service; set its exact `HOME_PUBLIC_ORIGIN` for
browser sessions. No WAN bind or wildcard CORS is enabled.

Run as the host's ordinary UID with a writable private state mount, read-only
root, tmpfs `/tmp`, dropped capabilities and no-new-privileges. Set
`AUGMENTOR_SHARED_STATE=/state/shared-run` and
`AUGMENTOR_SHARED_DATA=/state/shared-data`. The companion provides Compose and
a Docker CLI fallback. Owner model settings apply at an idle turn boundary and
persist privately; changes to deployment environment/mounted files still require
a controlled recreation. A saved model choice overrides its initial environment.

## Local API

APIs require a paired bearer, protected browser session or local operator token;
static assets and one-time pairing are the exceptions. JSON POSTs need
Content-Length and are limited to 16 KiB. Browser writes require matching Origin
and session CSRF; browser-origin bearer requests are refused.

| Endpoint | Contract |
| --- | --- |
| `POST /pair` | Exchange a one-use invitation for a scoped API/browser client |
| `GET /capabilities` | Protocol, permissions and enabled mode |
| `GET /devices/selected` | Read only enabled entities |
| `GET /devices`, `POST /devices/select` | Owner inventory and explicit access selection |
| `POST /device-actions` | Durable exact device control without another LLM call |
| `GET /model`, `POST /model/discover`, `POST /model/save` | Owner model configuration; credentials never returned |
| `GET /health` | Process/model identity and busy state; not provider readiness |
| `GET /ready` | Bounded HA dependency probe; 503 if unavailable; no billable model probe |
| `GET /prompts` | Existing family prompt-library snapshot, local to this host |
| `POST /ask` | `request_id`, `session_id`, `prompt`; optional saved `prompt_id` |
| `GET /requests/<id>` | Durable request status and saved response after disconnect/restart |
| `POST /cancel` | `{}`; request cancellation, then inspect outcome |
| `GET /actions` | Outstanding mutations with tool, arguments and originating request |
| `POST /actions/acknowledge` | `action_id`, `outcome_reviewed: true`; clear unknown only after inspecting actual state; never replays |

Example body (credentials deliberately omitted):

```json
{"request_id":"unique-request-1","session_id":"household-1","prompt":"Read the test lamp state without changing it."}
```

Conversation JSONL, request replies, action arguments and prompt SQLite are
private household data under `/state`. Session IDs do not identify a speaker.
Personal/relationship/project memory inference is disabled. The shared prompt
service implementation and schema are reused, but there is no cross-host prompt
sync yet. The Home page configures one OpenAI-compatible provider; full family
provider-picker/subscription integration remains pending. The selected provider
runs through the explicitly configured harness; subscription access is not assumed
to be a transferable API key.

## Pi backend — October 15

`HOME_HARNESS=pi` selects the family's public Pi coding-agent **1.1.0** session
lifecycle. Unset or `dsh` preserves the existing DSH backend. There is one session
owner per household, no second agent loop and no automatic engine fallback. The
existing `augmentor-home/1` HTTP contract, pairing/roles, request receipts,
SQLite action ledger, shared prompts, model settings and Home web page are reused.
`GET /health` identifies the actual harness; it does not prove provider readiness.

Both device modes work: default `selected` exposes only `home_devices` and
`home_set` through the existing exact registry/REST boundary; `assist-preview`
uses the public Pi MCP extension with HA live context and the same three allowed
intent tools. Reads and mutation acknowledgements remain separate from physical
verification. A failed/partial acknowledgement, mismatching observed selected
state, cancellation after dispatch or lost HTTP response leaves an unknown action;
the ledger fences further changes until review. No mutation is automatically
replayed. The Pi seat enforces ten provider requests, twelve tool calls,
sequential execution, 90 seconds by default, 4,096 output tokens and the same
configured context size (131,072 default). These are service bounds, not changes
to the owner's live Qwen/speech configuration.

Pi uses private `pi/agent`, `pi/index` and `pi/sessions` beneath the existing
`HOME_STATE_DIR`. An fsynced household-hash index names one native SDK JSONL; its
retained scope entry must match on cold resume. Missing, foreign, unsafe or
corrupt history fails closed. Index reservation can precede the first native
flush: a crash/cancel at that boundary can leave an index whose missing file needs
operator review. There is no automatic repair or silent fresh conversation.
Each backend refuses the other's same-household marker, including on rollback.
History conversion/import is **not implemented**. For a trial use a separate
private state mount and newly scoped conversations; retain the old state/image
for rollback, with one service owner holding its normal `flock` lock. Existing
live history is not a migration fixture.

The dedicated Home process sets `PI_CODING_AGENT_DIR` to its own private agent
directory, disables telemetry/analytics/cache warming/retries and loads no CLI
packages, project context, skills, themes, prompt templates or built-in coding
tools. The public `before_agent_start` forced-prompt projection sends only the
Home persona plus current tool declarations, excluding SDK-added cwd metadata.
Literal `/mcp ...` chat remains user text. Explicit model selection cannot silently
fall back. HA/model tokens remain in configured secret files/process memory;
owner-saved model settings retain the existing private `model.json` behavior.
See [data scope](DATA-AND-SUPPORT.md#home-pi-data) for native histories and retained
failed HTTP bodies.

Build and test from the repository root with Node **24.19.0**:

```sh
npm ci --ignore-scripts
./node_modules/.bin/tsc -p tsconfig.json
npm ci --prefix apps/home --ignore-scripts
node --test apps/home/test/*.test.mjs tests/home-client.test.mjs
docker build -f apps/home/Dockerfile.pi -t augmentor-home-pi:preview .
node apps/home/pi/proof.mjs augmentor-home-pi:preview
```

This separate image sets `HOME_HARNESS=pi` and installs its minimal lock from
`apps/home/pi`. All eight Pi/Chord packages match the tested root **1.1.0** family;
other uniquely versioned root dependencies are aligned to the reviewed root
lock. The preparation step rejects a different SDK family and verifies/replaces
Photon with the family's recorded source build. The normal dependency-notice
collector must pass; notices/source terms are preserved, not relicensed as MIT.
There are **158 lock entries / 133 installed production package instances** and
no DSH npm package. The image includes Python/shared prompt service, with no Qt,
server-side browser or GPU service requirement. Its measured local uncompressed
image size is **666,758,013 bytes**; this is not a hardware minimum or performance
benchmark. Debian repositories can change; preserve the actual immutable image
identity in the [portable qualification](../release/harness-home-pi-qualification.json).
The legacy Dockerfile remains separately supported and DSH by default.

Final local evidence at **640e871aeedad697fb87b7e47b754d1574fa0884**: strict check/TypeScript compilation; **54/54** combined Home
and shared-client tests; **9/9** shared SDK privacy/MCP regressions; **2/2** actual
image-CMD proofs, one per device mode. Each image proof uses authored loopback
provider/HA endpoints, normal config/secret-file loading, nonroot read-only root,
1 CPU/1 GiB with no extra swap, actual HTTP authentication, one mutation, cached
same-ID reply, real healthcheck, shared prompts and graceful exit. A preload
rejects DSH package loads and unexpected TCP destinations. Model requests contain
Home instructions/tools but no automatic cwd section. All **633** image-compiled
files match source outputs; all prior **1,007** application files match the sealed
Linux checkpoint, with only three new Home compiled files in the full source tree.
The legacy image also builds and its actual packaged prompt-service read passes.
CI now carries these Home image proofs and common client contracts on three OSes;
new-head hosted results remain separate from local evidence.

Retained preparation failures: a fresh minimal lock mixed SDK **1.1.0/1.2.0**
and failed actual startup before a request; full-family pins corrected it. The
notice-aware build then rejected three freshly resolved AWS versions with absent
reviewed licence text; aligning to the existing tested root versions makes the
unchanged collector pass. Initial Home intent-result envelope handling and a
probe showing SDK cwd leakage were corrected against actual SDK/provider traffic.
No notice requirement or production timeout was relaxed.

This is source plus an unselected local Linux image, not a NAS deployment, public
container, installed MX update or complete DSH retirement. Live HA/model, physical
device outcomes, household migration, controlled NAS upgrade/rollback, owner-crash/
power-loss durability, limited-hardware performance and broader network/privacy
qualification remain open. Desktop GUI bytes and all owner review/selected
artifacts stay unchanged. The independent Office engine build and full migration
release gates remain binding.

## Qualification and remaining work

Historical initial MCP qualification (superseded by the selected-device and access
checkpoints below):

- Twelve tests exercise the actual DSH+MCP bridge with deterministic model/MCP
  fixtures and the HTTP/SQLite contracts: resume, authority denial, unknown writes,
  deadlines, incomplete provider output, auth, validation, deduplication,
  concurrency, crash recovery, disconnected-client completion and partial HA
  intent errors inside successful MCP envelopes.
- Root TypeScript check and seven shared action-outcome regressions pass.
- The isolated image builds on a Linux amd64 NAS. Packaged shared prompt-library
  startup is exercised separately; CI builds and checks that path too.
- Real DeepSeek `deepseek-flash` and HA 2026.9.3: context read, virtual toggle off/on,
  post-action independent state checks, cached duplicate response, and conversation
  recall after a container restart. The non-admin runtime was denied the HA
  administrative user-list operation. No raw runtime credential values were found
  in persisted runtime files. An initial
  upstream tool-name mismatch was corrected to the live `intent__` names before
  accepting control results. No physical equipment was actuated.
- `npm audit --omit=dev` reported zero Home npm dependency vulnerabilities at
  qualification. This is not a full image/security certification.

This is a qualified integration preview, not a completed consumer appliance.
Remaining work includes guided connection/device selection in the existing UI,
family model-picker integration, household identity/privacy design, representative
physical-device tests, ARM/NAS certification, long-duration soak, host reboot and
backup/restore testing, storage retention/quotas and update UX. Persistent history
currently grows; operators must monitor storage. Docker restart policy covers
process/host startup; an unhealthy dependency does not itself restart a container.
HA automations remain independent of cloud model availability.

## Shared client and lightweight access candidate — 24 September

The approved development plan is being implemented. This candidate adds a shared
Home connection for DSH and Pi, native and Browser settings, and a small static NAS
page. Pairing issues independent, revocable owner/member/viewer clients. Browser
credentials use HttpOnly SameSite cookies with origin/CSRF checks; API credentials
stay in the local private configuration file and never enter tool arguments.
Invites last ten minutes, browser sessions seven days and API clients ninety days.
The operator credential remains a local recovery path. Initial startup writes an
owner invitation to the private state directory's `pairing-code`; an owner can
issue additional invitations through the page or authenticated `/clients/invite`.

Set `HOME_PUBLIC_ORIGIN` to the exact private HTTPS origin used by an existing
reverse proxy. The process still binds loopback. With no public origin, browser
access is restricted to loopback (including an SSH tunnel). Do not enable public
Funnel, wildcard origins or cleartext LAN access to the Home gateway.

Desktop and Browser settings connect through the shared local prompt service.
They save `augmentor/home.json` under the user's platform configuration directory
(mode 0600). `AUGMENTOR_HOME_CONNECTION` overrides that path for qualification.
`packages/home-client` provides `home_status`, `home_read`, `home_request`,
`home_result` and `home_cancel` to both harnesses. Home requests include only the
relevant user request, with client-scoped request/session IDs. The NAS retains
accepted work after client disconnect. Local receipts prevent an uncertain
submission from becoming a fresh device action. Viewer and read-only request
constraints are enforced before a device tool dispatch, independent of model text.
Owner action acknowledgement never replays the action.

Validation of this candidate: 17 Home tests use actual DSH/MCP with fixture model
and device endpoints; five shared-client tests cover interrupted access,
pre-admission refusal, duplicate tool calls and bounded responses. Shared suite
185/185, Browser 21/21, and native 402 passed with one environment-dependent skip; native ran with the pinned
requirements in an isolated Qt environment because system Qt lacks QtTest.
Two additional Python pairing tests pass. The in-app browser exercised disposable
pairing and request/reply and inspected a 390px layout without horizontal overflow.
These checks do not establish real phone voice or installed Desktop integration.

Still required: candidate NAS deployment and client-harness qualification,
Home-specific stable entity selection, guided HA/model setup, routines, voice,
retention/backup/update flows and continuous-operation qualification. Existing
installed clients and the recorded NAS image remain unchanged at this checkpoint.


Candidate deployment evidence: `005b3e7` image was built on the NAS and run in
separate state with a one-CPU/256 MiB limit. Private HTTPS pairing and the shared
client successfully called the real DeepSeek provider to read the existing virtual
helper. The candidate was healthy at 89.25 MiB and 0.00% CPU in one idle sample;
this is a spot measurement, not an unattended-operation qualification. Existing
NAS preview and Desktop remain selected. Exact private origin/image are recorded
in the companion. A real DSH client test also caught and corrected the adapter's
content-block rendering contract before client promotion.

Owner recovery: run `docker exec <container> node manage.mjs invite owner`, then
open the state directory's private `pairing-code` locally. This uses the installed
operator credential without printing it or placing it in command arguments. The
code expires in ten minutes. No restart or conversation replay is required.

## Selected-device adapter and direct controls

New configurations default to `HOME_DEVICE_MODE=selected`. No entities are enabled
initially. The owner's Home page loads existing HA inventory and explicitly enables
read-only or reviewed control access (up to 64 registered entities in this profile).
The adapter reuses [HA REST services](https://developers.home-assistant.io/docs/api/rest/)
and the [HA entity registry](https://github.com/home-assistant/core/blob/2026.9.3/homeassistant/components/config/entity_registry.py).
It implements no device protocol. Registration identity, integration and unique ID
are checked against the saved selection before dispatch. Replacement or rename
fails closed for owner review. It leaves HA's shared Assist exposure unchanged.
HA configuration is trusted administration; registry validation and service execution
are separate upstream operations, not an atomic compare-and-execute guarantee.

The selected mode registers only `home_devices` and `home_set` inside the NAS
harness. The generic Assist bridge is absent, preventing intent names from bypassing
the selection. Lights, reviewed switches/helpers and read-only sensors are the
initial supported categories. Device names are data, never authorization. A helper
or switch may trigger existing automations; the owner must review those effects.
Unregistered devices, locks and arbitrary services are unavailable.

Clients can call `home_devices` and then `home_set` for an exact, unambiguous entity.
`POST /device-actions` uses the same admission, role checks, durable requests and
action ledger, without a second LLM call. Status distinguishes observed integration
state from an uncertain result and never claims physical verification. Missing,
replaced, unselected and read-only devices are rejected before dispatch. HTTP or
state-verification failure after dispatch remains unknown; no automatic retry.
`HOME_DEVICE_MODE=assist-preview` explicitly retains the earlier MCP prototype for
compatibility and its earlier evidence only; it does not enforce Home selections.

Qualification: 21 Home tests now include the actual selected-device DSH path,
registry replacement, excluded targets, forged arguments, viewer denial and direct
request deduplication. The shared DSH suite's 36 tests include real client delegation.
Non-admin registry reads were verified against HA 2026.9.3 on the NAS. Selected-mode
real service control and installed-client qualification remain separate gates.

## Model configuration candidate

The owner's NAS page now discovers OpenAI-compatible model IDs and saves the
selected API base URL, model and context limit. Cloud, loopback and explicitly
confirmed private-LAN endpoints use the same configuration contract. Credentials
stay in a mode-0600 NAS state file and are never returned by the settings API.
Changing endpoint requires an explicit credential choice so an old provider's key
cannot silently travel to a new host. Empty credentials support local endpoints.
Discovery lists provider inventory; it does not certify text/tool capabilities.

Model changes require an idle service with no unknown actions. A replacement DSH
context is constructed before selection, settings are atomically replaced, and
subsequent requests use the new configuration. Startup reloads the saved choice.
Automatic fallback remains disabled. This is an OpenAI-compatible setup flow;
subscription portability, other provider protocols, usage budgets and integration
with the full family provider picker still require qualification.

The 24-test Home suite includes owner-only idle configuration, credential privacy,
endpoint-change isolation and persisted selection. The earlier selected-device
image `18cc707` passed real NAS helper off/on, duplicate-result retrieval and a
DeepSeek read using `home_devices`; no physical equipment was controlled. Pending
unknown actions were zero, and the helper was restored to on.

The container entrypoint holds an exclusive state-directory lock for its lifetime.
A second supported container cannot open the same Home state concurrently. Direct
`node server.mjs` development launches remain the operator's responsibility.
The static page totals 12,044 uncompressed bytes at this checkpoint; no framework,
font download, GPU or renderer is required on the NAS.

## Selected NAS build and current implementation checks

NAS runtime source `a6630b4` is promoted with the prior image and a consistent
pre-promotion backup retained. Main readiness, selected virtual helper and a clear
unknown-action ledger were verified. The container runs under one CPU/256 MiB;
a fresh idle spot sample was 50.78 MiB / 0.00% CPU. Thirty private HTTPS selected-
device reads had median 11 ms and p95 26 ms in this installation, with no model
calls or device changes. These are short measurements, not seven-day evidence.

Implementation `a983491` passed every job in
[CI 35989685407](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/35989685407):
Debian/source/native checks, Home image/tests, installed packages, packaged Browser
and credential checks. Native and Browser pairing form regressions were added;
the NAS fixture page also demonstrated populated model settings with an empty key
field. The combined Desktop release `20260924-125950-12694ac7` is selected and
running in secondary; main/mobile retain the prior Home-enabled release to preserve
the main draft. Browser extension reload is pending. See the handoff before any
deployment change; selection alone does not imply running adoption. Guided hub authorization, broader provider access, physical
qualification, routines, independent voice, retention and long soak remain open.


A subsequent NAS-only cancellation correction latches cancellation during async
session creation and threads revocation/Stop through admission and direct-device
validation. Cancellation before the first model request produces no provider or
device call. The 26-test Home suite covers that startup race and revocation of an
active client. This does not change the separately coordinated Desktop artifact.

Shutdown follow-up: after closing the HTTP/runtime services and SQLite ledger, the
container process now explicitly exits. Docker stop had otherwise reached its
forced-stop deadline despite an idle service. The correction passed isolated
Docker stop tests at 0.09 seconds idle and 0.2 seconds during an admitted read,
both exit 0; restart preserved the request outcome. It is now promoted, with main
authenticated health/readiness and zero unknown actions verified. This does not
imply a host power-loss test. A finite read-only availability sampler is collecting
seven days of health/readiness evidence on the NAS; no model/device calls are made
and this is not yet completed M7 workload qualification.

Runtime source `a6630b4` subsequently passed all jobs in [CI 35991631351](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/35991631351), including installed packages and packaged Browser checks. Later handoff documentation does not change that deployed source.

## Direct device panel — 24 September 2026

The NAS page now loads device cards immediately after pairing. Each controllable
entity has On/Off buttons with its reported state; unavailable, unselected, replaced
or read-only devices cannot dispatch from the card. Owners can enable reviewed
controls; other readings are grouped separately. Controls use the existing scoped,
durable `/device-actions` contract without an LLM. The pending request ID is saved
before sending; reconnect/refresh retrieves that request and never resubmits it.
Feedback reports integration state, not physical verification.

An optional private `discovered-devices.json` in the state directory provides a
bounded, owner-only inventory of devices needing setup. Its timestamp is shown
explicitly as a discovery snapshot; it grants no authority and never provides a
control target. The companion's `scripts/home-discover.py` reuses HA's installed
python-kasa to populate this file. Devices already connected through HA are omitted
from that snapshot. The page itself does not scan networks or require new packages.

Validation: 29 Home tests, including replaced-identity controls, discovery field
filtering/size limits and owner-only inventory. In-app browser fixture verified
On/Off, disabled offline/setup devices and reload without duplicate dispatch: exactly
two actions for one On and one Off. Deployment identity is recorded separately.


### Deadline regression fixture

The cancellation-after-dispatch test synchronizes on the synthetic MCP write
before invoking the actual request-deadline callback. It holds the remote reply,
checks the durable unknown outcome, and verifies that a later model-requested
mutation cannot dispatch again. This removes a 100 ms scheduling race seen in
CI run 36742665709 without changing the production deadline or cancellation
policy. All 29 Home tests pass locally after the fixture correction.


### Codex client and request-specific cancellation

New Codex Desktop/Browser chats use the same shared Home client and pairing as
DSH/Pi. Direct device actions stay on the NAS's model-free action endpoint;
delegated requests retain the NAS's existing DSH model and permissions. The NAS
application itself is not replaced by Codex. See
[Codex qualification](CODEX-INTEGRATION.md#paired-home-tools) for fixture evidence
and remaining deployment/device acceptance.

`GET /capabilities` advertises `requests.cancelById: true` in this source.
`POST /requests/<request_id>/cancel` with an empty JSON object cancels only when
that exact request is currently admitted for the authenticating client. Mismatch
returns 409 without signaling; this includes a stale cancellation after a newer
request starts. Owner status does not override ownership on this scoped route.
Legacy `/cancel` behavior is unchanged. The shared client checks capability
support before scoped cancellation and never falls back to the broad route.

The local `receipt_owners` table records hashed ownership alongside newly
created receipts in one transaction. The original four-column receipts table
stays unchanged, so older installed clients can continue writing to it. Existing
request identities/statuses are preserved and old rows get no inferred owner.
Codex receipt lookup/cancellation requires its conversation's recorded ownership
under the current pairing. Unknown outcomes still block new dispatches. Stopping
Codex's wait does not guarantee that an admitted NAS task stopped; inspect the
saved result, and use explicit cancellation where supported.


## Harness helper build closure — October 10

The `feat/augmentor-harness` follow-up on base `0b17d1f7d3971072b6cd0c342262e640452b0671` repairs the hosted Home Docker build's missing shared evidence dependency. Root TypeScript compiles the Pi host as well as Home clients; its new context/reassessment modules import the pure Augmentor helper and typed declaration. The curated Docker context now includes exactly `adapters/dsh-context-budget/evidence.mjs`, its `.d.mts` declaration and `adapters/dsh-compat/messages.mjs`. Runtime copies include the two JavaScript helpers. No DSH context service is mounted, and Home continues using its existing owned runtime.

All **30 Home Node tests pass** after installing its independent locked manifest with `npm ci --prefix apps/home --ignore-scripts`. The first local invocation had no Home dependencies and failed module resolution; dependencies were supplied without changing the manifest. The corrected final source image builds using the workflow's pinned Node 24.19.0 base. Local image ID: `sha256:5d8b530587780d9bf1f1ead0bb8719a571258c549a079779c375c3e7ee3ed43d`. An isolated `docker run --rm --tmpfs /tmp` with temporary shared data/state successfully calls the packaged `prompts.list` service and returns a valid empty library. It performs no household/device action and changes no installed Home service or private deployment companion. This is container/package proof; fresh matching-head hosted validation and broader NAS/device acceptance remain distinct gates. See [Harness evidence](AUGMENTOR-HARNESS.md#advisory-reassessment-and-home-build-correction) and [draft PR #45](https://github.com/ManoloRemiddi/augmentor-agent/pull/45).

### Hosted Pi Home follow-up — October 15

Source **476d7be89dd811ca785a873d3ea0abfb16a9fb19** passes the
[Home workflow job](https://github.com/ManoloRemiddi/augmentor-agent/actions/runs/38692313466/job/116280861710):
48/48 source tests, both Docker builds, the unchanged 133-instance notice check,
both actual Pi image-CMD modes and the legacy packaged shared prompt request.
The three-platform shared SDK matrix also passes at that head. This hosted
synthetic proof extends the preceding local Home checkpoint; it does not deploy
or publish the image. The wider Linux workflow fails a separate Context-menu
`Tab` pointer check before later packaging. Its cause remains unresolved.
