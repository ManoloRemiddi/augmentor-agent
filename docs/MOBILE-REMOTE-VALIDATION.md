<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->
# Original Desktop remote validation · 2026-09-19

This record supersedes the earlier separate web-chat MVP evidence. The current
preview renders the original installed Qt Desktop through noVNC. Earlier tests of
a custom history/send gateway do not establish behavior of this new transport.

## Tested build and boundary

- Installed Desktop source: `~/.local/share/resonant-voice/augmentor-preview`,
  version 0.2.8, using its existing Python runtime. The running DSH integration
  also reports 0.2.8. The maintained source checkout is 0.2.9, so the launcher
  deliberately uses the installed matching build without altering its files.
- Touch adapter maintained in this repository; applied in memory to the installed
  Window/Composer/Transcript classes. Normal Desktop sizing stays unchanged.
- Node 24.19.0, noVNC 1.6.0 official ESM release, ws 8.21.0, esbuild 0.25.12;
  x11vnc 0.9.17-1 and distro LibVNCServer 0.9.15+dfsg-1+deb13u2.
- One isolated Xvfb display and named `mobile` Desktop window. Main and secondary
  user Desktop processes remain separate. No main-display shadowing is used.

## Automated checks

- **5 web bridge tests:** pairing, rate limiting, Host/Origin/CSRF checks, logout,
  resize bounds, rejected unknown routes, remote HTTPS requirement, unauthenticated
  WebSocket rejection, authenticated binary relay, one-viewer ownership, and
  closing the active stream on logout and rejecting input after pairing expiry.
- **3 touch-layout tests:** unchanged ordinary Desktop button sizes; 44×44 touch
  targets at phone/tablet widths; real native menu handlers; containment of a large
  original dialog without losing its original button.
- **Installed-build event-loop proof:** real Qt event loop remains responsive;
  viewport change from 360×760 to 412×840 applies; Unicode text is preserved;
  composer remains at least 58 pixels tall; primary targets remain at least 44×44.
  This catches a sizing feedback loop found and fixed during integration testing.
- **34 existing Desktop regression tests:** 24 Window tests and 10 message-action
  tests passed. These include the existing native actions and default UI behavior.
- Client build, Node syntax checks, Python compilation and `git diff --check` pass.

The offscreen Qt plugin prints expected warnings about unsupported window-system
operations. They are not counted as proof of real desktop-window integration.
The separate live browser checks below provide the remote rendering evidence.

## Live browser and agent evidence

- The browser paired with the new bridge and displayed the actual installed
  Desktop, with the user's inherited skin, native model picker, toolbar, composer,
  transcript formatting, Thinking row and native message actions.
- Native More options opened with its real Settings, Colors & skins, Prompt library,
  model/setup, approval and license entries. Its position was corrected to remain
  inside the transmitted phone viewport.
- The actual Settings dialog opened remotely. Its original controls remained in
  a scrollable viewport with enlarged touch targets. Existing close buttons are
  reused to avoid duplicate Done controls.
- Keyboard forwarding delivered Unicode (`café`) into the native composer.
  Keyboard helper controls provide selection, backspace and Enter without requiring
  hardware keys. Actual Android IME behavior remains a separate gate.
- A harmless prompt was submitted using the original native Send button:
  “Do not use tools. Reply only: Original Desktop works.”
- The actual agent replied “Original Desktop works.” in the native transcript,
  using the already selected local Qwen model without changing provider selection.
  The synthetic test conversation is retained locally; its identifier is not
  included in the published record.
- Native message Copy reached the remote clipboard; the transport Copy button
  wrote exactly “Original Desktop works.” to the browser clipboard.
- Phone views at 412×915 and 360×800 were visually inspected. The original app
  resized at native scale and kept the composer and toolbar accessible.
- Reloading the browser reconnected using the existing pairing session and showed
  the same completed native conversation, without submitting the prompt again.
- Listener inspection verified the web bridge and VNC server bind only to
  `127.0.0.1`; no VNC IPv6 listener remains. The library's separate IPv6 listener
  required explicit disabling in addition to the application-level IPv6 option.

The preview runs under an independent supervisor rather than a temporary terminal
session. Its private PID/log files are under `~/.local/state/augmentor-mobile`.

## Not claimed

- Core Android emulator interaction passed the accelerated retest below. Full
  acceptance and physical Pixel testing remain pending. Browser viewport tests
  are separate from the recorded Android device tests.
- Private HTTPS passed from the host and emulator. The emulator uses the host's
  tailnet; physical Pixel VPN and Wi-Fi/cellular transitions remain untested.
- Phone microphone/speaker forwarding is not implemented. The visible original
  voice control still targets the host's audio devices.
- Phone file upload/download, mobile screen-reader accessibility, background/radio
  transitions, full dialog-by-dialog parity, and release Android/iOS packaging remain
  separate implementation and acceptance gates.
- Existing host tool behavior is inherited, but correct host browser/display
  targeting still needs remote acceptance tests; an isolated UI display must not
  be mistaken for the intended computer-control target.
- No public production-hardening or full functional parity claim is made merely
  because the original controls are rendered.

See [the revised roadmap](MOBILE-REMOTE-PLAN.md) and
[run instructions](../apps/mobile/README.md).

## HTTPS and lifecycle follow-up

