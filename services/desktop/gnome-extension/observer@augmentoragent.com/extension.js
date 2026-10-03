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
  <method name="SignalDiagnostics"><arg type="s" direction="out"/></method>
  <method name="InspectPoint"><arg type="s" direction="in"/><arg type="d" direction="in"/><arg type="d" direction="in"/><arg type="s" direction="out"/></method>
</interface></node>`;
const rect = r => ({x:r.x, y:r.y, width:r.width, height:r.height});

export default class Observer extends Extension {
    enable() {
        if (!/^(?:46|48|49|50)\.\d+(?:\.\d+)?$/.test(Config.PACKAGE_VERSION))
            throw new Error('The Augmentor observer supports GNOME 46, 48, 49 and 50 profiles.');
        this.legacyWindowProperties = Config.PACKAGE_VERSION.startsWith('46.');
        this.epoch = GLib.uuid_string_random();
        this.serial = 0;
        this.nonRaisedBarrier = 0;
        this.baseline = null;
        this.collecting = false;
        this.signalSequence = 0;
        this.signalRecords = [];
        this.signalDropped = 0;
        this.signalOverflow = false;
        this.firstInvalidatingSignal = null;
        this.signalReasons = new Set(['unspecified','tracking-window','tracking-actor','window:unmanaging',
            'window:unmanaged','actor:destroy','display:window-created','raised-reentrant','raised-read-failed',
            'raised-no-baseline','raised-binding-or-history','raised-changed','raised-redundant','raised-diagnostics-overflow']);
        this.connections = [];
        this.windows = new Map();
        this.trackedActors = new WeakSet();
        this.deadActors = new WeakSet();
        this.dying = new WeakSet();
        this.workspaceIds = new WeakMap();
        this.actorIds = new WeakMap();
        this.nextId = 0;
        const watch = (object, signals, scope) => {
            for (const signal of signals) {
                this.signalReasons.add(scope+':'+signal);
                this.connections.push([object, object.connect(signal, () => this.bump(scope+':'+signal))]);
            }
        };
        try {
            watch(global.display, ['notify::focus-window', 'restacked', 'grab-op-begin',
                'grab-op-end', 'window-visibility-updated', 'workareas-changed',
                'window-entered-monitor','window-left-monitor','showing-desktop-changed',
                'in-fullscreen-changed'],'display');
            this.connections.push([global.display,global.display.connect('closing',() => this.disable())]);
            this.connections.push([global.display,global.display.connect('window-created',
                (_display, window) => { this.track(window); this.bump('display:window-created'); })]);
            watch(global.workspace_manager, ['active-workspace-changed', 'workspace-added',
                'workspace-removed', 'workspaces-reordered','workspace-switched','showing-desktop-changed'],'workspace');
            watch(Main.layoutManager, ['monitors-changed'],'layout');
            watch(Main.sessionMode, ['updated'],'session');
            watch(Main.overview, ['showing', 'shown', 'hiding', 'hidden'],'overview');
            watch(global.stage, ['notify::key-focus', 'notify::is-grabbed'],'stage');
            watch(global.window_manager,['minimize','unminimize','map','destroy','size-change',
                'size-changed','switch-workspace','kill-switch-workspace','kill-window-effects'],'manager');
            if (Main.screenShield) watch(Main.screenShield,['active-changed','locked-changed','lock-screen-shown','wake-up-screen'],'shield');
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
            this.bump('tracking-window');
            const signals = ['position-changed','size-changed','workspace-changed',
                'notify::minimized','notify::on-all-workspaces','highest-scale-monitor-changed',
                'shown','notify::fullscreen','notify::above','notify::window-type','notify::decorated'];
            // Mutter 46 lacks these Meta.Window properties. Actor mapped and
            // display monitor-enter/leave signals provide the legacy tracking.
            if (!this.legacyWindowProperties) signals.push('notify::mapped','notify::main-monitor');
            const connections = [];
            this.windows.set(window,connections);
            for (const signal of signals) {
                this.signalReasons.add('window:'+signal);
                connections.push([window,window.connect(signal,() => this.bump('window:'+signal))]);
            }
            connections.push([window,window.connect('raised',() => this.raised(window))]);
            connections.push([window,window.connect('unmanaging',() => {this.dying.add(window); this.bump('window:unmanaging');})]);
            connections.push([window,window.connect('unmanaged',() => {
                this.bump('window:unmanaged');
                for (const [object,id] of this.windows.get(window) ?? []) object.disconnect(id);
                this.windows.delete(window);
            })]);
        }
        const connections=this.windows.get(window);
        const actor = window.get_compositor_private();
        if (actor && !this.trackedActors.has(actor)) {
            this.trackedActors.add(actor);this.bump('tracking-actor');
            for (const signal of ['notify::mapped','notify::visible','notify::opacity',
                'notify::allocation','notify::translation-x','notify::translation-y',
                'notify::scale-x','notify::scale-y']) {
                this.signalReasons.add('actor:'+signal);
                connections.push([actor,actor.connect(signal,() => this.bump('actor:'+signal))]);
            }
            connections.push([actor,actor.connect('destroy',() => {
                this.deadActors.add(actor);
                this.bump('actor:destroy');
                // Actor handlers disappear at disposal; never disconnect a disposed actor.
                const remaining=(this.windows.get(window) ?? []).filter(([object]) => object !== actor);
                if (this.windows.has(window)) this.windows.set(window,remaining);
            })]);
        }
        this.windows.set(window,connections);
    }

    nextIdentity() {
        if (!Number.isSafeInteger(this.nextId) || this.nextId < 0 || this.nextId >= Number.MAX_SAFE_INTEGER) {
            this.baseline=null;
            throw new Error('Observer identity counter exhausted; reconnect.');
        }
        return ++this.nextId;
    }

    actorId(actor) {
        if (!actor) return null;
        if (!this.actorIds.has(actor)) this.actorIds.set(actor,this.nextIdentity());
        return this.actorIds.get(actor);
    }

    recordSignal(reason, invalidating, windowId=null) {
        if (this.signalSequence >= Number.MAX_SAFE_INTEGER) {
            this.signalOverflow=true; this.baseline=null; return false;
        }
        const record={sequence:++this.signalSequence,serial:this.serial,barrier:this.nonRaisedBarrier,
            reason:this.signalReasons.has(reason) ? reason : 'unspecified',invalidating};
        if (typeof windowId === 'string' && /^[a-f0-9-]{36}:\d{1,16}$/.test(windowId)) record.windowId=windowId;
        this.signalRecords.push(record);
        if (this.signalRecords.length > 128) {this.signalRecords.shift();this.signalDropped++;}
        if (invalidating && !this.firstInvalidatingSignal) this.firstInvalidatingSignal=record;
        return true;
    }

    bump(reason='unspecified', raised=false) {
        this.baseline=null;
        if (this.serial >= Number.MAX_SAFE_INTEGER || (!raised && this.nonRaisedBarrier >= Number.MAX_SAFE_INTEGER)) {
            this.disable();
            throw new Error('Observer event serial exhausted; reconnect.');
        }
        this.serial++;
        if (!raised) this.nonRaisedBarrier++;
        this.recordSignal(reason,true);
    }

    safetyFingerprint(scene) {
        // Include every scene field except this one event counter; do not
        // whitelist away unknown fields, titles or guards to force equality.
        const {serial,...identity}=scene;
        const actors=global.get_window_actors();
        if (actors.length > 200 || new Set(actors).size !== actors.length)
            throw new Error('Unknown actor inventory.');
        const inventory=actors.map(actor => {
            const window=actor.get_meta_window();
            if (!window || !this.windows.has(window) || this.dying.has(window) ||
                !this.trackedActors.has(actor) || this.deadActors.has(actor) || window.get_compositor_private() !== actor)
                throw new Error('Untracked actor inventory.');
            const box=actor.get_allocation_box(),translation=actor.get_translation(),scale=actor.get_scale(),
                opacity=actor.get_opacity();
            if (!box || !['x1','y1','x2','y2'].every(key => Number.isFinite(box[key])) ||
                !Array.isArray(translation) || translation.length !== 3 || !translation.every(Number.isFinite) ||
                !Array.isArray(scale) || scale.length !== 2 || !scale.every(Number.isFinite) ||
                !Number.isInteger(opacity) || opacity < 0 || opacity > 255)
                throw new Error('Unknown actor getter contract.');
            return {window:this.epoch+':'+window.get_stable_sequence(),pid:window.get_pid(),
                geometry:rect(window.get_frame_rect()),minimized:window.minimized,
                actor:this.actorId(actor),parent:this.actorId(actor.get_parent()),
                visible:actor.is_visible(),mapped:actor.is_mapped(),opacity,
                allocation:{x1:box.x1,y1:box.y1,x2:box.x2,y2:box.y2},
                translation,scale};
        });
        let count=0;
        const canonical=(value,depth=0) => {
            if (++count > 20000 || depth > 12) throw new Error('Fingerprint bounds exceeded.');
            if (value === null || typeof value === 'boolean' || typeof value === 'string') return value;
            if (typeof value === 'number' && Number.isFinite(value)) return value;
            if (Array.isArray(value)) return value.map(item => canonical(item,depth+1));
            if (value && Object.prototype.toString.call(value) === '[object Object]')
                return Object.fromEntries(Object.keys(value).sort().map(key => [key,canonical(value[key],depth+1)]));
            throw new Error('Unknown fingerprint value.');
        };
        const fingerprint=JSON.stringify(canonical({scene:identity,inventory}));
        if (fingerprint.length > 262144) throw new Error('Fingerprint size exceeded.');
        return fingerprint;
    }

    raised(window) {
        const baseline=this.baseline;
        let reason='raised-no-baseline';
        if (this.collecting) {this.bump('raised-reentrant',true);return;}
        if (baseline && !this.signalOverflow && this.signalSequence-baseline.sequence < 128 &&
            baseline.epoch === this.epoch && baseline.serial === this.serial && baseline.barrier === this.nonRaisedBarrier &&
            baseline.window === window && this.windows.has(window) && !this.dying.has(window)) {
            this.collecting=true;
            try {
                if (global.display.get_focus_window() !== window || window.get_compositor_private() !== baseline.actor ||
                    !this.trackedActors.has(baseline.actor) || this.deadActors.has(baseline.actor))
                    throw new Error('Raised window binding changed.');
                const scene=this.snapshot();
                const fingerprint=this.safetyFingerprint(scene);
                const focused=global.display.get_focus_window(),actor=window.get_compositor_private();
                if (focused !== window || actor !== baseline.actor || this.deadActors.has(actor))
                    throw new Error('Raised window binding changed during collection.');
                if (!scene.blockedReasons.length && scene.serial === this.serial && scene.epoch === this.epoch &&
                    baseline.epoch === this.epoch && baseline.serial === this.serial &&
                    baseline.barrier === this.nonRaisedBarrier && fingerprint === baseline.fingerprint) {
                    if (this.recordSignal('raised-redundant',false,scene.window?.id)) return;
                    reason='raised-diagnostics-overflow';
                } else reason='raised-changed';
            } catch (_) {reason='raised-read-failed';}
            finally {this.collecting=false;}
        } else if (baseline) reason='raised-binding-or-history';
        this.bump(reason,true);
    }

    SignalDiagnostics() {
        return JSON.stringify({schema:1,epoch:this.epoch,limit:128,totalRecords:this.signalSequence,
            droppedRecords:this.signalDropped,historyGap:this.signalDropped > 0,overflow:this.signalOverflow,
            firstInvalidating:this.firstInvalidatingSignal,records:this.signalRecords});
    }

    Status() {
        return JSON.stringify({schema:1,backend:'gnome-shell-observer',shellVersion:Config.PACKAGE_VERSION,
            epoch:this.epoch,serial:this.serial,readOnly:true,inputQualified:false,
            completeActorCompositionTracking:false});
    }

    snapshot() {
        const active = global.workspace_manager.get_active_workspace();
        if (!this.workspaceIds.has(active)) this.workspaceIds.set(active,this.nextIdentity());
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
            // Ubuntu Desktop Icons can retain visible focus outside the actor
            // inventory. A blocked, unlisted focus is never an eligible target.
            window:index >= 0 ? describe(focus) : null,
            windows:order.map(describe),above:above.map(describe),screens,
            workspace:{id:this.workspaceIds.get(active),index:active.index()},guards,blockedReasons:reasons};
    }

    Read() {
        this.baseline=null;
        if (this.collecting) throw new Error('Observer collection reentered.');
        this.collecting=true;
        try {
            const scene=this.snapshot();
            const epoch=this.epoch,serial=this.serial,barrier=this.nonRaisedBarrier;
            try {
                const fingerprint=this.safetyFingerprint(scene);
                const window=global.display.get_focus_window(),actor=window?.get_compositor_private();
                const windowId=window ? epoch+':'+window.get_stable_sequence() : null;
                if (!scene.blockedReasons.length && scene.epoch === epoch && epoch === this.epoch &&
                    scene.serial === this.serial && serial === this.serial && barrier === this.nonRaisedBarrier &&
                    scene.window?.id === windowId && window && this.windows.has(window) && !this.dying.has(window) &&
                    actor && this.trackedActors.has(actor) && !this.deadActors.has(actor) && !this.signalOverflow)
                    this.baseline={epoch,serial,barrier,fingerprint,window,actor,sequence:this.signalSequence};
            } catch (_) {this.baseline=null;}
            return JSON.stringify(scene);
        } finally {this.collecting=false;}
    }

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
        this.baseline=null;
        this.exported?.unexport(); this.exported = null;
        for (const [object,id] of this.connections ?? []) object.disconnect(id);
        for (const connections of this.windows?.values() ?? [])
            for (const [object,id] of connections) object.disconnect(id);
        this.connections = [];this.windows?.clear();this.dying = new WeakSet();this.workspaceIds = new WeakMap();this.trackedActors = new WeakSet();
        this.deadActors = new WeakSet();
    }
}
