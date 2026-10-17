<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Local model identity before generation

A local OpenAI-compatible server can accept a configured model name while serving
another loaded model. The actual MX Qwen endpoint accepted an invented model name
and returned the running alias. Pi's configured/credential-available catalogue
does not establish which model a local server is currently serving.

The [route guard](../packages/runtime/src/local-model-route.ts) checks each HTTP
generation for explicitly named `AUGMENTOR_PI_LLAMA_CPP_PROVIDERS` providers using
`openai-completions`. This is the existing llama.cpp compatibility opt-in; ordinary
unlisted providers retain their transport. Picking, pinning and inspecting a
configured dormant model remain possible. Generation requires a matching server.
No model-management operation or GPU tuning is introduced.

## Request and response contract

The guard uses the public Agent `streamFunction` seam and SDK request-options
`fetch`, `onPayload` and `onProviderStreamEvent`. The original SDK still owns the
agent, tools, authentication, generation options and lifecycle. An exception in
an extension event alone would be swallowed as a warning, so it is not used as
the dispatch barrier.

Before the actual chat-completions POST, a GET to the same endpoint prefix's
`models` path must advertise the exact selected ID. The GET uses the fully
assembled SDK authentication/headers and actual request URL, including auth URL
resolution. It sends no prompt body and does not resolve credentials again.
Metadata and chat redirects are refused. Metadata is bounded to **1 MiB / five
seconds**; Stop cancels the pending read. Invalid/unavailable metadata refuses
generation without a fallback or a model load.

Every step after a tool repeats that check; a previous match is not cached.
Payload hooks cannot substitute another model ID. A reported response-stream
model ID must also match before Pi normalizes that chunk into text/tool calls.
This catches a server change after metadata verification. Original raw-stream
observers still receive that frame, and the diagnostic states whether a prompt
POST was dispatched. An absent response ID provides only the metadata check;
this contract does not attest weights or make server changes atomic.

The guard preserves payload/schema hooks, reported usage, headers, native history
and existing request limits. SDK transport errors can hide a local rejection as
"Connection error"; the relay retains SDK terminal events/usage while attaching
the known `augmentor.local-model-route` diagnostic and actionable error. It does
not fabricate an HTTP response. Prompt improvement retains the draft and reports
the route failure. Desktop workers retain failed/unknown outcome rules and still
release their own desktop connection. Delegated chat and SDK compaction use the
same managed stream seam.

The UI error directs the user to load the matching profile in AI Model Manager
or choose the running model, then send a new request. It does not automatically
replay an accepted failed request. The original GUI layout and model-picker
curation stay intact. `host.describe` exposes the named-provider scope and the
advertised/reported-ID policy.

## Qualification and adoption

Source type-check/build and **576 Node / 92 Python** pass across 74 Node files,
nineteen Chromium files and 26 GUI cases, two workers/no skips. The focused 24
cases exercise the actual SDK, Host, original GUI, improvement and desktop worker:
wrong selection, authenticated metadata, retained hooks/usage, a response race,
step changes without tool replay, body/status/redirect bounds, Stop, cold reopen,
resource reload and an explicit fresh request after a corrected route.

A bounded live SDK probe on the current Qwen service refuses a configured inactive
alias with **one metadata GET / zero prompt POSTs**. A distinct matching-alias
request uses one more GET and one POST, and raw stream IDs match the running
alias. Its 64-token request-local output cap is a transport/identity probe, not
a full-answer quality test or a change to saved model settings. The SDK's
normalized `responseModel` is populated only on divergence; the proof checks raw
IDs rather than assuming a missing normalized field means missing metadata.

The earlier failed focused checks retained a generic connection error until the
relay preserved its local cause. A desktop fixture initially rejected the normal
owned connection-release call; the corrected assertion permits only that stop
and forbids desktop work. These preliminary failures remain recorded separately.

A fresh ordinary package independently passes the same **576 Node / 92 Python**
cohort, all **1,120 compiled files**, eight shipped-code public-codec/native proof
groups and the same five frozen historical preparations (42 parents, 35 archived
children, 28 images). Its 23,555 unchanged baseline inputs verify. The exact separately sealed candidate independently passes
that same cohort and both shipped-code/frozen-input checks; all **24,686 sealed
inputs** verify after qualification and subsequent running-review checks.

Package/owner adoption status and exact tested input hashes are in the
[qualification record](../release/harness-local-model-route-qualification-20261017.json).
Both actual review profiles now run **e37d79b6 / 20261017-055628-b9afa698**,
artifact `6cb94165f70e191c99746500127a600a8e2ec2afaaf67994cc2653dd4c60b477`.
Guarded shutdown and the installed opener preserve four conversations and all
36 authoritative file prefixes after verified shared SQLite and full cold
backups (416 regular files). Only typed MCP connection metadata is appended;
no old agent work is replayed. The actual original Plugins page passes read-only
On/Off/switch checks in both owners with zero browser errors. Twelve prompts,
nineteen captured memory records and all shared eligibility/job/settings rows
remain exact. See [actual adoption](../release/harness-local-model-route-owner-review-20261017.json)
for the caught menu-namespace correction, exact preservation and remaining scope.

Open the current build with the existing **Augmentor Harness (MX)** menu entry
or `augmentor-harness-review open main`; use `open pilot` for the migration pilot.
Old browser links expire with their old process. Production Desktop selection
and the earlier Preview entry remain unchanged. No additional real project is
moved. MX Linux is the qualified target. Shared Node code uses public SDK APIs;
later platform artifacts, virtual routes, every external provider and physical
owner acceptance remain separate. The owner pilot-feedback gate still applies
to wider DSH migration. Connected-tools detail-panel visual polish is separate
from the working overview controls; voice remains deferred.
