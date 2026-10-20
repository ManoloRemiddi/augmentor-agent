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

## Installed acceptance — 20 October 2026

This supersedes the initial source-only qualification. AH runtime source
`44ae92b31db900cee2c08704b6ccbc1e49b93ae1` is installed on MX and the 32 GB Mac
mini. Both contain the existing macOS Search/defaults and Wiki compatibility
commits, preserving the Mac update that arrived during research qualification.
The DSH-only fetch-body translation is source
`1ea13f31d4fb6865689fcc1dceba42c906c5c7a2`; its separate sealed integration uses
exactly the same compiled research client. No selected artifact was edited.

| Installation | Artifact | Actual model acceptance |
| --- | --- | --- |
| MX AH | `2c6b3a441261a685e7f512c95a48948d5f8d5fe56bc928d26c26506fc98a1538` | Local Qwen used Search/Fetch and cited inspected primary pages. Its first Pi URL failed; an explicit recovery located and read the current Pi documentation. |
| Mac mini AH | `41629b727335b9be87c675d245e314b4383144c39eaf8274f3723646b1544134` | Existing DeepSeek selection used Search/Fetch, recovered from one failed Pi page, and cited both projects. |
| MX original DSH | `e6fa8eb477981cde4d8bbec3517b2cf12729e218161a74035506236620ce3710` | Local Qwen used Search and two Fetch calls, read dsh-context and Pi Sessions, and cited both. The final run had no tool errors. |

Each received the fixed question above. These are actual installed conversations,
not mocked clients. The MX recovery adds a follow-up to the original question;
the Mac chose its own recovery. This proves usable tools, readable evidence,
explicit failures and citations, not that every model interpretation is correct.
The question's separate DSH Trajectory terminology was not fully established by
all models; do not use these smoke answers as an upstream architecture audit.

The original DSH failure was a registered provider with no usable key. Its
machine-level patch outranks the web-profile patch, and duplicate selectors did
not replace the original selection. Update the **existing** `web` entry with both
`searchProvider: augmentor-research` and `fetchProvider: augmentor-research`, and
register the adapter once. Verify the composed configuration and the restarted
owner; a changed YAML file alone is not runtime proof. The old web-search plugin
remains installed. DSH's fetch seam receives a text body, and explicitly labels
HTTP 200 as the extraction-service success; Tavily does not report the origin
server's HTTP status.

The key supplied privately through MX Search was configured privately on the
Mac; DSH reads the same protected MX file. All share one account allowance. No
billing settings were changed. Basic remains the default; advanced search is an
explicit tool control, not the separately priced hosted Research endpoint.

A full build plus 70 focused cases passed on Linux and macOS; Linux also passed
the same cohort against the sealed app. After the DSH body correction, eight
research cases passed before and after sealing that integration. Real client
search/extraction passed on both operating systems. Existing owner model choices,
Metafolders and conversations passed pre-test preservation checks; cold backup
verification covered 4,802 MX profile files and 90 Mac files. Prior builds and
small original DSH configuration backups are retained. One obsolete candidate
and finished scratch copies were removed; no unused research build is retained.
Login services remain enabled and current owners are running. A physical reboot
and a separate new live Wiki acceptance were not part of this research update.
Private receipts, paths, account counters, keys and transcripts stay outside Git.
