<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Cinnamon adapter research and qualification boundary

The [actual installed Mint 22.3 report](../release/qualification/next-targets/20261002-mint223-installed-session.json)
passes standard ISO installation, X11 login, normal reboot and wrong/correct
password lock tests. It records Cinnamon 6.6.4+zena, Muffin 6.6.1+zena and
screensaver 6.6.1+zena with unchanged package files and AppArmor enabled.
Augmentor is not installed in this guest. No shortcut delivery, observer,
consent, input, Stop, Browser, physical audio or release pass is claimed.

The external seed used stock Casper/Ubiquity through firmware/GRUB with an
unchanged, signed-checksum-verified ISO and blank disk. No installer success
hook receipt arrived. Acceptance instead uses the installed disk with ISO
detached, actual LightDM password login and preserved installer/package baseline
before adding SSH. No host devices or mounts are attached. Credentials and raw
installer/authentication logs remain private; checked evidence contains hashes.
The reboot driver initially submitted before typing and produced two refused
authentication attempts. Separate typing/submission then passed; both failures
remain explicit. No administrative unlock was used for these password tests.

## Native shortcut helper and interruption recovery

The [Qt adapter](../apps/native/augmentor_linux/cinnamon_shortcuts.py) now routes
Cinnamon before an inherited GNOME environment, while Mac retains priority.
It shares key identities with GNOME and runs GTK3 in a separate bounded worker;
the approved two-row settings UI stays unchanged. The
[native helper](../services/desktop/cinnamon_shortcuts.py) owns numeric custom<N>
rows through a private mapping, quoted canonical launcher commands and fresh
native-owner/epoch/lock/registry checks. It checks WM/media, foreign custom,
other owned and live spice bindings; dummy-list refresh preserves foreign IDs
and order. Native registration is separate from functional application delivery.

Before mutation, a private durable intent records the exact old/new ownership,
user values and candidate row. Pending reads refuse a saved-status claim. Retry
Save recovers only exact owned desired/previous fields: precommit interruption
restores the previous row/defaults and removes only its newly added ID; completed
ownership is retained. Foreign takeover refuses recovery and retains intent.
The [marked VM proof](../release/prove-cinnamon-shortcut-interruption.py) abruptly
exits real workers after intent, fields, registration and ownership, also testing
new-row interruption and foreign takeover. All six real cases pass.

The [checked helper report](../release/qualification/next-targets/20261002-cinnamon-native-shortcuts.json)
binds actual two-row Save/native registration and two QEMU key events to the
current helper. Both synthetic launcher argument sets pass; no Augmentor is
installed. Actual WM/custom/other-row/spice conflicts, tampering, precommit
rollback, postcommit durability refusal/recovery and production disabled-object/
stale-epoch refusal pass. The same v2 bridge remains active after a wrong password
and normal inspected password unlock recovers; default idle locking remains on.
The first 500ms native-property timeout and shorter cold discovery refusal are
retained. Reviewed calls allow2s, bridge discovery10s and the worker25s. A first
cold Save passed in about6s; later worker loss is covered by durable intent.

Nine native adapter/ownership tests, seven GNOME regressions and ten bridge
protocol cases pass. Full current source runs710 native cases in the owned Arch
fixture:708 pass, two platform skips. Earlier host QtTest, fixture Node and build
dependency failures remain explicit. Graphical product settings, full app/two
instances/reboot, physical keyboard, complete scene/control/Stop, Browser/audio
and release remain unqualified; the source helper does not widen the matrix.

## First bridge checkpoint (historical)

The first [bridge candidate](../services/desktop/cinnamon-extension/README.md)
is now implemented with Status/RefreshLock/ShortcutBindings only, no scene/input
methods. It pins the exact running6.6.4/X11 API and exports on Cinnamon's native
unique connection. Ten protocol cases pass; actual Mint returns76 bounded
callback-free registry entries. Actual disable removes its object, re-enable
creates a new initially unknown epoch and preserves foreign extension IDs/order.
Natural idle screensaver owner exit invalidates cached inactivity; explicit fresh
discovery verifies a new owner/generation. Read the
[checked artifact/helper evidence](../release/qualification/next-targets/20261002-cinnamon-shortcut-bridge.json).

