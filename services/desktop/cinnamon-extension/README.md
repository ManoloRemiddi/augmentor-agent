<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Cinnamon shortcut bridge candidate

This legacy extension supports only running Cinnamon6.6.4/X11 and exports on
the native Cinnamon session connection. Metadata alone does not restrict the
runtime. Read [the pinned contract and remaining acceptance](../../../docs/LINUX-CINNAMON-ADAPTER.md).

`com.augmentor.CinnamonBridge` at `/com/augmentor/CinnamonBridge` exposes Status,
RefreshLock and ShortcutBindings only. Input/capture/scene qualification stays
false. No commands, callback functions or action invocation are exported.
Current bounded registry snapshots include settled manager/spice bindings;
they are not a complete history or a physical key-delivery claim.

RefreshLock asynchronously requests normal stock screensaver query activation.
The discovery reply never grants inactivity: a second unique-owner GetActive and
owner/generation recheck must succeed. Status remains unknown while pending.
Active signals block immediately; negative signals require a fresh read. Owner
loss and disable invalidate pending replies, and ordinary idle exit never causes
a restart loop. Unknown, active or registry-pending state must prevent Save.

Install through Cinnamon Settings Extensions for normal users. For an owned
fixture, `cinnamon-install-spice extension /absolute/path/bridge@augmentoragent.com`
is the upstream installer; it installs only and can update metadata. Enable via
the Settings UI or an ownership-preserving read/append to org.cinnamon
enabled-extensions. Do not force-enable with !uuid, replace foreign IDs or use
GNOME's extension CLI. Actual native-owner Status, not enabled-list readback,
confirms the running extension. Candidate source changes require a separately
installed artifact and exact installed identity in the proof.
