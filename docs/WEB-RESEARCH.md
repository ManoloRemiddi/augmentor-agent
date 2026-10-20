<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Shared Tavily research

The authenticated route shares `packages/runtime/src/research.ts` between AH's
existing Pi owner and the original DSH web-provider adapter. No second model loop,
new npm dependency, hosted answer generation, telemetry or account/billing change
is introduced. Existing other-provider credentials and explicit order remain.

## Setup

Create a free Tavily Researcher account at <https://app.tavily.com/> and generate
an API key. The published allowance is 1,000 credits/month without a credit card;
confirm the current plan in the dashboard. Do not paste the key in a conversation,
command argument, public file or issue. Save it in AH Plugins → Search → API
engines → Tavily. Set the provider order to Tavily first and enable page fetching.
The key remains in the private operator Search settings, outside model inputs.
Each machine has its own credential store; a configured Mac does not configure MX.
Do not enable pay-as-you-go or an automatic paid plan for this pilot.

The DSH adapter takes a `searchFile` path to the private AH settings file and
registers `augmentor-research` for both search and fetch. It reads only Tavily's
key, rejects public/linked/hardlinked credentials, and releases both registrations
on unload. Select that provider through the DSH composition. Keep the original
plugin and configuration backup for rollback; never edit its installed source.

## Research behaviour

AH retains `web_search {queries:[...]}` and `web_fetch {urls:[...]}`. Tavily search
also accepts depth (`basic` by default, or `advanced`), `max_results` (1–10),
`include_domains`, `exclude_domains`, `time_range` and `topic`. These controls are
not silently discarded by a different provider. DSH retains its original tools
and uses basic search defaults through its provider seam.

Basic search costs one credit; advanced search costs two. Page extraction has its
own published credit policy. The optional hosted Tavily Research endpoint is not
called. Multi-step research still belongs to the selected local or hosted model.
Source URLs, selected controls and reported credits stay inspectable. Clean page
Markdown replaces raw HTML on the authenticated Tavily path. Existing keyless
mode is retained separately; it does not inherit API credentials.

The agent is told to discover relevant primary sources, read them, check dates and
contradictions and cite actual inspected evidence. A successful shell command,
HTTP challenge page, search snippet or failed extraction is not a completed read.
Long saved evidence remains recoverable through the existing excerpt tool.

Empty results advance to the next explicitly configured provider. Empty or
mismatched extraction fails honestly. Authentication, quota, rate limits, malformed
responses and timeout have safe distinct codes. No immediate repeated requests
are made to exhaust a rate-limited provider. Stop prevents later admission and
partial batches retain completed evidence. Provider responses are bounded;
credentials/raw provider errors are withheld and external content stays untrusted.

## Qualification and activation

The fixed question is: “How do DSH Trajectory / dsh-context and Pi session trees /
context compaction differ, and what should Augmentor Harness preserve?”

The bounded client proof uses two searches and two successful primary-page
extractions. Real model/session proof must additionally show actual tool calls,
readable evidence and citations in MX DSH, MX AH and Mac mini AH. A client test is
not that model proof. Preserve owner model choices, projects, histories, address,
startup and necessary backups; activate only a new tested immutable candidate.

Run the focused build/tests through `scripts/harness-build-workspace.py` using
`scripts/check-research.py --dependencies <existing-node_modules>` on MX. Optional
`--credentials <private-search-json>` adds the bounded live client proof without
printing keys. `scripts/research-live.mjs` also runs on macOS. Keep private live
receipts outside Git. Source, staged candidate and installed acceptance are distinct.

References: [Search API](https://docs.tavily.com/documentation/api-reference/endpoint/search),
[Extract API](https://docs.tavily.com/documentation/api-reference/endpoint/extract),
[credits](https://docs.tavily.com/documentation/api-credits).