- User configured private Tailscale Serve. Real HTTPS pairing and encrypted
  WebSocket display passed with normal certificate validation; no TLS bypass.
  Live API checks confirmed Secure/HttpOnly/SameSite cookies, occupied-viewer
  rejection, logout and rejection of the revoked session.
- Native More menu responded remotely. A generation revealed an opaque black
  activity-halo overlay on the isolated X display. Added pinned xcompmgr 1.1.8-1
  to provide compositing; the original translucent halo and controls then remained
  visible during generation. The compositor is now supervised with the display.
- Native Stop cancelled a synthetic count-to-10000 response around item 98 and
  returned the native controls to idle. The earlier 500-item test finished before
  cancellation and is not counted as evidence of Stop.
- A second authenticated viewer now receives an explicit occupied-session message
  and a Reconnect control. The bridge contract test covers rejection and release.
- Three keyboard contract tests cover composed Unicode, IME beforeinput deletion/
  Enter, hardware edit-key suppression and discarding disconnected input. These
  tests do not substitute for Android IME acceptance. Client also tracks the visual
  viewport to keep transport controls above software keyboards.
- Per-user systemd service installed, enabled and started. Unit validation passed;
  supervised processes include Xvfb, xcompmgr, original Desktop, x11vnc and Node.
  Graceful restart preserved the native conversation and required fresh pairing.
  No DSH or main Desktop restart was needed. Idle crash recovery was fault-injected by killing only the owned Node bridge;
  systemd restarted the complete remote group. Active-task crash recovery still
  needs separate qualification. Login startup is configured;
  unattended boot before login is not promised.

## Android artifact checkpoint

- Internal Java/WebView APK compiled with Java 21.0.12.1, Android API 36 platform
  revision 2 and Build Tools 36.0.0. Development signature (v2/v3) and zip alignment
  verified. Artifact SHA-256:
  `aacb6b0c6f13bd881309836e61c2eaaa4d2ec3a993cbf286c3c272cdf4dd5b7a`.
- Package `com.augmentor.remote`, version `0.1.0-internal`, minimum API 26, target
  API 36. Uses only INTERNET permission. Cleartext and backups disabled; no
  JavaScript/native bridge or TLS exception bypass. Build is not debuggable.
- This internal build includes the IME inset fix tested below. It is eligible for
  a supervised Pixel smoke test, not a production-qualified release. Physical
  phone audio, clipboard, files, IME and network/lifecycle behavior remain gates.

### Historical software-emulator evidence (superseded by accelerated retest)

The Android 16 / API 36 Google APIs x86_64 revision 7 image booted using Emulator
37.1.11 with `-accel off`, SwiftShader and a Pixel 7 profile. ADB reported
`sys.boot_completed=1`; package installation returned Success; Activity launch
opened the native HTTPS connection screen. Screenshots were inspected locally.
System UI repeatedly reported ANRs and the Bluetooth system process aborted;
these are emulator/system failures, not proof of an APK crash. Performance, full
HTTPS interaction, real IME and lifecycle acceptance are not established by this
limited boot/install/launch check. Accelerated retest is required.

The software-emulator run was stopped after recurrent System UI ANRs interrupted
URL entry on the first connection screen. No Android HTTPS/agent interaction pass
is claimed. The installed AVD/APK remain available for a KVM retest; the host
remote service stays running independently.

### Accelerated Android retest · 19 September 2026

Tested the source change following `7b3205f`, with the APK hash above, against the
same installed Desktop 0.2.8 and running private service. KVM version 12 became
usable after administrator setup. Emulator 37.1.11 / API 36 / Pixel 7 profile
booted in 20.6 seconds, then 18.9 seconds on a second cold boot. This is an x86_64
virtual device using host tailnet DNS, not the user's physical Pixel.

- Entered the HTTPS origin through the native connection form, paired through
  the WebView form, and rendered the actual Qt Desktop with normal TLS checks.
- Found and fixed an API 36 keyboard overlap: edge-to-edge layout left the WebView
  full-height. Including IME insets in its parent now shrinks the remote viewport;
  composer, Send and keyboard helpers remain visible above Gboard.
- Tapped actual Gboard letter and space keys; text reached the original composer.
  Two Gboard backspaces removed the trailing space and character. Select all and
  helper Backspace cleared the test. This is basic IME evidence; accented input,
  suggestions, multiple languages and long composition still need qualification.
- Entered “Do not use tools. Reply only: Android remote works.” through Android
  input, tapped original Send, and received “Android remote works.” from the
  existing selected local model. No model/provider change was made.
- Rotated portrait → landscape → portrait; the original window resized. Pressed
  Android Home and resumed the Activity; the same completed conversation returned
  without another submission. Reinstall and cold boot also retained the origin
  and valid pairing session.
- Tapped native Stop during a count-to-10000 request while the model was thinking.
  The activity halo and Stop control cleared, returning the native window to idle.
- Opened original More → Settings. Its original scrollable controls and Done
  button were visible and Done returned to the conversation.
- The first emulator process exited cleanly during the Settings check. Its log
  shows graceful shutdown, not an app-crash report; cause is unconfirmed. Restarted
  independently of the command session and completed the Settings check. No
  long-duration emulator stability claim is made.
- Rebuilt APK signature/alignment passed; all eight bridge/keyboard contract tests
  passed again. Native source was unchanged by this Android-only fix.
