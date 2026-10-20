<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Harness installation defaults

Harness includes Metafolder, the shared Prompt library, in-input prompt
improvement, Model Picker, Context Insights and Adaptive Reasoning. They are
application components, not separate DSH servers to install alongside Pi.

New Linux and macOS Harness profiles enable Metafolder grouping and keyless Web
Search/Fetch. Initialisation runs only for a Harness profile without existing
conversations. The installer helper creates missing private configuration records;
existing enabled/disabled choices, groupings, credentials, models and prompt
content remain byte-for-byte intact. An operator can explicitly provision missing
defaults for an existing, backed-up profile:

```sh
AUGMENTOR_PI_CONFIG=/absolute/private/profile node scripts/install-harness-defaults.mjs
```

This helper does not restart or reload an owner. Apply changes through the
existing guarded lifecycle; finish active work and send or clear drafts first.
Never edit a selected application artifact in place.

| Component | Default and location |
| --- | --- |
| Metafolder | Enabled in new profiles; **New meta folder** in the workspace sidebar. Existing groups are preserved. |
| Prompt library | Built in; **Settings → General → Prompt library**, or the prompt command. A fresh library has no personal saved prompts. |
| Improve prompt | Built in; the **✦** control inside the input. Enabled for an eligible non-empty draft in an idle connected conversation. Its result stays a draft; Undo restores the original wording. Instructions are in the library's **Improve prompt** tab. |
| Web Search/Fetch | Keyless mode enabled in new Linux/macOS profiles. Original provider forms, revision checks, same-owner reload, cancellation, public-address checks and pinned DNS remain. Optional API credentials are configured separately. |
| Models | Existing provider configuration and model choices are preserved. Machine-specific local endpoints and credentials are private installation state, never release defaults. Adding local providers does not select a new conversation model. |
| Wiki Tools/Skills | The earlier defaults update left these Linux-only. The subsequent macOS filesystem/receipt adapter is now carried forward in the [research installation](WEB-RESEARCH.md#installed-acceptance--20-october-2026); research acceptance does not replace live Wiki qualification. |

The web Harness is an interface to the existing Pi owner. Its native-workspace
conversations can use Search on Linux and macOS. Browser-extension conversations
keep their separate browser tool/resource boundary; this change does not grant
them native tools.

## Qualification on October 20, 2026

The macOS candidate passes strict source check/full build and 40 focused tests
covering installation defaults, saved Search choices, credentials, unsafe/linked
records, cancellation, network limits, original provider bindings, plugin controls,
authenticated browser access and real Host restart. The same 40 tests and full
check/build pass on Linux in the required disposable build workspace.

macOS live keyless search returned public source links and public page fetching
completed. Two pre-existing local provider declarations were privately transferred
without changing their model/context/output configuration; both advertised their
configured model and returned a real connection-check reply from the Mac. The
existing chat model was preserved. Metafolder was enabled through its revisioned
API, and the actual Harness interface exposed the creation control. The original
Prompt library and Improve prompt controls were inspected in that same interface.

Mac test fixtures now resolve the operating system's temporary-directory alias
before using the private configuration store. Runtime path checks were not
weakened. Broader packaging, Windows, physical voice and Wiki qualification remain
separate. An expanded focused run passes **53/53 on macOS** and **52/52 on
Linux**, including cold grouping retention and input rewrite/Undo. The additional
Mac SDK/native prompt-improvement proof passes; the available Linux Python lacks
QtTest, so that one native proof is not counted as a Linux pass. Three broader
Mac browser/desktop-adapter leaf failures reproduce with both the candidate and
the preceding installed application; this change does not qualify those adapters.
Installed activation and owner-state preservation must be recorded independently
of candidate tests.

Session review also identified excessive source-code discovery and an overstated
memory-isolation claim. A workspace-local knowledge base and a globally registered
skill are not an OS access boundary. Future agent guidance should distinguish
storage separation, resource discovery and enforced isolation, and consult the
product guide before exploring installation internals. Private owner transcripts
and knowledge content are not test fixtures or publication inputs.
