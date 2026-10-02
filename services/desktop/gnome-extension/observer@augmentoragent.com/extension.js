// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Read-only Shell bridge. This does not authorize or implement desktop input.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Clutter from 'gi://Clutter';
import Shell from 'gi://Shell';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Config from 'resource:///org/gnome/shell/misc/config.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const XML = `<node><interface name="com.augmentor.GnomeObserver">
  <method name="Status"><arg type="s" direction="out"/></method>
  <method name="Read"><arg type="s" direction="out"/></method>
  <method name="InspectPoint"><arg type="s" direction="in"/><arg type="d" direction="in"/><arg type="d" direction="in"/><arg type="s" direction="out"/></method>
</interface></node>`;
const rect = r => ({x:r.x, y:r.y, width:r.width, height:r.height});

export default class Observer extends Extension {
    enable() {
        if (!/^(?:46|50)\.\d+(?:\.\d+)?$/.test(Config.PACKAGE_VERSION))
            throw new Error('The Augmentor observer supports GNOME 46 and 50 profiles.');
        this.legacyWindowProperties = Config.PACKAGE_VERSION.startsWith('46.');
        this.epoch = GLib.uuid_string_random();
        this.serial = 0;
        this.connections = [];
        this.windows = new Map();
        this.trackedActors = new WeakSet();
        this.dying = new WeakSet();
        this.workspaceIds = new WeakMap();
        this.actorIds = new WeakMap();
        this.nextId = 0;
        const bump = () => this.bump();
        const watch = (object, signals) => {
            for (const signal of signals)
                this.connections.push([object, object.connect(signal, bump)]);
        };
        try {
            watch(global.display, ['notify::focus-window', 'restacked', 'grab-op-begin',
                'grab-op-end', 'window-visibility-updated', 'workareas-changed',
                'window-entered-monitor','window-left-monitor','showing-desktop-changed',
                'in-fullscreen-changed']);
            this.connections.push([global.display,global.display.connect('closing',() => this.disable())]);
            this.connections.push([global.display,global.display.connect('window-created',
                (_display, window) => { this.track(window); bump(); })]);
            watch(global.workspace_manager, ['active-workspace-changed', 'workspace-added',
                'workspace-removed', 'workspaces-reordered','workspace-switched','showing-desktop-changed']);
            watch(Main.layoutManager, ['monitors-changed']);
            watch(Main.sessionMode, ['updated']);
            watch(Main.overview, ['showing', 'shown', 'hiding', 'hidden']);
            watch(global.stage, ['notify::key-focus', 'notify::is-grabbed']);
            watch(global.window_manager,['minimize','unminimize','map','destroy','size-change',
                'size-changed','switch-workspace','kill-switch-workspace','kill-window-effects']);
            if (Main.screenShield) watch(Main.screenShield,['active-changed','locked-changed','lock-screen-shown','wake-up-screen']);
            for (const actor of global.get_window_actors()) this.track(actor.get_meta_window());
            this.exported = Gio.DBusExportedObject.wrapJSObject(XML, this);
            this.exported.export(Gio.DBus.session, '/com/augmentor/GnomeObserver');
        } catch (error) {
            this.disable();
            throw error;
        }
    }

    track(window) {
        if (!window || this.dying.has(window)) return;
        if (!this.windows.has(window)) {
            this.bump();
            const signals = ['position-changed','size-changed','workspace-changed','raised',
                'notify::minimized','notify::on-all-workspaces','highest-scale-monitor-changed',
                'shown','notify::fullscreen','notify::above','notify::window-type','notify::decorated'];
            // Mutter 46 lacks these Meta.Window properties. Actor mapped and
            // display monitor-enter/leave signals provide the legacy tracking.
            if (!this.legacyWindowProperties) signals.push('notify::mapped','notify::main-monitor');
            const connections = [];
            this.windows.set(window,connections);
            for (const signal of signals) connections.push([window,window.connect(signal,() => this.bump())]);
            connections.push([window,window.connect('unmanaging',() => {this.dying.add(window); this.bump();})]);
            connections.push([window,window.connect('unmanaged',() => {
                this.bump();
                for (const [object,id] of this.windows.get(window) ?? []) object.disconnect(id);
                this.windows.delete(window);
            })]);
        }
        const connections=this.windows.get(window);
        const actor = window.get_compositor_private();
        if (actor && !this.trackedActors.has(actor)) {
            this.trackedActors.add(actor);this.bump();
            for (const signal of ['notify::mapped','notify::visible','notify::opacity',
                'notify::allocation','notify::translation-x','notify::translation-y',
                'notify::scale-x','notify::scale-y'])
                connections.push([actor,actor.connect(signal,() => this.bump())]);
            connections.push([actor,actor.connect('destroy',() => {
                this.bump();
                // Actor handlers disappear at disposal; never disconnect a disposed actor.
                const remaining=(this.windows.get(window) ?? []).filter(([object]) => object !== actor);
                if (this.windows.has(window)) this.windows.set(window,remaining);
            })]);
        }
        this.windows.set(window,connections);
    }

    actorId(actor) {
        if (!actor) return null;
        if (!this.actorIds.has(actor)) this.actorIds.set(actor,++this.nextId);
        return this.actorIds.get(actor);
    }

    bump() {
        if (this.serial >= Number.MAX_SAFE_INTEGER) {
            this.disable();
            throw new Error('Observer event serial exhausted; reconnect.');
        }
        this.serial++;
    }

    Status() {
        return JSON.stringify({schema:1,backend:'gnome-shell-observer',shellVersion:Config.PACKAGE_VERSION,
            epoch:this.epoch,serial:this.serial,readOnly:true,inputQualified:false,
            completeActorCompositionTracking:false});
    }

    snapshot() {
        const active = global.workspace_manager.get_active_workspace();
        if (!this.workspaceIds.has(active)) this.workspaceIds.set(active,++this.nextId);
        const actors = global.get_window_actors();
        if (actors.length > 200) throw new Error('Too many windows for a complete observation.');
        const candidates = actors.map(actor => actor.get_meta_window()).filter(Boolean);
        for (const window of candidates) this.track(window);
        const focus = global.display.get_focus_window();
        const visible = window => {
            const actor = window.get_compositor_private();
            return actor && actor.is_visible() && actor.is_mapped() && !window.minimized &&
                window.located_on_workspace(active) && window.showing_on_its_workspace();
        };
        const describe = window => ({id:this.epoch+':'+window.get_stable_sequence(),
            pid:window.get_pid(),application:(window.get_gtk_application_id() ?? window.get_wm_class() ?? '').slice(0,1024),
            title:(window.get_title() ?? '').slice(0,1024),geometry:rect(window.get_frame_rect()),
            overrideRedirect:window.is_override_redirect(),unmanaging:this.dying.has(window)});
        const order = global.display.sort_windows_by_stacking(candidates.filter(visible));
        const index = order.indexOf(focus);
        // Override-redirect stacking is not covered by Mutter's managed comparator.
        const above = order.filter((window,i) => window !== focus && (i > index || window.is_override_redirect()));
        const reasons = [];
        const guards = {locked:Main.sessionMode.isLocked,greeter:Main.sessionMode.isGreeter,sessionMode:Main.sessionMode.currentMode,
            parentSessionMode:Main.sessionMode.parentMode ?? null,
            actionMode:Main.actionMode,modalCount:Main.modalCount,overview:Main.overview.visible,
            overviewTarget:Main.overview.visibleTarget,stageGrabbed:global.stage.is_grabbed,
            overviewAnimation:Main.overview.animationInProgress,
            screenShieldAvailable:Boolean(Main.screenShield),screenShieldActive:Main.screenShield?.active ?? null,
            screenShieldLocked:Main.screenShield?.locked ?? null,
            stageGrabActor:this.actorId(global.stage.get_grab_actor()),
            stageKeyFocus:this.actorId(global.stage.get_key_focus()),windowDragging:global.display.is_grabbed()};
        if (guards.locked || guards.greeter) reasons.push('locked-or-greeter');
        // Ubuntu 24.04 supplies this specific user-derived normal mode. Do not
        // treat arbitrary session inheritance as an unlocked desktop.
        const normalSession = guards.sessionMode === 'user' || (this.legacyWindowProperties &&
            guards.sessionMode === 'ubuntu' && guards.parentSessionMode === 'user');
        if (!normalSession) reasons.push('non-user-session-mode');
        if (!guards.screenShieldAvailable) reasons.push('screen-shield-unavailable');
        if (guards.screenShieldActive || guards.screenShieldLocked) reasons.push('screen-shield-active');
        if (guards.actionMode !== Shell.ActionMode.NORMAL || guards.modalCount || guards.overview || guards.overviewTarget || guards.overviewAnimation)
            reasons.push('shell-mode-or-modal');
        if (guards.stageGrabbed || guards.stageGrabActor || guards.windowDragging) reasons.push('input-grab');
        if (!focus || index < 0 || this.dying.has(focus)) reasons.push('no-visible-live-focus');
        if (actors.some(actor => !actor.get_meta_window())) reasons.push('unidentified-window-actor');
        const screens = [];
        for (let i=0;i<global.display.get_n_monitors();i++)
            screens.push({name:'monitor:'+i,geometry:rect(global.display.get_monitor_geometry(i)),scale:global.display.get_monitor_scale(i)});
        return {schema:1,backend:'gnome-shell-observer',shellVersion:Config.PACKAGE_VERSION,
            epoch:this.epoch,serial:this.serial,inputQualified:false,
            window:focus && visible(focus) ? describe(focus) : null,
            windows:order.map(describe),above:above.map(describe),screens,
            workspace:{id:this.workspaceIds.get(active),index:active.index()},guards,blockedReasons:reasons};
    }

    Read() {return JSON.stringify(this.snapshot());}

    InspectPoint(expected,x,y) {
        if (!Number.isFinite(x) || !Number.isFinite(y) || expected.length > 100)
            throw new Error('Invalid point inspection.');
        const snapshot = this.snapshot();
        const focus = global.display.get_focus_window();
        const ancestryMatches = picked => {
            let actor=picked;
            while (actor && actor !== focus?.get_compositor_private()) actor=actor.get_parent();
            return Boolean(actor && snapshot.window?.id === expected);
        };
        const reactive=global.stage.get_actor_at_pos(Clutter.PickMode.REACTIVE,x,y);
        const painted=global.stage.get_actor_at_pos(Clutter.PickMode.ALL,x,y);
        const reactiveMatches=ancestryMatches(reactive),paintedMatches=ancestryMatches(painted);
        const matches=reactiveMatches && paintedMatches;
        const ancestry = picked => {
            const types=[];
            for (let actor=picked;actor && types.length<32;actor=actor.get_parent()) types.push(actor.constructor.name);
            return types;
        };
        return JSON.stringify({schema:1,epoch:this.epoch,serial:this.serial,inputQualified:false,
            expected,pickedActor:this.actorId(reactive),paintedActor:this.actorId(painted),windowMatches:matches,
            reactiveWindowMatches:reactiveMatches,paintedWindowMatches:paintedMatches,
            reactiveAncestors:ancestry(reactive),paintedAncestors:ancestry(painted),
            blocked:snapshot.blockedReasons.length > 0 || !matches});
    }

    disable() {
        this.exported?.unexport(); this.exported = null;
        for (const [object,id] of this.connections ?? []) object.disconnect(id);
        for (const connections of this.windows?.values() ?? [])
            for (const [object,id] of connections) object.disconnect(id);
        this.connections = [];this.windows?.clear();this.dying = new WeakSet();this.workspaceIds = new WeakMap();this.trackedActors = new WeakSet();
    }
}
