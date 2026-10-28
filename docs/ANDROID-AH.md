<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->
# Android Agent connected to the existing Augmentor Harness

The [responsive tablet Harness](TABLET-HARNESS.md) supersedes the separate Agent presentation below. The October 22 qualification remains historical evidence.

This is an opt-in browser presentation preview, not a new session engine or a
native Android APK. AH remains the sole owner of sessions, tools, selected model,
approvals and running work. The Android and desktop views attach to the same
native conversation; transcripts are not copied into a new agent. The EDGE
adapter is a design reference only; no private EDGE source/assets were copied.

The preview reuses the existing Harness React conversation, session navigation,
model picker, attachment/draft lifecycle, tools, questions and approvals. Its
Agent composer adds three larger Talk / Send / Improve seats, a connection
indicator, exact-session identity and explicit reconnect. It adapts to Android's
visual viewport/keyboard. Dictation uses the existing recognition bridge and
requires browser microphone permission; it has not been acoustically qualified
by the continuity test. It is not the former Qt/VNC mobile remote surface.

## Host and authority

`apps/mobile-ah/connection.mjs` uses the existing installed-AH resolver and an
attested IPC handshake to obtain the current owner's loopback carrier. It checks
reported version/config/state identity before obtaining the connection. It never
starts a fallback/empty profile, invokes a model, or opens a second SDK owner.
Changing/restarting the AH owner requires an explicit mobile-service restart.

The mobile service listens only on `127.0.0.1`. It accepts exact declared Host /
Origin pairs, rejects cross-site API access, bounds request bodies, and pairs
through a private owned key. Pairing gives operator access to the selected AH
profile, not merely one conversation. Existing session permission modes still
apply. The AH bearer stays in the computer process; the phone receives only a
12-hour HttpOnly/SameSite=Strict pairing cookie, Secure on HTTPS. Logout, expiry
and service restart revoke access. Five failed pair attempts per minute are
admitted. No proxy target, upstream Authorization or arbitrary file path can be
supplied by a browser. This is a single-owner preview, not multi-user isolation.

Only fixed API carriers and the reviewed build asset manifest are served. Some
advanced full-Harness operations, including session ZIP export and nested HTML
inspectors, are intentionally not exposed by this first carrier and fail visibly.
No claim of complete desktop surface parity is made. Keep the original AH browser
available for those operations. PDFs/Office, attachment combinations, model-account
sign-in and physical speech need their own Android acceptance.

## Continuity and no replay

The shared controller uses AH's durable request IDs, queue receipts, subscription
cursors and historical read models. Reconnect only reattaches and reads; it never
retries a prompt, action, approval response, upload or unknown mutation. A single
submission gate prevents overlapping touch/keyboard admissions. A requested missing
Android conversation fails explicitly instead of falling back to another session.

AH persists text, attachment receipts and prepared submissions. Pristine
composers now read peer draft revisions; a concurrent local edit, late read or
session switch cannot overwrite retained local text. A failed/unconfirmed save
keeps its existing blocked-draft warning; copy unsaved text before reloading that
page. Concurrent differing edits are not silently merged or promised lossless
under arbitrary browser termination. The older already-installed AH frontend
requires a reload to read another device's draft; the new shared source adds live
peer reconciliation. Loading this preview does not replace that installed build.

Closing a phone page does not cancel AH work. Stop is an explicit AH operation.
After interrupted or unknown delivery, inspect AH's saved state; never resend
merely because the view disconnected. The computer must remain awake/reachable.

## Build and run

Use locked root and Harness UI dependencies matching `package-lock.json`. On MX,
run the build through the managed workspace helper with its unchanged 64-GiB
reserve, choosing storage with adequate room:

```sh
python3 -B scripts/harness-build-workspace.py --root /PATH/TO/PRIVATE/BUILD-STORAGE -- \
  python3 -B scripts/build-mobile-ah.py --dependencies /PATH/TO/MATCHING-CHECKOUT \
  --output /PATH/TO/NEW-MOBILE-CANDIDATE
```

