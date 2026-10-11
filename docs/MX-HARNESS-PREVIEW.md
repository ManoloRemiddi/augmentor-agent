<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# MX Linux Harness preview

The owner has chosen MX Linux first: test the experience on this PC, collect feedback and refine it before implementing further Windows, macOS or other Linux distribution work. The first machine is **MX Linux 25.3 KDE x86-64, based on Debian 13**. This is a separate local development preview, not a production migration or a public binary release.

## Open the preview

Use **Augmentor Harness Preview** in the application menu, or run:

```sh
augmentor-harness-preview
```

It opens the local Harness in the default browser. **Augmentor Desktop – Pi Preview**, or `augmentor-harness-preview --native`, opens the existing native interface with Pi in the same preview profile. The native preview uses its own working folder and dictation state. The existing Augmentor and DSH installation remains available. The two preview presentations share one Pi Host; each conversation has one SDK session owner.

Choose **Conversations**, enter a working folder and create a new conversation. The initial demonstration uses a separate preview workspace and an independently authored note. Choose your own project folder when ready; tools operate with your user account's filesystem access, so this profile separation is not an execution sandbox.

The initial selection uses the existing local Qwen 27B 262k route on the RTX 5090. The preview copies that provider's connection/model metadata into its own private configuration. It does not restart the model service or change GPU placement, context, concurrency, precision, ASR or VAD. No production conversations, prompts or Hindsight bank are imported. This preview therefore starts without your existing personal/project memory configuration.

## What to try

- Chat, file reading and ordinary tasks in your chosen folder; check that answers and Stop behave as expected.
- **Trajectory**: inspect request, tool and turn order, timing and saved tool originals.
- **Context**: inspect the structured provider request, system instructions, messages, tool declarations and reported usage. **Save context history** in Conversations retains future diagnostic payloads locally for up to 14 days or 512 MiB; it does not reconstruct old requests. It is enabled for the demonstration profile so the first successful request can be inspected.
- Prompt library, draft improvement and exact Branch/Edit behavior.
- Plan, Goal and Jobs views. Autonomous continuation and delegated work require their explicit controls/grants; merely opening a tab starts no work.

Feedback is most useful when it includes the task, selected model, expected behavior, actual behavior and the relevant Trajectory/Context observation. Start with everyday work and interface clarity. Voice, browser-extension integration, live MCP services, full memory/data migration, Home and complete desktop-specialist workflows retain their separate acceptance work; menu visibility or synthetic tests do not certify them.

## Local Qwen compatibility

The initial live read request failed before inference with `Failed to initialize samplers: failed to parse grammar`. The actual llama.cpp journal reports a repetition bound in its generated grammar. A diagnostic request with the same model and complete tool set, omitting only string-length schema annotations, returns HTTP 200 and `READY`.

The supported Pi `before_provider_request` extension now offers an **explicit** `AUGMENTOR_PI_LLAMA_CPP_PROVIDERS` list. The preview launcher selects `mx-qwen`. For those named OpenAI-completions providers only, the wire tool parameter schemas omit `minLength` and `maxLength`. The original SDK schemas retain those constraints and still reject invalid arguments before tool execution. Required fields, enums, patterns, object/array/numeric constraints, tool availability, approval rules and execution limits remain intact. Context shows the effective adapted request. Other providers and APIs are unchanged; no SDK patch, automatic fallback, changed sampler setting or second agent loop is used.

The independent actual-SDK/HTTP regression verifies that both too-short and oversized arguments fail, the valid value executes once, and the received request omits only the selected annotations. It also preserves literal property names such as `maxLength` and leaves annotation examples unchanged.

## Installation and identity

`scripts/harness-preview.py` is a stable launcher. It resolves the separate selection, verifies the complete immutable artifact inventory before executing candidate code, uses its bundled Node and staged external Python, and clears inherited Augmentor/DSH path overrides before constructing the private profile. It opens the regular browser with the normal OS environment and never prints the bearer link.

The installed launcher is `~/.local/bin/augmentor-harness-preview`. Profile roots are the ordinary XDG data/config/state/runtime roots with `augmentor-harness-preview` appended. The preview selection is `<preview data>/augmentor/desktop.json`; releases are under its `releases/` directory. Production `~/.local/share/augmentor/desktop.json` is a separate selection.

Stage and activate through the existing **augmentor-update** using `XDG_DATA_HOME=<preview data>`. Never edit a selected release or point a menu entry at a source checkout/version-specific release. Later preview updates must retain this profile and pass the updater's preflight/full inventory checks. Stop only an idle preview owner through its normal authenticated shutdown before adopting a new preview; preserve any active work.

