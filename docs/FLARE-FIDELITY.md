<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Shared desktop flare fidelity

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

Installed artifact identities and activation evidence are recorded below after
qualification. Source, selected release and running process are distinct.
