// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Synthetic owned VM fixture. Never install as a product extension.
const Main = imports.ui.main;
const Meta = imports.gi.Meta;
const Config = imports.misc.config;
const xlet = {_uuid:'shortcut-proof@augmentoragent.com'};
function init(_metadata) {}
function enable() {
    if (Config.PACKAGE_VERSION !== '6.6.4' || Meta.is_wayland_compositor() !== false)
        throw new Error('Synthetic shortcut fixture requires reviewed Cinnamon 6.6.4 X11.');
    Main.keybindingManager.addXletHotKey(xlet,'proof','<Control><Super>F11',() => {});
}
function disable() { Main.keybindingManager.removeXletHotKey(xlet,'proof'); }
