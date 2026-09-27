<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Shared desktop flare fidelity

The owner's subsequent outline report and native shadow correction are recorded
in [September 27 transparency and app size](MACOS-APPEARANCE-2026-09-27.md).
The historical throughput checks below did not establish visual acceptance.

Current implementation: [Mac recovery and the shared Metal/OpenGL renderer](MACOS-RECOVERY-2026-09-26.md). The CPU renderer below remains the fallback.
The following records describe the earlier correction and its historical installation.

The September 26 macOS report exposed a shared renderer defect: a 744 × 804
logical-pixel canvas used a 186 × 201 emission texture. The finest arch strands
are about 1.6 logical pixels wide, smaller than its four-pixel sampling interval.
Bilinear enlargement cannot recover detail never sampled. Enlarging the whole
fluid solver from 37,386 to 598,176 cells took its isolated step from about
8 ms to 122 ms on the test Mac, before drawing the emission.

`activity.py` now evaluates the same seeded noise and arch equations with NumPy
arrays. The emission uses one sample per logical pixel at 1× display density,
modest supersampling up to 1.25× at higher density, and an approximately one-million
sample ceiling for large windows. Density is in the geometry cache key. This is
intentionally bounded CPU rasterization, not a claim of full physical-resolution
rendering at every display size. Qt maps the explicit destination rectangle to
the display backing store; see [Qt high-DPI image semantics](https://doc.qt.io/qt-6.8/highdpi.html).

The existing smaller fluid grid still owns broad pointer interaction and
world-space smoke transport. After transport, the renderer restores the emission
detail that downsampling removed, in premultiplied RGBA, and clamps colour to
alpha. Fine current strands resolve independently of the transport grid; detached
smoke retains the existing broad transport. This is a visual multiresolution
approximation, not a change to a physical plasma solver. Bounds, window ownership,
input transparency, colour equations, glyphs, flare frequency, lifespan, idle
shutdown and the interior smoke effect retain their existing design. The code
has no macOS/Linux branch and changes no interface layout or controls.

## Validation

The six new activity checks cover scalar/vector noise equivalence, two-pixel
emission recovery, detached smoke, display-density cache changes, large/resized
windows, pointer stirring and valid translucent borders. Together with the
existing four fluid and 25 window checks, all 35 pass on Linux and macOS.
The initial Linux runtime lacked QtTest; validation used a separate temporary
Qt 6.8.2.1 environment, leaving installed dependencies unchanged. A test-only
borrowed-image lifetime error was corrected before the passing runs.

`python -B scripts/flare-fidelity-proof.py APP_ROOT OUTPUT_DIRECTORY` generates
seeded fixture captures using the actual QWidget surfaces, with no live agent,
user state or focus activation. On the 32 GB Mac, Cocoa reports a BenQ display
at 1×: emission changes from 186 × 201 to 744 × 804, with median field time
approximately 28 ms before and 25 ms after over the same 16 warmed frames.
A synthetic `QT_SCALE_FACTOR=2` run uses 930 × 1005 samples and takes about
34 ms per field. The uncapped experimental 2× raster took 74 ms and was rejected.
These are short field timings, not end-to-end or long-duration frame-rate claims;
actual Retina hardware and physical pointer acceptance remain separate.

Linux's real X11/KWin two-process proof also passes workspace switching, pinning,
stacking in both directions, desktop edges, minimize/restore, hide/show and compact
mode. Mac CI now runs the activity, fluid and window suites explicitly; Linux
already discovers them. The checked Mac/Linux runs above are local evidence,
not an assertion that remote CI has completed.

## Installed artifacts (September 26)

Implementation: `e1d245e` on `fix/shared-flare-fidelity`, PR #15. Documentation-only
follow-ups do not alter the tested renderer.

**Mac installed and running:** the owner reported quitting and reopening; read-back
showed that the previous `252215b` application was still installed. Reopening
alone had not applied the candidate. The authorized replacement then paused the
owned shortcut, gracefully closed the idle desktop, verified idle DSH sessions,
replaced the app through the existing installer, and resumed the same owned DSH
and shortcut registrations. Saved profile/settings and both conversation metadata
records were identical before and after.

The separately copied and ad-hoc sealed application retains `252215b`'s
setup/menu/resize changes over the public `ea128d6` binary/dependency baseline.
Only `activity.py`, this guide at candidate construction, and the fixture proof
are overlaid. Its inventory SHA-256 is
`3c5d6ffee13352c52c0b20ff0eee034f7ad8227ef4e94abc503d12e6da93aff9`.
The actual candidate passed 37 activity/fluid/window checks (including the two
resize regressions from PR #13), native Cocoa captures, eight-edge/corner
synthetic resize and menu checks, and strict signature verification after use.

Installed read-back confirms `e1d245e`, the matching inventory, the normal native
app process, online/model-ready state, no connection or session-restore errors,
and both owned login services loaded. A rollback bundle is retained. The installed
renderer also passed a Cocoa widget capture with the owner's saved appearance
and 457 × 578 window size: its 777 × 898 effect canvas uses a 777 × 898 field,
with approximately 29 ms median warmed field time. macOS denied whole-display
capture over this connection; the capture is an isolated preview of the installed
renderer, not a screenshot of a live conversation. Screen-recording permissions
were not changed. Physical-motion/subjective visual acceptance remains the owner's.

At documentation commit `3a94d92`, GitHub Mac 14/26, Debian, installed-package,
Browser and Home workflows all passed. Subsequent documentation changes do not
change the tested renderer. The maintenance endpoint still does not expose or
persist an unsent draft; do not infer draft preservation from an idle status or
from the profile/session metadata checks.

**Linux selected, existing windows retained:** the compatible 0.2.11 candidate
copies selection `20260926-094732-3b3861db`, preserving its embedding, Home,
DSH and speech contracts. Its 35 subsystem tests pass. `augmentor-update` staged
and activated `20260926-204300-30f1286f`, artifact SHA-256
`ed11a3bb8c73a2d1eda10e347aa145378aa37e182fb93787dd7aa3104d5ef69d`.
Main/mobile still run `20260924-125423-63307454`; secondary still runs
`20260926-083736-5d6b65f6`. All report online and voice available, with update
pending until normal reopen. No live conversation window or backend restarted.

These are documented compatible overlays, not a claim that the wider release
convergence or Mac second-shortcut work in the platform audit is complete.
