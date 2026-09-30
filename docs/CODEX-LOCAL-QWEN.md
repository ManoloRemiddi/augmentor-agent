<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Codex and the current local Qwen template

Status, October 1: the live local provider still fails the actual pinned Codex
tool check. A separately prepared template candidate passes offline rendering
and parser checks. It has **not** been activated or qualified through inference.

## Confirmed cause

Codex 0.159.2 sends base instructions plus developer messages through Responses.
The existing Qwen3.8-27B-GSQ-RCO-IQ3_S-mtp-262k endpoint is healthy but rejects
the request with HTTP 400 and `System message must be at the beginning` before
generating an answer. The isolated `checkAgent` used only a synthetic nonce tool,
fresh state and no owner credentials or conversations; one request was sent.

The running llama.cpp identifies as `b1-049326a`. Its
[Responses conversion](https://github.com/ggml-org/llama.cpp/blob/049326a/tools/server/server-chat.cpp)
adds base instructions as a system message; the
[template layer](https://github.com/ggml-org/llama.cpp/blob/049326a/common/chat.cpp)
maps developer messages to system messages. The current template renders its
first system message but rejects any later system message. Thus the application
instructions cannot pass through this formatter. A similar failure was reported
in [upstream issue 20733](https://github.com/ggml-org/llama.cpp/issues/20733);
that report is background, not proof of this model's compatibility.

## Reviewable candidate

[prepare-qwen-codex-template.py](../scripts/prepare-qwen-codex-template.py) replaces
one exact rejection block with explicit rendering of later system messages. It
preserves their position, role and text, including developer instructions;
simply deleting the exception would silently omit those instructions. All other
template bytes, reasoning instructions, vision handling and tool syntax remain
unchanged. The helper writes a separate new file and refuses unknown blocks,
source replacement, existing outputs and symlinks. It neither contacts a server
nor edits or restarts a service.

```sh
python3 scripts/prepare-qwen-codex-template.py \
  --source /path/to/original-template.jinja \
  --out /path/to/separate-codex-candidate.jinja
```

Observed original SHA-256:
`c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041`.
Candidate SHA-256:
`a49e6e5da2cb6d114814c9ee5079677dfd1bdc4cf6b5c1519eb73d0bcf12f02b`.
The full model template and installed configuration are not copied into GitHub.

Offline checks use the installed `test-chat-template` and
`llama-debug-template-parser` tools, without loading another model. Both leading
and later developer-message scenarios reproduce the failure with the original
and render successfully with the candidate. Every synthetic constraint/correction
appears exactly once, in its original order, as system text. A single-system
conversation renders byte-for-byte identically. System-image rejection remains
enabled, and the candidate's tool grammar generates successfully. Helper guard
checks and Python compilation also pass. This establishes formatting behavior;
it does not establish model compliance, tool execution, streaming or quality.

## Activation and acceptance still required

The proposed service change is to add `--chat-template-file` pointing at the
separate candidate, preserving the existing model, GPU, context, concurrency,
precision and all other arguments. The service would need a restart. Retain its
original configuration so removing only this override and restarting restores
the current formatter. Do not activate this change without the owner's decision:
[workspace instructions](../AGENTS.md) require preserving the approved model
settings and reporting failure for the owner to direct the next change.

After authorization, qualify the actual Codex nonce/receipt check, streaming,
Stop, resume, persona restrictions and existing DSH/Pi tool behavior. Record the
exact service/template revision and restore the original if qualification fails.
The endpoint remains unqualified until those tests pass. API/account eligibility,
physical Desktop/Browser acceptance and binary distribution gates remain separate
requirements in the full [C0–C9 plan](CODEX-INTEGRATION-PLAN.md).