The first expected-inactive inspection correctly refused the actual default idle
lock. The earlier candidate then stayed unknown during cold service startup;
those refusals are preserved. The revised bridge uses bounded async activation/
query waits and rechecks a startup negative signal through a new pinned query.
Negative signals never directly grant inactivity. An earlier input-driver step
ran before screenshot inspection and landed on the already unlocked Update Manager
welcome; it is explicitly excluded from authentication evidence. Actual v2
password-lock repetition, production stale-epoch consumer, registry-spice mutation,
shortcut Save/delivery and the full scene/consent/Stop cases remain open. No app
is installed. The normal source-helper inspector requests service query activation
but changes no settings, grabs or screen lock state.

Use a separate Cinnamon backend, not a GNOME observer alias. Research pins are
[Cinnamon 6.6.4](https://github.com/linuxmint/cinnamon/tree/8842b16921bb6984f1e14658bf56132163fc094d),
[Muffin 6.6.1](https://github.com/linuxmint/muffin/tree/7f8302f7953ca5a3cb88223f21d646a011e24844)
and [screensaver 6.6.1](https://github.com/linuxmint/cinnamon-screensaver/tree/2831a3ecb8b4592609681cc5c77e99b4b34c99a8).
Installed +zena API/source-patch equivalence still needs runtime checks.
Extensions use legacy imports and init/enable/disable, not GNOME ESM.
Required metadata includes uuid/name/description/cinnamon-version; the loader's
[version check](https://github.com/linuxmint/cinnamon/blob/8842b16921bb6984f1e14658bf56132163fc094d/js/ui/extension.js#L477)
accepts later versions. Explicit runtime 6.6/X11/API checks must restrict the
profile. Export bounded typed Status/Read/InspectPoint on Cinnamon's session
connection, pin calls to the unique owner of org.Cinnamon and keep
inputQualified false until the separate control qualification.

Watch supported display/window/workspace/monitor events and CinnamonWM lifecycle,
with a fresh epoch on each enable and full idempotent disconnect/unexport on
disable. Identity is epoch plus Meta.Window stable sequence, not PID or XID.
[Muffin's display signals and stacking caveat](https://github.com/linuxmint/muffin/blob/7f8302f7953ca5a3cb88223f21d646a011e24844/src/core/display.c#L2714)
require conservative intersecting override-redirect and unknown actor refusal.
Sample modalCount/modalActorFocusStack, overview and expo visibility/animation,
get_grab_op and stage key focus on every read. Do not assume GNOME sessionMode,
screenShield, actionMode or newer Mutter/Clutter APIs exist.

Actor picks are input-shaped. Muffin's
[surface pick](https://github.com/linuxmint/muffin/blob/7f8302f7953ca5a3cb88223f21d646a011e24844/src/compositor/meta-surface-actor.c#L183)
uses input_region; ALL is not a complete painted-pixel oracle. Public extension
signals do not establish every input-region away/back history. Use current picks
plus conservative intersecting window/Shell cover geometry, including same-PID
covers, and retain truthful incomplete-coverage flags. This preserves the approved
KDE check-then-dispatch baseline; it does not add compositor-atomic dispatch.

## Password lock and service ownership

Use org.cinnamon.ScreenSaver at /org/cinnamon/ScreenSaver, interface
org.cinnamon.ScreenSaver. Subscribe exact-owner ActiveChanged and owner changes
before initial owner-pinned GetActive; check query generation and owner again
before accepting a reply. Active true blocks immediately. Missing owner,
replacement, timeout or malformed reply is unknown, increments the generation
and discards target/consent. Only a fresh verified false permits new selection.
[The actual API](https://github.com/linuxmint/cinnamon-screensaver/blob/2831a3ecb8b4592609681cc5c77e99b4b34c99a8/libcscreensaver/org.cinnamon.ScreenSaver.xml#L5)
is broader than password locking, so blocking while active is conservative.

Actual Mint returned GetActive true while logind LockedHint stayed no. Never
combine these guards with AND or use logind false to clear Cinnamon's guard.
The read-only inspector refuses a missing owner both immediately after reboot
and after correct-password unlock. A normal GetActive call to the activatable
service then returned false, and a fresh owner-pinned inspection passed. Service
activation is a new generation; it cannot restore pre-lock selections. Do not
copy Cinnamon's missing-owner-to-false fallback. Extension unloading is not a
lock mechanism here. SetActive(false), Quit and administrative unlock are not
password-authentication evidence.

Missing unlocked owner is expected: the pinned Gtk.Application has a
[30-second inactivity timeout](https://github.com/linuxmint/cinnamon-screensaver/blob/2831a3ecb8b4592609681cc5c77e99b4b34c99a8/src/cinnamon-screensaver-main.py#L32),
holds while active and releases on stage deactivation. GetActive pokes that
lifetime and the [official query command](https://github.com/linuxmint/cinnamon-screensaver/blob/2831a3ecb8b4592609681cc5c77e99b4b34c99a8/src/cinnamon-screensaver-command.py#L104)
permits normal D-Bus autoactivation. Recover only on a requested fresh observation:
subscribe owner changes, asynchronously query the well-known name for discovery,
discard that bool as authorization, then obtain the unique owner, subscribe its
ActiveChanged and query it with NO_AUTO_START. Accept only after owner/generation
recheck without intervening blocking events. Status/Read stay unknown while
discovery is pending. No Shell main-loop blocking, automatic restart loop or
permanent --hold process. Alternate configured screen lockers remain unsupported.

## Shortcut ownership and refresh

Actual schemas are org.cinnamon.desktop.keybindings custom-list:as and
relocatable .custom-keybinding name:s, command:s, binding:as. Use numeric
custom<N> paths under /org/cinnamon/desktop/keybindings/custom-keybindings/.
The [standard editor](https://github.com/linuxmint/cinnamon/blob/8842b16921bb6984f1e14658bf56132163fc094d/files/usr/share/cinnamon/cinnamon-settings/bin/KeybindingTable.py#L768)
parses numeric suffixes; application-named IDs would break it. Persist a private
mapping for main/secondary and expected name/command/bindings. Treat any altered
owned row or unlisted nonempty candidate as foreign; never take it over.

Normalize accelerators with the GTK3 parser used by Cinnamon Settings, in a
separate helper if GTK4 is already loaded. Collision checks include parent,
WM/media, every foreign custom, the other owned row and runtime spice bindings;
empty/disabled entries are ignored. Quote absolute canonical launcher argv with
GLib.shell_quote and validate its shell_parse_argv round trip. Cinnamon spawns
argv without a shell or newly generated activation token.

Save changes only owned child fields; reread/merge parent IDs preserving foreign
order and toggle __dummy__ once to force the native
[changed::custom-list rebuild](https://github.com/linuxmint/cinnamon/blob/8842b16921bb6984f1e14658bf56132163fc094d/js/ui/keybindings.js#L308).
Child-only writes do not refresh grabs. Preserve existing lock/rollback discipline;
disable uses binding:[] and delete resets only verified-owned fields. Readback is
not actual key delivery. Optional version-pinned grab-registry inspection is
read-only and bounded, never callback export or grab mutation.

## Remaining finite acceptance

1. Verify installed runtime APIs/signals, strict unsupported profiles and clean
   enable/disable/enable epochs with stale-owner/epoch refusal.
2. Actual main/secondary Save, delivery, hide/restore, focus, two distinct PIDs,
   cold launch, change/disable and standard Keyboard editor acceptance.
3. Foreign WM/media/custom/spice conflicts, tampered ownership, foreign list/data
   preservation, concurrent Save and unrelated settings mutation.
4. Focus/geometry/workspace/sticky/close-recreate, monitor scale, menus/desklets,
   modal/grab/overview/expo transitions and all unknown guards.
5. Same-PID, override-redirect, shaped/click-through and Shell cover fixtures with
   conservative current geometry/pick handling and truthful history limits.
6. Actual password lock plus owner loss/replacement and fresh unlock generation;
   no pre-lock target/token/consent survives.
7. Separately qualify consent, capture/input transport and visible Stop mid-action,
   revocation and unknown-outcome no replay before enabling control.
