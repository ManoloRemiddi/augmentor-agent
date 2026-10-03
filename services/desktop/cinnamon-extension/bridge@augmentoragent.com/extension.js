// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Versioned, read-only bridge. No input, capture, launcher or callback export.
const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;
const Meta = imports.gi.Meta;
const Config = imports.misc.config;
const Main = imports.ui.main;
const ByteArray = imports.byteArray;
const NAME = 'org.cinnamon.ScreenSaver';
const PATH = '/org/cinnamon/ScreenSaver';
const XML = `<node><interface name="com.augmentor.CinnamonBridge">
<method name="Status"><arg type="s" direction="out"/></method>
<method name="RefreshLock"><arg type="s" direction="out"/></method>
<method name="ShortcutBindings"><arg type="s" direction="out"/></method>
</interface></node>`;

class Bridge {
    constructor() {
        this.alive = false;
        this.subscriptions = [];
        this.activeSubscription = 0;
        this.cancel = null;
        this.exported = null;
        try {
            if (Config.PACKAGE_VERSION !== '6.6.4' || typeof Meta.is_wayland_compositor !== 'function' ||
                Meta.is_wayland_compositor() !== false || !(Main.keybindingManager?.bindings instanceof Map) ||
                !(Main.keybindingManager.applet_bindings instanceof Map))
                throw new Error('The Augmentor bridge requires the qualified Cinnamon 6.6.4 X11 API profile.');
            this.bus = Gio.DBus.session;
            this.epoch = GLib.uuid_string_random();
            this.generation = 0;
            this.registrySerial = 0;
            this.signature = null;
            this.owner = null;
            this.state = 'unknown';
            this.pending = false;
            this.requested = false;
            this.alive = true;
            this._advance();
            this.subscriptions.push(this.bus.signal_subscribe('org.freedesktop.DBus','org.freedesktop.DBus',
                'NameOwnerChanged','/org/freedesktop/DBus',NAME,Gio.DBusSignalFlags.NONE,
                (_bus,_sender,_path,_interface,_signal,parameters) => {
                    if (!this.alive) return;
                    const [name,_old,next] = parameters.deep_unpack();
                    if (name !== NAME) return;
                    const wasRequested = this.requested;
                    this._advance('owner-changed');
                    this._bindOwner(next || null);
                    // Finish only an already requested discovery. Ordinary idle
                    // owner loss never causes a service restart loop.
                    if (wasRequested && this.owner) {
                        this.requested = this.pending = true;
                        this._queryUnique(this.generation);
                    }
                }));
            this.closedSignal = this.bus.connect('closed',() => this.disable());
            this.exported = Gio.DBusExportedObject.wrapJSObject(XML,this);
            this.exported.export(this.bus,'/com/augmentor/CinnamonBridge');
        } catch (error) {
            this.disable();
            throw error;
        }
    }

    _advance(reason='fresh-query') {
        this.cancel?.cancel();
        if (this.generation >= Number.MAX_SAFE_INTEGER) throw new Error('Lock generation exhausted.');
        this.generation++;
        this.cancel = new Gio.Cancellable();
        this.state = 'unknown';
        this.reason = reason;
        this.pending = this.requested = false;
    }

    _current(generation) { return this.alive && this.generation === generation; }

    _fail(generation,error=null) {
        if (this._current(generation)) {
            // Export only a public protocol classification, never raw error
            // arguments or messages from another application's service.
            const match = typeof error?.message === 'string' ? error.message.match(
                /org\.freedesktop\.DBus\.Error\.(?:UnknownMethod|UnknownObject|NameHasNoOwner|ServiceUnknown|NoReply)/) : null;
            this._advance(match ? match[0] : 'query-failed');
        }
    }

    _call(destination,path,iface,method,args,type,flags,generation,success,failure=null,timeout=1000) {
        this.bus.call(destination,path,iface,method,args,new GLib.VariantType(type),flags,timeout,this.cancel,
            (bus,result) => {
                if (!this._current(generation)) return;
                let reply;
                try { reply = bus.call_finish(result).deep_unpack(); }
                catch (error) {
                    try {
                        if (failure) failure(error);
                        else this._fail(generation,error);
                    } catch (failureError) { this._fail(generation,failureError); }
                    return;
                }
                if (this._current(generation)) {
                    try { success(reply); }
                    catch (error) { this._fail(generation,error); }
                }
            });
    }

    _bindOwner(owner) {
        if (this.activeSubscription) this.bus.signal_unsubscribe(this.activeSubscription);
        this.activeSubscription = 0;
        this.owner = owner && /^:\d+\.\d+$/.test(owner) ? owner : null;
        if (!this.owner) return;
        const expected = this.owner;
        this.activeSubscription = this.bus.signal_subscribe(expected,NAME,'ActiveChanged',PATH,null,
            Gio.DBusSignalFlags.NONE,(_bus,sender,_path,_iface,_signal,parameters) => {
                if (!this.alive || sender !== this.owner || sender !== expected) return;
                const values = parameters.deep_unpack();
                const wasRequested = this.requested;
                this._advance(values[0] === true ? 'active-signal' : 'negative-or-invalid-signal');
                // A negative signal cannot authorize an unlocked observation;
                // only a fresh owner-pinned GetActive reply can do that.
                if (values.length === 1 && values[0] === true) this.state = 'active';
                else if (values.length === 1 && values[0] === false && wasRequested) {
                    // A startup negative signal may supersede discovery. Finish
                    // that existing request through a NEW pinned query, never
                    // by granting inactivity directly from the signal.
                    this.pending = this.requested = true;
                    this._queryUnique(this.generation);
                }
            });
    }

