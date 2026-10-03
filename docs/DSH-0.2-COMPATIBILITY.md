<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# DSH 0.2 compatibility — October 3, 2026

The qualified target is `@deepseek-ai/dsh@0.2.0-rc.2`, Cordis 4.0.4 and
Schemastery 3.18.4. The newer 0.2.1 alpha is not qualified. The complete-install
lock remains on 0.1.5-rc.1: this work qualifies the existing Linux installation
and shared plugin contracts, not new macOS/Windows/customer installers.

## Changed contracts

- Tool results have role `tool`, direct content and top-level `isError`; 0.1
  results use a nested block. Context trimming/evidence retrieval, execution,
  memory and native/browser speech rendering accept both tested shapes.
- Producer attribution is `plugin:<name>`. Memory/workspace/execution emit the
  current form and recognize old attribution during replay. Status completions
  now have a matching plugin-owned command opener; surfaces hide this opener.
- Jobs may belong to a session ID rather than an Agent object. Maintenance still
  refuses active jobs; deterministic checks exercise both representations.
- Own Adaptive Reasoning 0.2.4 and Resonant Voice 0.1.20 explicitly support the
  two tested DSH/Cordis pairs. Voice keeps speech transcripts in assistant/tool
  roles and now tests a persisted cold read. Model Picker Augmented 1.1.3 uses
  the scoped schema package and Loader Config/settings.configure on 0.2, with
  the old settings.register fallback on 0.1.

## Local migration requirements

Do not upgrade solely by widening peers. Inspect actual mounted packages;
installed immutable adapters can differ from disabled profile dependencies.
Back up the runtime, profile, configuration, presets and session directory with
private permissions. Keep credentials and private history outside source control.
Run all migration reads against a copy before changing the live service.

DSH 0.2 uses declarative `@deepseek-ai/dsh-agent-preset` rows, each with
`config.id` and `config.plugins`, registered by `agent-preset-registry`.
Wrap existing `.agent-presets/<id>/agent.cordis.yml` entries in those declarations;
retain IDs, prompts, settings, groups and YAML expressions. Resolve relative
plugin modules against their original preset folder. Rename workflow-worker-thread
and its package to workflow-ptc. Preserve explicitly enabled Ralph in custom
presets. A successful web boot alone does not prove these presets are usable.
Create a real session using each active Augmentor role.

Legacy settings import is not sufficient evidence of preservation. Compare actual
provider routes and model parameters, default selection, model curation and supported
UI preferences through settings/describe. Explicitly declare OpenRouter's existing
`openai-completions` wire protocol when models are absent from the newer built-in
catalog. Use a YAML 1.2 parser: Python's default YAML 1.1 loader converts a reasoning
level named `off` into a boolean key and corrupts the configuration.

The old Web UI aggregate is replaced by `@linxin666/dsh-web-all@0.4.4`; Doctor
0.3.24 retains the existing supervisor/disabled-plugin choices. Explicit peer
resolution overrides pin the tested DSH family. The model/provider/speech hardware
settings are preserved, not reduced to pass qualification.

## Temporary upstream history patch

Unmodified 0.2.0-rc.2 reads 862 of 955 local saved session entries; 0.1.5-rc.1
reads 913. Fifty sessions lack an opener for legacy Augmentor `Harness: ` status
completions; another contains idle tool-context replacements made by `/trim-tools`.
The remaining 42 descriptor failures also occur on the old runtime.

The local reviewed [patch](../release/dsh/patches/dsh-session-format-v3-to-v4-0.2.0-rc.2.patch)
restores the 51 regressions. It retains original completions and adds only an
attributed status opener using upstream reference/inheritance remapping. Idle
replacements require the exact saved tool identity, turn/step, adjacent prune and
single-node provenance. Unrelated orphan commands, forged tool metadata and
ordinary invalid lifecycles remain rejected. No user/model/tool action is replayed.
Original v3 artifacts remain preserved by upstream successor migration.

This is a **locally patched release candidate**, not an unmodified official DSH
build. [The installer](../scripts/apply-dsh-02-compat.py) refuses any other package
version or source hash and verifies the output hash. Apply it to every resolved
copy of dsh-session-format-v3-to-v4 after installation; retain it as a pnpm patched
 dependency when rebuilding profiles. Do not automatically apply it to future DSH.
A future upstream correction must be requalified before removing this bridge.

## Evidence and scope

Public source baseline: Augmentor `f738a73`, Reasoning `7c38ebb`, Voice `9f43183`,
Model Picker `3264aa7`. Linux-only local candidate overlays the selected 0.2.11
artifact with independently authored compatibility edits; it preserves later
voice/Handy/settings changes. Existing private checkouts are untouched.

- All 78 existing DSH Node contracts pass against 0.2.0-rc.2; two added migration
  fixtures also pass. Manual idle trim now verifies cold persistence and rejects
  forged replacement metadata. Legacy focused contracts also pass.
- Browser renderer: 13 passing cases; native voice delivery: 3 passing cases.
- Actual mounted execution adapter: 37 passing cases. Actual mounted voice adapter
  passes real DSH lifecycle and persisted cold-read tests with fixture LLM/TTS.
- Private history copy: patched 0.2 reads 913/955, matching the old runtime. No
  private conversations or machine configuration are public test fixtures.
- Candidate real-model chat completed on the existing Qwen provider and survived
  reopening. All seven provider routes, saved curation and default selection were
  restored. Seventeen declarative presets register without broken entries.
- Broader unrelated Codex suite encountered four missing-system-QtTest fixtures
  and one browser image-input failure; those are not DSH qualification evidence.
  Real microphone/listening and macOS/Windows installed acceptance remain separate.

Installed promotion and exact mixed-artifact identity are recorded below after
live verification. npm registry publication requires owner credentials; local
file artifacts and reviewed GitHub source do not depend on publishing credentials.
