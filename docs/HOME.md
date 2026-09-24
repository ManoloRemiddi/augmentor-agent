<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Home runtime — development preview

Home reuses the family's DSH sessions, model provider, tool lifecycle, prompt
service and action-outcome helpers. Application code lives here in `apps/home`
and `adapters/dsh-home`. The private `local-ai-smart-home` companion owns hub
packaging, operational evidence and household-specific configuration. It does
not own a second conversation engine. Desktop and Browser remain unchanged.

## Integrate existing homes

Home Assistant owns discovery, device drivers, vendor account linking, areas,
entity names and exposure. Augmentor uses its official
[Assist MCP integration](https://www.home-assistant.io/integrations/mcp_server/),
through the upstream DSH MCP client and MCP SDK. No custom WebSocket frames,
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
Home can control, test one device. The guided Augmentor UI is not implemented
in this preview; operators currently use HA's UI and the local API.

## Authority and uncertainty

Use `/api/mcp/assist` with a dedicated non-administrator HA user. Never mount
an owner token into this runtime. HA Assist exposure controls which entities
are available. Exposure belongs to the shared HA conversation assistant, not a
private per-client list; preserve existing settings when attaching a household.
The HA token itself is not an entity-scoped credential: confinement also depends
on the Assist endpoint, this adapter and protecting the credential/container.

Only live context and `intent__HassTurnOn`, `intent__HassTurnOff` and
`intent__HassLightSet` are advertised. The policy checks every invocation,
including unadvertised calls. Changes require a name and explicit domains limited
to `light`, `switch` and `input_boolean`; administrative, lock, cover, climate,
script and arbitrary service tools are unavailable. Exposed switches may control
consequential equipment: review real devices before enabling them. Multiple devices
can share a friendly name; unique names/areas and explicit exposure are necessary.
The current contract does not certify semantic intent or physical safety.

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
transport to reach the service; no browser-origin API access or WAN bind exists.

Run as the host's ordinary UID with a writable private state mount, read-only
root, tmpfs `/tmp`, dropped capabilities and no-new-privileges. Set
`AUGMENTOR_SHARED_STATE=/state/shared-run` and
`AUGMENTOR_SHARED_DATA=/state/shared-data`. The companion provides Compose and
a Docker CLI fallback. Restart/recreate after credential or model changes so
the process loads them; writing an environment file alone is insufficient.

## Local API

All endpoints require `Authorization: Bearer <service-token>`; JSON POSTs need
Content-Length and are limited to 16 KiB. Browser Origin requests are refused.

| Endpoint | Contract |
| --- | --- |
| `GET /health` | Process/model identity and busy state; not provider readiness |
| `GET /ready` | Bounded HA MCP initialization probe; 503 if unavailable; no billable model probe |
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
sync or model-picker UI yet. One explicitly configured OpenAI-compatible provider
runs through DSH; subscription access is not assumed to be a transferable API key.

## Qualification and remaining work

24 September 2026 development qualification:

- Eleven tests exercise the actual DSH+MCP bridge with deterministic model/MCP
  fixtures and the HTTP/SQLite contracts: resume, authority denial, unknown writes,
  deadlines, incomplete provider output, auth, validation, deduplication,
  concurrency, crash recovery and disconnected-client completion.
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