```sh
augmentor-harness-preview --status
```

This verifies and prints selected release/version/source/hash without starting a Host or model. Selected and running identities are distinct. The private runtime log is `<preview state>/augmentor-pi/runtime.log`. Never share `harness.json`, a real bearer link, API credentials or unreviewed conversation payloads.

## Qualification scope

Runtime implementation **`0ab56432af22ec88a5b5e65e92561ab881f0c5be`** passes the final broad Linux source run: **834 cases/828 passes/six explicit optional/platform skips**, zero failures/cancellations, with two workers and unchanged deadlines. Three provider-compatibility cases pass. A separate ordinary bundled-Node artifact passes **100 cases across nine files**, zero failures/skips/cancellations, with four workers: provider compatibility/scheduling, Host lifecycle, jobs/delegation/specialists, observations, Harness chat and actual Chromium Context. All **351 compiled files** match source; **19,088 dependency files**, **709 license files** and bundled Node remain identical to the preceding ordinary stage. The final preview launcher additionally isolates the native working folder and Linux dictation state; its exact installed source/hash is available through `--status`.

Actual installed MX evidence uses the owner's existing local Qwen route: a synthetic file read returns **infinity**, Trajectory exposes its successful five-millisecond tool record and original payload, and Context shows the successful post-tool request with reported input **7,850**, output **54**, cache read **7,811** and declared capacity **262,144**. These are one request's SDK-normalized values, not a performance benchmark or independent token count. Stop interrupts a visible stream, retains the partial answer marked **ABORTED**, and restores Send/model controls. A subsequent clean conversation reads the same note successfully. Native self-rendering passes, and its actual running window reports online/model-ready with no connection/restoration error. A final clean artifact is being staged after the guard finding below; installed identity/adoption is recorded in the handoff.

Retained qualification failures: using production Python for the broad Qt fixtures fails because that interpreter lacks QtTest (**834 cases/816 passes/12 failures/six skips**); the app itself renders with it. The isolated QtTest environment's first broad run has **834 cases/826 passes/one failure/one cancellation/six skips**, from a native inspector assertion and a startup timeout. Both pass immediately in the five-case focused run. The final two-worker broad run passes as above; contention is a possible explanation, not a proved cause. The initial compatibility fixture's empty tool allowlist refused its own tool; explicitly selecting that synthetic tool corrects the fixture without weakening validation.

The first installed core test command wrote two generated reasoning screenshots into an immutable candidate. **No existing candidate file changed**, but the stable launcher's complete-inventory check correctly refused the extra files. The failed artifact remains preserved; it is not patched in place. The fixture now saves screenshots under its own temporary profile. The corrected 100-case run uses an unselected assembly and leaves its pre-existing historical output inventory unchanged. The clean replacement is staged through the updater, which excludes those historical fixture outputs. This finding is a test-artifact placement error, not a relaxed inventory policy.

For reproduction, build, provide an isolated Python with PySide6 **QtTest**, and run `AUGMENTOR_PYTHON=<test-python> node --test --test-concurrency=2 tests/*.test.mjs`. For the staged scope, set `AUGMENTOR_PI_TEST_ROOT=<ordinary-artifact>` and use its bundled Node with four workers on `pi-provider-compat`, `pi-scheduling`, `runtime`, `pi-jobs`, `pi-desktop-jobs`, `desktop-specialist`, `pi-observations`, `harness-chat` and `harness-context-chromium` (`tests/<name>.test.mjs`). Never run output-writing fixtures against a selected installed artifact.

The preceding product revision `fc0a5b1c2302c5da2ce1f92757373a0aba50cf29` passes Linux source **831 cases/825 passes/six explicit optional/platform skips** and ordinary unselected bundled stage **316 cases/312 passes/four Windows skips**, all zero failures/cancellations. Those historical results do not qualify the added preview launcher or compatibility option. Its actual Windows x64/ARM64 focused runs fail the broader Host job gate; further platform implementation is deferred by the owner's MX-first direction. No complete migration, platform parity or DSH retirement is claimed.

The [Harness contract](AUGMENTOR-HARNESS.md), [migration requirements](AUGMENTOR-HARNESS-MIGRATION.md), [desktop deployment rules](DESKTOP-DEPLOYMENTS.md) and [current handoff](AGENT-HANDOFF.md) retain the broader product scope.
