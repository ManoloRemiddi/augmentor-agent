<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->
# Internal Android host

This thin Java Activity hosts the exact remote Desktop web surface in Android
WebView. It introduces no chat, model, history or settings implementation. The
only native setup screen asks for the computer's HTTPS origin; the existing
pairing form then authenticates the device. UI updates are served by the computer.

The app requires Android 8 or newer and a current Android System WebView. The
first qualification target is Android 16 / API 36, followed by the user's Pixel.
The computer and a physical phone must be connected to the same authorized tailnet.

## Build

Use Java 21 and Android Command-line Tools 22.0. The inspected Linux archive
`commandlinetools-linux-15859902_latest.zip` has SHA-256
`4e4c464f145a7512b57d088ac6c278c03c9eea610886b35a5e0804e74eedf583`.
Install these official SDK packages into `~/.local/share/augmentor-android/sdk`:

```sh
SDK="$HOME/.local/share/augmentor-android/sdk"
"$SDK/cmdline-tools/22.0/bin/sdkmanager" --sdk_root="$SDK" \
  'platforms;android-36' 'build-tools;36.0.0' 'platform-tools' \
  'emulator' 'system-images;android-36;google_apis;x86_64'
python3 apps/mobile/android/build.py
```

The small internal build uses the official aapt2 → javac → d8 → zipalign →
apksigner pipeline without Gradle or third-party Android dependencies. It builds
`apps/mobile/android/build/augmentor-remote-internal.apk` and verifies its signature
and alignment. SDK Build Tools are pinned to 36.0.0 and platform API to 36. The
SDK's mutable package revisions must be requalified when updated. See the current
[validation record](../../../docs/MOBILE-REMOTE-VALIDATION.md) for installed
versions and the boundary between build checks and device acceptance.

The development signing key lives outside the repository in the private remote
state directory. Its conventional development password is not a release secret.
Do not distribute this identity as a production signing key. A release build,
signing/updates and Play distribution remain later gates. The APK is not debuggable.

## Isolated emulator

```sh
python3 apps/mobile/android/start-emulator.py
# Only when KVM is unavailable, for a slower diagnostic boot:
python3 apps/mobile/android/start-emulator.py --software
```

The launcher creates an isolated `augmentor_pixel_api36` AVD using the Pixel 7
profile, fixed port 5580, software graphics and the host tailnet DNS. It neither
wipes user devices nor changes system networking. `--window` shows the native
emulator window. Headless mode can still be inspected with ADB screenshots.

After boot, use the specific device serial:

```sh
SDK="$HOME/.local/share/augmentor-android/sdk"
"$SDK/platform-tools/adb" -s emulator-5580 shell getprop sys.boot_completed
"$SDK/platform-tools/adb" -s emulator-5580 install -r apps/mobile/android/build/augmentor-remote-internal.apk
"$SDK/platform-tools/adb" -s emulator-5580 shell am start -n com.augmentor.remote/.MainActivity
```

The emulator uses the host's tailnet connection. That is not evidence of a physical
phone's VPN or cellular behavior. Hardware acceleration requires a usable `/dev/kvm`;
installation or an AVD definition alone is not a passing boot/device test.

## Lifecycle and boundaries

- Only HTTPS is accepted. Cleartext traffic, mixed content, local file/content
  access and third-party cookies are disabled; there is no native JavaScript
  bridge or certificate-error bypass. Navigation stays on the configured origin.
- Backgrounding releases the remote view; foregrounding reconnects to the same
  native session. No saved keystrokes or tasks are replayed. Rotation preserves
  the WebView instance. Rotation and background/resume passed the API 36 emulator;
  physical-device acceptance remains pending.
- System-bar, cutout and IME insets constrain the WebView on API 30+, including
  enforced edge-to-edge layouts on API 35+. The original composer remains above
  the keyboard. Older Android versions remain unqualified.
- Only the origin is stored in private app preferences; pairing uses the server's
  HttpOnly cookie. Android backup is disabled. Back offers connection settings
  without sending a task cancellation.
- Phone microphone, speaker, files, WebView clipboard compatibility, accessibility
  and real IME/radio transitions remain acceptance/implementation gates. The
  visible voice control currently uses the computer's audio devices.

[Android WebView](https://developer.android.com/develop/ui/views/layout/webapps/webview),
[AAPT2](https://developer.android.com/tools/aapt2),
[APK signing](https://developer.android.com/tools/apksigner),
[emulator acceleration](https://developer.android.com/studio/run/emulator-acceleration).