    _resolveOwner(generation,activate) {
        this._call('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetNameOwner',
            new GLib.Variant('(s)',[NAME]),'(s)',Gio.DBusCallFlags.NO_AUTO_START,generation,
            values => {
                this._bindOwner(values[0]);
                if (!this.owner) throw new Error('Invalid screensaver owner.');
                this._queryUnique(generation);
            },error => {
                if (!this._current(generation)) return;
                if (!activate || Gio.DBusError.get_remote_error(error) !== 'org.freedesktop.DBus.Error.NameHasNoOwner') {
                    this._fail(generation,error);
                    return;
                }
                // The normal query can activate the stock service. Its bool is
                // discovery-only and is never accepted as lock authorization.
                this._call(NAME,PATH,NAME,'GetActive',null,'(b)',Gio.DBusCallFlags.NONE,generation,
                    _values => this._resolveOwner(generation,false),null,5000);
            });
    }

    _queryUnique(generation) {
        const expected = this.owner;
        if (!expected) { this._fail(generation); return; }
        this._call(expected,PATH,NAME,'GetActive',null,'(b)',Gio.DBusCallFlags.NO_AUTO_START,generation,
            values => {
                if (values.length !== 1 || typeof values[0] !== 'boolean') throw new Error('Invalid lock reply.');
                this._call('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetNameOwner',
                    new GLib.Variant('(s)',[NAME]),'(s)',Gio.DBusCallFlags.NO_AUTO_START,generation,
                    owners => {
                        if (owners[0] !== expected || this.owner !== expected) throw new Error('Screensaver owner changed.');
                        this.state = values[0] ? 'active' : 'inactive';
                        this.reason = 'owner-pinned-query';
                        this.pending = this.requested = false;
                    });
            },null,3000);
    }

    _status() {
        if (!this.alive) throw new Error('Cinnamon bridge is disabled.');
        return {schema:1,backend:'cinnamon-shortcut-bridge',cinnamonVersion:Config.PACKAGE_VERSION,
            sessionType:'x11',epoch:this.epoch,readOnly:true,inputQualified:false,
            sceneObserverQualified:false,completeRegistryHistoryTracking:false,
            lock:{state:this.state,owner:this.owner,generation:this.generation,queryPending:this.pending,reason:this.reason}};
    }

    Status() { return JSON.stringify(this._status()); }

    RefreshLock() {
        if (!this.alive) throw new Error('Cinnamon bridge is disabled.');
        if (!this.pending) {
            this._advance();
            this.pending = this.requested = true;
            this._resolveOwner(this.generation,true);
        }
        return this.Status();
    }

    ShortcutBindings() {
        const status = this._status();
        const manager = Main.keybindingManager;
        if (!(manager.bindings instanceof Map) || !(manager.applet_bindings instanceof Map) ||
            manager.bindings.size > 1024 || manager.applet_bindings.size > 1024)
            throw new Error('Cinnamon shortcut registry is unavailable or oversized.');
        const records = [];
        for (const entry of manager.bindings.values()) {
            if (!entry || typeof entry.name !== 'string' || entry.name.length > 512 ||
                !Array.isArray(entry.bindings) || entry.bindings.length > 64 ||
                entry.bindings.some(value => typeof value !== 'string' || value.length > 512))
                throw new Error('Cinnamon shortcut registry contains an invalid entry.');
            records.push({name:entry.name,accelerators:entry.bindings.slice()});
        }
        records.sort((a,b) => a.name < b.name ? -1 : a.name > b.name ? 1 : 0);
        let registryPending = false;
        for (const entry of manager.applet_bindings.values()) {
            if (!(entry instanceof Map)) throw new Error('Invalid Cinnamon spice registry.');
            const id = entry.get('commitTimeoutId');
            if (!Number.isSafeInteger(id) || id < 0) throw new Error('Invalid Cinnamon spice commit state.');
            if (id > 0) registryPending = true;
        }
        const signature = GLib.compute_checksum_for_string(GLib.ChecksumType.SHA256,JSON.stringify(records),-1);
        if (signature !== this.signature) {
            if (this.registrySerial >= Number.MAX_SAFE_INTEGER) throw new Error('Registry serial exhausted.');
            this.registrySerial++;
            this.signature = signature;
        }
        const result = JSON.stringify({...status,bindings:records,registryPending,
            snapshotSignature:signature,registrySerial:this.registrySerial});
        if (ByteArray.fromString(result).length > 131072) throw new Error('Cinnamon shortcut snapshot is too large.');
        return result;
    }

    disable() {
        this.alive = false;
        this.cancel?.cancel();
        this.generation++;
        this.exported?.unexport();
        this.exported = null;
        if (this.bus) {
            if (this.activeSubscription) this.bus.signal_unsubscribe(this.activeSubscription);
            for (const id of this.subscriptions) this.bus.signal_unsubscribe(id);
            if (this.closedSignal) this.bus.disconnect(this.closedSignal);
        }
        this.activeSubscription = this.closedSignal = 0;
        this.subscriptions = [];
        this.owner = null;
        this.state = 'unknown';
        this.pending = this.requested = false;
    }
}

let bridge = null;
function init(_metadata) {}
function enable() { bridge = new Bridge(); }
function disable() { bridge?.disable(); bridge = null; }
