<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Response metrics on Pi

Pi now registers `response_metrics` for Native and Browser conversations through
the supported extension API. It carries forward the response-preview workflow
from the public MIT [Augmentor DSH adapter](../adapters/dsh-response-metrics/index.mjs).
The Pi binding is independently authored; the inspected DSH source is not claimed
to supply this tool. Pi remains the sole conversation owner. There is no new
network request, service, GUI component, model setting or action permission.
Existing original Trajectory rows expose its result/schema with the original
expandable JSON tree in Light and Dark themes.

For a request to write text and measure its speed, the assistant should write the
text **before** calling the tool in that same assistant step. The following step
must identify the matching `responsePreview`. A later call also measures its own
newly finished tool-calling step: the first row must never be silently described
as an earlier reply. Up to five rows are returned, newest first; the default is
three. An optional exact observed request ID filters within the same bounded
window. No foreign session, path or file argument is accepted. Browser read-only
mode permits this inspection without granting shell/filesystem access; bounded
workers still require explicit tool grants and inspect only their own observations.

## Measurement boundaries

| Field | Meaning and limitation |
| --- | --- |
| `observed.durationMs` | Monotonic time from the final provider-payload hook to SDK assistant `message_end`. Includes first-delta latency; excludes earlier prompt preparation, later tool execution and other steps. |
| `observed.firstObservedDeltaMs` | First parsed text, reasoning or tool-argument delta from the same observed request. This is not a first network-byte measurement. |
| `observed.outputTokensPerSecond` | Positive SDK-normalized output tokens divided by that client-observed duration. Includes reported reasoning/tool-call output, with provider-dependent accounting. Missing/zero/invalid counters produce `null`. |
| `serverDecode` | Separately reported numeric terminal `timings` fields from an explicitly declared llama.cpp adapter, matched to the native response ID. It uses the server's `predicted_per_second`, `predicted_n` and `predicted_ms`, without inferring them from client latency. Otherwise unavailable. |

The [llama.cpp server contract](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
documents those provider fields. The Pi 1.1.0 OpenAI-completions provider calls the
public parsed-provider-event hook before normalization. The binding observes only
already received fields; it does not enable per-token timing or alter provider
options. Other formats are deliberately unsupported rather than guessed. Partial,
length-limited and error responses retain their stop reason; their measurements
do not certify completion or compare model quality.

## Native identity and privacy

Pi 1.1.0 notifies public listeners **before** persisting the assistant message.
Consequently the observation records the preceding native leaf ID, explicitly
labelled as such, plus a SHA-256 of the credential-field-redacted SDK assistant
JSON. When the tool executes, the assistant has been persisted. A unique message
on the current selected ancestry must match both its parent ID and fingerprint;
the same retained request observation must also exist. An intervening custom
entry, ambiguous/duplicate observation, missing request or changed message yields
unavailable. No private SDK message-ID map or timing heuristic is used.

This metadata retains no second response body, reasoning or tool arguments.
Payload opt-out continues to disable diagnostic bodies while permitting numeric
metadata and hashes, as other observations already do. A result preview reads
only the exact matched native assistant's text, limited to 160 Unicode code
points; it excludes reasoning and tool arguments. Tool results are ordinary
conversation content and their historical previews are data, not instructions.

Each call reads at most 500 recent observation metadata rows and examines at most
4,096 recent selected native ancestry entries returned by the public SDK. The
SDK's `getBranch()` still constructs its ancestry array; this is not claimed to
bound its underlying file/array work. Fingerprinting uses an 8,192-node and
conservative 1 MiB worst-case JSON budget. Oversized/non-JSON/cyclic messages
produce no match. Observation retention, earlier-window cursors, native window
truncation and unavailable older uncorrelated records are explicit in coverage.
No parent observation store is borrowed for a child, and no extra native custom
metric entry changes branch cuts. These observations remain read models without
execution or replay authority.

## Qualification and remaining work

Eleven initial focused authored/real-SDK/original-Chromium checks pass on MX Linux with
two workers and unchanged time limits. They cover native-before-persistence
correlation, exact same-step previews, cold reopen, branch/foreign-session
isolation, read-only Browser policy, payload opt-out, declared server fields,
per-request reset, missing/zero counters, old/ambiguous/unmatched data and bounds.
The initial browser assertion did not expand the original JSON tree; its failure
log is retained and the driver now uses the existing expanders. No GUI or bound
was changed to accommodate it. The first complete 794-case run retained five
failures in older minimal observation peers lacking the newly used public SDK
session-manager interface. Those peers now use real in-memory `SessionManager`s;
all original assertions remain and the numeric correlation is additionally
checked. A twelfth focused case verifies that the SDK already refuses a duplicate
tool supplied by an approved resource before dispatch. Its initial external
driver expected an application-specific error rather than the SDK's actual
collision error; that assertion failure is retained. Full source/fresh ordinary,
live provider and publication evidence are recorded separately once completed.

The current MX owner review **20261016-065534-c8cdf03c/application dfe855f3** does
not include this increment or the preceding shared-persona increment. Installed
activation, owner acceptance, public distribution, representative other-provider
timing formats and later-platform adoption remain separate. No merge or public
binary follows from source checks.
