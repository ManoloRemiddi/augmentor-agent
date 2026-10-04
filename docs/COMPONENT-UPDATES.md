<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Component update controls — October 4, 2026

The user requested an optional automatic-install setting with individual choices
for Augmentor Agent, DSH, Pi, Codex and future connected harnesses. They confirmed
that no Apple Developer account or Windows signing certificate/service is
available and asked us to choose a stable, secure release process with low friction.

## Current implementation

Desktop Versions & updates and Browser Settings → Updates share four Boolean
component choices. The main automatic-install setting remains separate. Defaults
allow Augmentor when that main setting is explicitly enabled, while harness
choices start off. Existing bundle-wide installation consent is reset during
migration; it cannot silently become permission to update every harness. An older
surface can save the common preferences without erasing the component choices.

The release builder stages `release/update-components.json` before payload sealing.
It records reviewed DSH/plugin-lock inputs, the Pi runtime dependency closure and
the separate Codex prerequisite. Versions alone do not identify a change. The
component digests describe reviewed build input contracts, not standalone binary
attestations; signed artifacts and complete payload inventories authenticate the
actual bytes. Nested npm records without an equivalent hashed record bind the
whole reviewed lock conservatively, so unrelated lock changes may also defer Pi.
No registry lookup, global installation or upstream execution fills missing data.

Signed catalogs may carry the matching `updateComponents` contract. The live
installer requires complete source/target identities and current component consent
at verification, preparation and immediately before installation. Consent revoked
during a network refresh refuses. Changed installed contracts also refuse. Mac and
managed Linux compare the staged target contract before any source drain. Windows
package intake requires a valid contract; its external installer trusts the signed
artifact and publisher declaration. Publisher qualification must derive the catalog
contract from the exact built payload, never hand-copy versions from another build.

| Component | Current installation ownership | Automatic behavior in this checkpoint |
| --- | --- | --- |
| Augmentor Agent | Complete application release | Turning its choice off defers whole-application automatic installation. |
| DSH | Bundled tested runtime and plugins | A changed DSH input contract requires its own enabled choice as well as Augmentor's choice. |
| Pi | Bundled tested runtime and dependency closure | A changed Pi input contract requires its own enabled choice as well as Augmentor's choice. |
| Codex CLI | Separately installed, exact tested prerequisite | Stores the choice but cannot execute a standalone updater yet. A changed prerequisite defers the application update and requires separately verified installation. |

These controls enforce permission within the existing complete-release controller.
They do **not** yet implement harness-only downloads or independently installed
harness slots. Selecting only DSH/Pi/Codex while Augmentor is off does not start a
whole-bundle update. Other harnesses need a reviewed registry entry, discovery,
compatibility and ownership adapter before a toggle can authorize installation.
No remote metadata can invent an executable or an arbitrary update command.

## Release process decision

Use GitHub Actions for repeatable builds/tests and ordinary release publishing.
Keep offline root recovery keys outside Actions. Give signing/publishing separate,
minimal-permission jobs against reviewed source; use protected release environments,
immutable action references and short-lived provider authentication where supported.
Do not give fork or ordinary build jobs release credentials. Automated checks should
notify users only about published compatible releases, not every repository commit.

This recommendation follows GitHub's [workflow security guidance](https://docs.github.com/en/actions/reference/security/secure-use),
including immutable actions, least privilege, protected environments and OIDC.
It is our selected deployment design, not a claim that production accounts, keys
or a signed feed have been provisioned.

For frictionless direct Mac distribution, set up Developer ID signing and Apple
notarization through the owner's Apple Developer Program account; Apple's
[Developer ID guide](https://developer.apple.com/developer-id/) describes that path.
Windows needs an explicitly provisioned publisher identity for the existing native
signature gate. Until these prerequisites and real signed forward acceptance are
complete, keep platform automatic-install qualification disabled and provide manual
installation instructions. Do not bypass OS protections or remove publisher checks.

Codex's [official CLI documentation](https://developers.openai.com/codex/cli/) provides
its supported installation/update methods. Its independent adapter must detect the
actual owner and method, update only compatible tested versions, wait for active
work, preserve authentication/settings and verify readiness. It must not update the
Codex desktop app or somebody else's global package as a side effect.

## Verification and remaining work

Portable consent tests use private actual files and inert downloads; they cover
unchecked changed bytes, allowed bundled updates, in-flight revocation, changed
source contracts, mismatched staged targets, legacy migration, external Codex refusal
and unknown/non-Boolean choices. Desktop and Browser tests verify independent
choices, offline operation, conflict preservation and readable compact layout.
Host updater suite passes 280 cases with seven explicit platform/context skips.
The Node repository/Browser checks pass sixteen cases, Windows package intake
passes seven, and type checks pass. The compact native form was rendered and
inspected; it scrolls rather than clipping version information, with Done fixed
outside the scrolling body. These checks are distinct from actual signed forward
OS installation. Native qualification of this new source remains required.

Remaining work includes independent harness release catalogs/immutable slots and
lifecycle adapters, actual installation-method detection for external Codex and
other harnesses, component-aware release publication validation, native packaging
qualification of these new contracts, and real signed forward acceptance. Production
feed/root provisioning and Mac/Windows signing remain owner setup requirements.
No owner's running application, harness installation, profile, model or GPU has changed.

See [the full updater record](UPDATE-SYSTEM.md) for exact tested refs and prior
platform evidence; earlier native passes do not qualify this component follow-up.
