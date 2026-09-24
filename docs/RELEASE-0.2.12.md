<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Augmentor 0.2.12 desktop flare correction

The exterior plasma/flare canvas now follows its owning Desktop window’s
workspace and stacking order. Previously it bypassed the window manager and
requested a global keep-above layer, so it could remain on another workspace
or cover a second agent raised over its owner. The managed transient canvas
keeps its exterior reach and input transparency. Butterfly effects share it.

This matched Debian 13 amd64 preview retains the 0.2.11 WebSocket security fix
and existing DSH, Model Picker 1.1.2, Adaptive Reasoning 0.2.3 and Resonant Voice
0.1.16 dependencies. Home/shared-surface feature previews are not included.

## Qualification and distribution

The isolated X11/KWin proof uses two native processes and checks workspace
switching, pin/unpin, effect reappearance, stacking in both directions, desktop
edges, minimize/restore, hide/show and compact transitions. It makes no model
calls and does not touch the user’s desktop. CI runs it alongside existing checks.
This does not qualify native Wayland or macOS window-manager behavior.

Release artifacts and publication evidence will be recorded after final CI.
Existing installations follow [matched upgrade guidance](RELEASE-0.2.11.md#existing-installations)
with version 0.2.12. Source publication does not reload open windows. Preserve
active tasks and unsent drafts; managed local previews must retain their extra
features when applying this scoped native correction.
