<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Agent Desktop and Browser on the personal Air — October 20

The MacBook Air now runs **Applications → Augmentor Agent Desktop**, product
**0.2.13**, source **dc87d48e**, with **Augmentor Harness** as its default.
The application hosts the Browser extension too; a second large companion
application is unnecessary for this installation. The separately installed AH
runtime remains **44ae92b3 / 41629b72…64134**, including its existing Wiki/research
components and private profile. No Mac Mini or MX application was changed.

The signed development package is **7b7c1bb0…11cab2**; application inventory
**7e2b7475…115fca** verifies all **2,845** listed inputs. Source strict check/build,
132 Mac tests, 40 focused Python checks and 39 SDK/Browser cases pass. Exact
sealed candidate qualification passes **27 Python / five Node** cases and strict
code-signature verification. The actual installed native process then receives
a real configured-provider reply through its composer and Send button. Normal
Applications reopening restores the same AH conversation/model, is online and
model-ready, and has test controls disabled. The app's captured window was
visually inspected. One labelled installation-check conversation remains.

The live check first reproduced an adapter gap: this Air's newer owned
LaunchAgent uses `bin/start-harness` plus private `bin/environment.sh`, rather
than an EnvironmentVariables dictionary. The resolver now accepts both formats,
parses only known connection paths without executing shell code, and normalizes
the owned shared IPC path. Dynamic expressions/unsafe files fail closed. Actual
owner directory/version attestation still precedes requests. The initial offline
Desktop did not send a prompt and its superseded application backup was removed
after the corrected installation passed. See [connection behavior](AH-DESKTOP-BROWSER.md).

Existing AH histories, default model, owner PID and browser address verify
preserved. AH itself was not replaced or restarted. Temporary source, dependency
environment, candidates and duplicate build archives were removed; the working
application, prepared extension and small private qualification receipts remain.
The original AH startup/recovery jobs are retained. A physical reboot, voice
and broader desktop-control permission flows were not tested here. This is a
personal ad-hoc development install; it publishes no new public download and
makes no notarization claim. Mac supplier notices remain separately attributed.

## Comet: installed and tested in the owner's browser

Comet's native messaging registration targets the installed Applications bundle,
including its existing Chrome-compatibility registration location. The actual
signed browser-host executable selects AH and initializes against its real
model catalog without a new Browser prompt or conversation. The installed
extension defaults to AH while retaining explicit saved choices.

The first attempt stopped at macOS's assistive-access restriction. Once that
permission was available, the ordinary Comet installation was completed through
its actual Extensions page and folder chooser. The hidden hashed Library path
was unnecessarily difficult for the owner to find. This installation instead
loads from the clearly named **Desktop → Augmentor Browser Extension** folder.
Its 67 files match the extension in the signed installed application. This is
the live extension source, so retain that folder; future updates must explicitly
update/reload the loaded copy rather than only prepare another hidden folder.

**Augmentor Agent** is loaded, enabled and pinned in Comet. Actual sidebar
accessibility controls show Connected and the configured model; Settings shows
**Augmentor Harness · Connected**. A prompt entered in the real sidebar composer
and submitted through its Send button returns **AH BROWSER READY** from the
configured provider. Hiding the sidebar and reopening it with the pinned toolbar
icon restores that reply, Connected status and an empty, usable composer. One
marked Browser verification conversation remains alongside the earlier native
installation check. Desktop remains online and model-ready.

Private receipts record the loaded profile/path, matching file hashes and actual
UI results. The browser's own metadata confirms the visible folder is loaded.
No browser security database or signed application was edited to bypass approval.
This qualification uses actual accessibility controls; a screen capture was
unavailable and no screenshot inspection is claimed. Full browser restart and a
physical reboot were not performed in this follow-up.

## Repository synchronization

The active implementation is pushed to [PR #45](https://github.com/ManoloRemiddi/augmentor-agent/pull/45).
The completed Mac plugin and research implementations are also durable in
[PR #51](https://github.com/ManoloRemiddi/augmentor-agent/pull/51) and
[PR #52](https://github.com/ManoloRemiddi/augmentor-agent/pull/52).
An audit found no additional unpublished implementation commits outside existing
remote refs; local stash records remain local.

The old canonical `main` working checkout still contained 38 modified/new source,
test and documentation files. They were credential-pattern/syntax/whitespace
reviewed and preserved at **7c46b29d** on
[archive/local-application-work-20261020](https://github.com/ManoloRemiddi/augmentor-agent/tree/archive/local-application-work-20261020),
without changing that checkout or its index. This historical snapshot is not a
qualified candidate or a merge of older UI over current behavior. Feature work
remains on its existing branches; no main merge or public binary release was
performed by this installation.

[Portable qualification record](../release/macos-ah-agent-air-20261020.json).
