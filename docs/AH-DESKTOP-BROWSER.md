<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Select Augmentor Harness in Desktop and Browser

Desktop **Settings → All → Connections & Home → Agent engine** and Browser
**Settings → Harnesses → Browser harness** offer **Augmentor Harness** (`ah`),
**DSH**, the retained **Pi (legacy profile)** and Codex development integration.
The previous choice remains selected until the user changes it. A busy or
mutating conversation cannot switch owners. Workspace-embedded Browser profiles
keep their registered engine and do not acquire standalone harness switching.

AH is the installed Augmentor Harness, not a renamed legacy Pi installation.
On MX, the connection follows the existing login controller's explicit review
selection and verified launcher. It uses that entry's socket, model catalog,
working folder and shared prompt/memory stores. On macOS, the adapter reads the
installed `com.augmentor.Harness` LaunchAgent's explicit environment and current
release selection. That adapter has authored metadata-fixture coverage; physical
Mac Desktop/Browser adoption is not qualified by the MX proof. Windows discovery
and installed adoption remain a separate platform gap.

Before any action, the client performs the Pi protocol handshake and compares
the owner's reported profile directories and product version with the selected
AH. Native reconnects revalidate selection; Browser pins its selection for the
connection. Missing/changed installations and mismatched owners fail visibly.
Only a connection failure during health/startup can invoke the existing AH
launcher. No conversation operation is retried, no bearer is copied into browser
storage, and an unavailable AH never creates an empty legacy Pi profile.

Desktop stores its current AH conversation under that AH state's
`clients/desktop/session.json`, with existing per-window scoping. Browser uses
separate `-ah` session/model keys; old DSH, Pi and Codex keys are retained.
Switching engines does not migrate or replay a conversation. The Pi SDK remains
the one execution owner; the surface adapter does not introduce a second loop.
Existing AH surface presets retain their supported `augmentor-*-pi` identities.
Library and memory clients use AH's shared stores; memory provenance continues
to use the owner's `pi:` conversation identity. Plugins still execute under AH's
capabilities and surface policy; adding a backend does not expose every plugin
GUI inside the floating app or Browser sidebar.

The explicit `AUGMENTOR_AH_CONNECTION` operator adapter accepts a private owned
`augmentor-ah-connection/1` JSON record containing `root`, `version` and `profile`
(`config`, `state`, `socket`, `workspace`, `sharedState`, `sharedData`). It contains
no credentials and cannot specify an arbitrary startup command. Such profiles
must already be started by their owning installer. It is used for authored
integration fixtures, not as a substitute for normal installation discovery.

## Qualification on October 20, 2026

Source checks include strict TypeScript validation, private IPC wrong-owner and
changed-selection refusal, missing/offline-profile no-fallback, preference/chat
restoration and separate Browser engine keys. An actual Qt composer and Browser
native-messaging bridge both obtain replies through the supported Pi SDK and an
authored local provider, then restore without another request. Both use the same
owner PID. These are real SDK/transport tests with synthetic model responses,
not claims about physical voice or arbitrary provider compatibility.

The actual registered MX AH additionally passed metadata-only profile, catalog,
history and prompt-library reads without generating an owner conversation.
Installed activation is recorded separately below; source changes alone do not
change the working Desktop, loaded Browser extension or selected AH artifact.

## Preserve the current MX application contract

The working Desktop is product **0.2.11**, with a retained direct Handy overlay,
whereas the Harness source branch is **0.2.13**. Replacing the whole application
would break its matching DSH integration contract. The bounded
`scripts/ah-surfaces-compat.py` recipe instead accepts exactly the recorded
`90bc1347…c9d9669f` base and ports the selectable AH client paths. It preserves
the old release/extension versions, DSH integration, legacy runtime, voice/Handy
dependencies and all unrelated application bytes. The recipe requires the
managed scratch workspace and must pass exact-candidate checks before normal
immutable deployment staging/activation. It is not a general version bypass.
