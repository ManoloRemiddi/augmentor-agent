<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Home runtime — development preview

Home reuses the family's DSH sessions, model provider, tool lifecycle, prompt
service and action-outcome helpers. Application code lives here in `apps/home`
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

One active request, 90-second cancellation deadline, 10 DSH steps and 12 tool
calls bound each turn. MCP calls time out after 15 seconds. Cancellation after
dispatch leaves an unknown outcome. Client disconnection does not cancel an
admitted turn; retrieve its result with the original request ID. At most 16 DSH
session handles are retained in memory; durable sessions resume on demand.

## Build and configuration

```sh
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
runs through DSH; subscription access is not assumed to be a transferable API key.

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

NAS runtime source `b2006ff` is promoted with the prior image and a consistent
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
field. Desktop integration is coordinating with a simultaneous shared-surfaces
release; follow its final deployment record rather than assuming selection equals
running adoption. Guided hub authorization, broader provider access, physical
qualification, routines, independent voice, retention and long soak remain open.


A subsequent NAS-only cancellation correction latches cancellation during async
session creation and threads revocation/Stop through admission and direct-device
validation. Cancellation before the first model request produces no provider or
device call. The 26-test Home suite covers that startup race and revocation of an
active client. This does not change the separately coordinated Desktop artifact.
