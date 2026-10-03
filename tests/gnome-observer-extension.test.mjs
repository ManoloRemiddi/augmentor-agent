// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Execute extension policies with synthetic Shell objects, never a live session.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=readFileSync(new URL('../services/desktop/gnome-extension/observer@augmentoragent.com/extension.js',import.meta.url),'utf8')
  .replace(/^import .*;\n/gm,'').replace('export default class Observer','class Observer')+'\nglobalThis.Observer=Observer;';
function fixture(version='46.0',mode='ubuntu',parent='user') {
  function emitter(extra={}) {
    const callbacks=new Map();let next=0;
    return {callbacks,connect(signal,callback){callbacks.set(++next,{signal,callback});return next;},
      disconnect(id){callbacks.delete(id);},emit(signal){for(const item of callbacks.values())if(item.signal===signal)item.callback();},...extra};
  }
  const workspace={index:()=>0};
  const stage=emitter({is_grabbed:false,get_grab_actor:()=>null,get_key_focus:()=>null});
  const display=emitter({get_focus_window:()=>null,sort_windows_by_stacking:windows=>windows,is_grabbed:()=>false,
    get_n_monitors:()=>1,get_monitor_geometry:()=>({x:0,y:0,width:1280,height:800}),get_monitor_scale:()=>1});
  const Main={sessionMode:emitter({currentMode:mode,parentMode:parent,isLocked:false,isGreeter:false}),
    layoutManager:emitter(),overview:emitter({visible:false,visibleTarget:false,animationInProgress:false}),
    screenShield:emitter({active:false,locked:false}),actionMode:1,modalCount:0};
  const global={stage,display,workspace_manager:emitter({get_active_workspace:()=>workspace}),window_manager:emitter(),get_window_actors:()=>[]};
  const context=vm.createContext({Config:{PACKAGE_VERSION:version},Main,global,Extension:class {},
    GLib:{uuid_string_random:()=> '01234567-89ab-cdef-0123-456789abcdef'},Shell:{ActionMode:{NORMAL:1}},
    Gio:{DBus:{session:{}},DBusExportedObject:{wrapJSObject:()=>({export(){},unexport(){}})}}});
  new vm.Script(source).runInContext(context);
  const observer=new context.Observer();
  return {observer,Main,display,emitter,global};
}

test('visible focus outside the actor inventory remains blocked without an invalid scene',()=>{
  for(const version of ['46.0','48.4','49.5','50.5']) {
    const {observer,display,emitter,global}=fixture(version,'user',null);observer.enable();
    const actor=emitter({is_visible:()=>true,is_mapped:()=>true});
    const window=emitter({get_compositor_private:()=>actor,minimized:false,located_on_workspace:()=>true,
      showing_on_its_workspace:()=>true,get_stable_sequence:()=>13,get_pid:()=>104,
      get_gtk_application_id:()=> 'com.rastersoft.ding',get_wm_class:()=>null,get_title:()=> 'Desktop Icons 1',
      get_frame_rect:()=>({x:0,y:0,width:1280,height:800}),is_override_redirect:()=>false});
    display.get_focus_window=()=>window;
    const unlisted=observer.snapshot();assert.equal(unlisted.window,null);
    assert.equal(unlisted.windows.length,0);assert(unlisted.blockedReasons.includes('no-visible-live-focus'));
    assert.equal(unlisted.inputQualified,false);
    global.get_window_actors=()=>[{get_meta_window:()=>window}];
    const listed=observer.snapshot();assert.deepEqual(listed.window,listed.windows[0]);
    assert(!listed.blockedReasons.includes('no-visible-live-focus'));observer.disable();
  }
});

test('Ubuntu normal mode requires GNOME 46 and the explicit user parent',()=>{
  for(const [version,mode,parent,blocked] of [['46.0','ubuntu','user',false],['46.2','user',null,false],
    ['48.4','user',null,false],['48.4','ubuntu','user',true],['49.5','user',null,false],['49.5','ubuntu','user',true],['50.5','user',null,false],['50.5','ubuntu','user',true],['46.0','ubuntu','greeter',true],
    ['46.0','arbitrary','user',true],['46.0','unlock-dialog','user',true]]) {
    const {observer}=fixture(version,mode,parent);observer.enable();
    const value=observer.snapshot();assert.equal(value.blockedReasons.includes('non-user-session-mode'),blocked);
    assert.equal(value.guards.parentSessionMode,parent);assert.equal(value.inputQualified,false);
    assert.equal(JSON.parse(observer.Status()).readOnly,true);observer.disable();
  }
});

test('Ubuntu inheritance never bypasses lock, overview or modal guards',()=>{
  const {observer,Main}=fixture();observer.enable();
  Main.sessionMode.isLocked=true;Main.screenShield.locked=true;
  assert(observer.snapshot().blockedReasons.includes('locked-or-greeter'));
  assert(observer.snapshot().blockedReasons.includes('screen-shield-active'));
  Main.sessionMode.isLocked=false;Main.screenShield.locked=false;Main.overview.visible=true;
  assert(observer.snapshot().blockedReasons.includes('shell-mode-or-modal'));
  Main.overview.visible=false;Main.modalCount=1;
  assert(observer.snapshot().blockedReasons.includes('shell-mode-or-modal'));observer.disable();
});

test('46 tracks actor mapping and display monitor changes without nonexistent window properties',()=>{
  for(const version of ['46.0','48.4','49.5','50.5']) {
    const {observer,emitter,display}=fixture(version,'user',null);observer.enable();
    const actor=emitter();const window=emitter({get_compositor_private:()=>actor});observer.track(window);
    const signals=[...window.callbacks.values()].map(item=>item.signal);
    for(const property of ['notify::mapped','notify::main-monitor'])assert.equal(signals.includes(property),!version.startsWith('46.'));
    let serial=observer.serial;actor.emit('notify::mapped');assert(observer.serial>serial);
    serial=observer.serial;display.emit('window-entered-monitor');assert(observer.serial>serial);
    serial=observer.serial;display.emit('window-left-monitor');assert(observer.serial>serial);
    observer.disable();assert.equal(actor.callbacks.size,0);assert.equal(window.callbacks.size,0);
  }
});

test('unreviewed Shell generations refuse before bridge export',()=>{
  for(const version of ['45.9','47.0','51.0','46.0-foreign'])
    assert.throws(()=>fixture(version).observer.enable(),/46, 48, 49 and 50/);
});
