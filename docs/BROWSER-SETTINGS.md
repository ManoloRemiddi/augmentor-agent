<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Browser Settings

The browser toolbar keeps New chat, Save, History and Settings, with harness selection available only in Settings. The quick model picker remains below the composer. Colour sliders show their full hue or brightness gradients.
Settings opens an extension-owned browser tab with Colours, Models, Harnesses,
Prompt library, Memories and Support. Repeated and concurrent requests reuse
that tab. Chromium's extension Options command opens the same Settings page.

Settings reuses the existing forms and native message API. Forms appear in
normal page flow using nonmodal dialogs; switching sections keeps their DOM and
unfinished edits. Closing or reloading the page discards unsaved edits. Saving a
model or DSH connection refreshes its form. DSH provider management still opens
DSH's own interface from Models. Pi model setup is embedded in Models. Existing model connections show first; adding another model and provider tuning use expandable sections.

The prompt library and Hindsight settings continue to use the shared services;
there is no separate browser copy of that data. Colours use the existing
extension storage keys. The chat and Settings share theme tokens and base CSS;
storage events apply colour changes to open chat pages. Browser-control overlays
read the mirrored Chrome storage values. Support provides the private preview's
installer update information and the existing downloadable diagnostic report.

## Verification

- `AUGMENTOR_PROOF_SETTINGS=1 python3 scripts/browser-composable-proof.py`
  checks real mouse navigation, tab reuse including concurrent callers, chat
  draft preservation, live and persistent colours, light-theme text tokens,
  inline forms, section draft preservation, Pi/DSH model views and narrow layouts.
- `AUGMENTOR_PROOF_FRESH=1 AUGMENTOR_PROOF_HEADED=1 xvfb-run -a -s
  '-screen 0 1280x1000x24' python3 scripts/browser-composable-proof.py`
  checks new-user model setup in Settings, a real Pi SDK browser task using a
  deterministic model endpoint, clipboard/scroll, edit/branch, prompt revision
  conflicts, clipboard templates and the downloaded support report.
- `DSH_TEST_MODULES=<DSH profile node_modules> AUGMENTOR_PROOF_BROWSER=1
  .venv/bin/python scripts/dsh-setup-proof.py` exercises the actual DSH SDK and
  browser Settings connection form with a disposable DSH home and model fixture.

The 0.2.4 Settings baseline also passed against its packaged ZIP and installed
companion. The 0.2.5 onboarding changes passed against source with isolated
configuration and data; packaged native onboarding files were then checked byte
for byte against the tested source. Host installation of 0.2.5 is complete, including the browser extension and
DSH browser integration. See `REPLY-COMPLETION.md` for the final desktop checks.
Evidence is in `outputs/browser-settings-proof.json`,
`outputs/browser-composable-proof.json` and
`outputs/browser-dsh-setup-proof.json`. This UI preview retains protocol and
companion version 0.2.5; `outputs/browser-0.2.5/artifacts.json` records its
source revision, dirty status and exact file hashes.

## Agent-led memory onboarding

Memories starts with **Set up with Augmentor**. Manual configuration and stored
memory management remain in a collapsed Advanced section. The setup button sends
only a fixed topic and request ID to the companion, which acknowledges a handoff
to Augmentor Linux. The Linux UI uses its existing selected harness and model,
starts a separate conversation, and supplies a setup brief that directs the agent
to inspect services and configuration, choose technical defaults, and use the
shared memory service's checked configuration API. Browser conversations retain
their browser-only tool boundary.

Setup refuses to interrupt an active Linux action or discard an unfinished
composer draft. A persisted receipt prevents a repeated click or lost reply from
replaying setup. The receipt records dispatch, not proof that Hindsight has been
installed; the agent verifies and reports the actual outcome in its conversation.
The model needs to be configured before it can guide onboarding. Missing service
credentials, paid-provider choices, OS authentication and external failures can
still need the user's involvement. The app supplies instructions and OS tools;
it does not claim that every model will complete every Hindsight deployment.

`AUGMENTOR_PROOF_SETTINGS=1 AUGMENTOR_PROOF_ONBOARDING=1 .venv/bin/python
scripts/browser-composable-proof.py` tests the actual browser button, native
companion, Linux UI, Pi SDK and OS tool against a deterministic model fixture.
The fixture calls `memory.describe` through the real shared service, returns a
question about the missing service, and verifies that Continue reuses the session.
It does not install Hindsight or change the user's memory configuration. Unit
coverage additionally checks busy/draft protection and persisted deduplication.