This builds/checks shared source in disposable scratch, runs the focused tests,
and retains only browser assets, their notices, the small carrier/resolver and a
SHA-256 manifest. It neither rebuilds nor activates the installed AH. If cleanup
is retained for a still-exiting caller, inspect the workspace marker and live
references before removing that exact scratch; never lower the reserve.

From that candidate directory:

```sh
AUGMENTOR_MOBILE_AH_ASSETS=/PATH/TO/NEW-MOBILE-CANDIDATE/web \
  node apps/mobile-ah/server.mjs
adb reverse tcp:8767 tcp:8767
```

Open `http://127.0.0.1:8767/agent` in phone Chrome and enter the key from the private
`~/.local/state/augmentor-mobile-ah/pairing-key`. Never publish it. An explicit
session link uses `/agent#session=SESSION_ID`. Session switching also works from
the shared navigation. Authorize USB debugging normally; root/unlocking is not
required. USB forwarding works only while the cable/debug connection remains.

For private wireless/away access, configure the service's
`AUGMENTOR_MOBILE_AH_ORIGINS` as a JSON array including the exact HTTPS origin,
then have the desktop administrator add a dedicated Tailscale Serve HTTPS route
(e.g. port 8444 to `http://127.0.0.1:8767`). Preserve existing Serve routes; do not
use public Funnel or expose the underlying AH port/bearer. The phone must be
connected to the authorized tailnet. TLS/VPN and cellular-transition acceptance
are separate from USB acceptance. No phone VPN/account changes are automated.

The carrier is portable Node/browser code and reuses the Linux/macOS resolver.
The 22 October installed preview runs as a separate Linux user service; AH and
existing Desktop/EDGE/VNC services are unchanged. This service is a session-local
preview, not a login/reboot installer. macOS source support is inherited, not
physically qualified; Windows discovery remains unsupported by that resolver.

## Qualification — 22 October 2026

Base source: `efd85b83` in the canonical application repository. New work is on
`feat/android-ah-continuity`. The real Pixel 7a reports Android 17; Chrome, a
physical USB cable and the already-installed AH 0.2.13 were used. A labelled
isolated workspace/session used the existing local Qwen route, with Ask before
actions. Global permissions, models, GPU placement, owner conversations and
installed AH selection were not changed.

The physical proof:

1. Desktop AH submitted one prompt and approved one scoped marker write. The
   assistant returned `DESKTOP READY`.
2. The Pixel opened that exact session and recovered its history. A continuation
   typed on the Pixel was recovered as an unsent draft by the desktop AH after
   reload, without admitting a prompt.
3. Send was selected once on the Pixel. Its single tool proposal was approved
   once there. The tool slept for 15 seconds and appended the second marker.
   USB forwarding was removed after approval; the phone page was refreshed while
   forwarding was absent, then forwarding was restored and the page reopened.
4. Desktop AH reopened the same session. A new desktop draft appeared on the
   updated Pixel without reload. Desktop sent it; without tools, the model named
   both markers and ended with `BACK ON DESKTOP`.
5. The saved history contained three human messages, two tool calls, two tool
   results and three completed turns. The file contained exactly `DESKTOP-ONE`
   and `PHONE-TWO`, each once. Final packaged-client reopening retained them and
   admitted no extra prompt. This is bounded test evidence, not a guarantee about
   arbitrary tool exactly-once execution during every possible failure.

The final packaged client also received two rapid Send touches for one tool-free
`FINAL VERIFIED` request. AH admitted exactly one additional human message and
no additional tool call: final totals were four human messages, four completed
turns and the same two tool calls/results/marker lines.

The focused artifact cohort passed **28 tests**, with no failures/skips.
[Portable qualification receipt](../release/android-ah-continuity-20261022.json).

Authored tests cover lost accepted replies, private/expiry/origin/path boundaries,
rapid submission admission, wrong-session refusal, peer drafts, late local edits,
SDK/HTTP durable drafts and original browser access. Full TypeScript and browser
build passed. The reviewed supplier package retains its pre-existing duplicate
Office dependency-key warning; supplier bytes were not modified. Build and test
logs/private profile bindings/transcripts remain outside the public repository.

Native floating-desktop handoff, a signed Android APK, reboot availability,
physical speech, real radio/cellular transition, all original menus and installed
macOS/Windows acceptance are not established by this proof.
