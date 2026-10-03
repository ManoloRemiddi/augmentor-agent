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

function raisedFixture(version='50.5') {
  const result=fixture(version,'user',null),{observer,emitter,display,global}=result;
  const state={box:{x1:240,y1:141,x2:1040,y2:691},frame:{x:240,y:141,width:800,height:550},
    translation:[0,0,0],scale:[1,1],opacity:255,mapped:true,visible:true};
  const actor=emitter({get_allocation_box:()=>state.box,get_translation:()=>state.translation,
    get_scale:()=>state.scale,get_opacity:()=>state.opacity,get_parent:()=>null,
    is_visible:()=>state.visible,is_mapped:()=>state.mapped});
  const window=emitter({get_compositor_private:()=>actor,minimized:false,located_on_workspace:()=>true,
    showing_on_its_workspace:()=>true,get_stable_sequence:()=>13,get_pid:()=>104,
    get_gtk_application_id:()=> 'PRIVATE APP',get_wm_class:()=>null,get_title:()=> 'PRIVATE TITLE',
    get_frame_rect:()=>state.frame,is_override_redirect:()=>false});
  actor.get_meta_window=()=>window;state.actors=[actor];state.focus=window;
  global.get_window_actors=()=>state.actors;display.get_focus_window=()=>state.focus;
  observer.enable();observer.Read();assert(observer.baseline);
  return {...result,state,actor,window};
}

function anotherWindow(f,{visible=true,id=14}={}) {
  const state={translation:[0,0,0],visible};
  const actor=f.emitter({get_allocation_box:()=>({x1:0,y1:0,x2:20,y2:20}),get_translation:()=>state.translation,
    get_scale:()=>[1,1],get_opacity:()=>255,get_parent:()=>null,is_visible:()=>state.visible,is_mapped:()=>true});
  const window=f.emitter({get_compositor_private:()=>actor,minimized:false,located_on_workspace:()=>true,
    showing_on_its_workspace:()=>true,get_stable_sequence:()=>id,get_pid:()=>204,
    get_gtk_application_id:()=> 'PRIVATE OTHER APP',get_wm_class:()=>null,get_title:()=> 'PRIVATE OTHER TITLE',
    get_frame_rect:()=>({x:0,y:0,width:20,height:20}),is_override_redirect:()=>false});
  actor.get_meta_window=()=>window;f.state.actors.push(actor);f.observer.track(window);
  return {state,actor,window};
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

test('46/48/49/50 redundant raised pulses preserve serial only for the exact cached alive focused actor',()=>{
  for(const version of ['46.0','48.4','49.5','50.5']) {
    const {observer,window}=raisedFixture(version),serial=observer.serial,barrier=observer.nonRaisedBarrier;
    window.emit('raised');window.emit('raised');assert.equal(observer.serial,serial);assert.equal(observer.nonRaisedBarrier,barrier);
    const diagnostics=JSON.parse(observer.SignalDiagnostics());
    assert.deepEqual(diagnostics.records.slice(-2).map(record=>record.reason),['raised-redundant','raised-redundant']);
    assert(diagnostics.records.slice(-2).every(record=>!record.invalidating));observer.disable();
  }
});

test('every registered non-raised callback always invalidates cache and barrier, even with equal final fields',()=>{
  for(const version of ['46.0','48.4','49.5','50.5']) {
    const f=raisedFixture(version);
    for(const object of [f.display,f.global.workspace_manager,f.Main.layoutManager,f.Main.sessionMode,
      f.Main.overview,f.global.stage,f.global.window_manager,f.Main.screenShield,f.window,f.actor]) {
      for(const {signal} of [...object.callbacks.values()]) {
        if(['raised','unmanaging','unmanaged','destroy','closing','window-created'].includes(signal))continue;
        f.observer.Read();assert(f.observer.baseline);const serial=f.observer.serial,barrier=f.observer.nonRaisedBarrier;
        object.emit(signal);assert.equal(f.observer.serial,serial+1);assert.equal(f.observer.nonRaisedBarrier,barrier+1);
        assert.equal(f.observer.baseline,null);
      }
    }
    f.observer.disable();
  }
});

test('watched focus/lock/geometry/stage away-back cannot regain the old scene serial',()=>{
  for(const version of ['46.0','48.4','49.5','50.5']) {
    for(const kind of ['focus','lock','geometry','stage']) {
      const f=raisedFixture(version),serial=f.observer.serial;
      if(kind==='focus') {
        f.state.focus=null;f.display.emit('notify::focus-window');f.state.focus=f.window;f.display.emit('notify::focus-window');
      } else if(kind==='lock') {
        f.Main.screenShield.locked=true;f.Main.screenShield.emit('locked-changed');
        f.Main.screenShield.locked=false;f.Main.screenShield.emit('locked-changed');
      } else if(kind==='geometry') {
        f.state.frame.x++;f.window.emit('position-changed');f.state.frame.x--;f.window.emit('position-changed');
      } else {
        f.global.stage.is_grabbed=true;f.global.stage.emit('notify::is-grabbed');
        f.global.stage.is_grabbed=false;f.global.stage.emit('notify::is-grabbed');
      }
      assert.equal(f.observer.serial,serial+2);f.window.emit('raised');assert.equal(f.observer.serial,serial+3);
      f.observer.Read();f.window.emit('raised');assert.equal(f.observer.serial,serial+3);
      f.observer.disable();
    }
  }
});

test('changed scene, guards, stack order or private actor fingerprint invalidates instead of suppressing',()=>{
  for(const mutation of [f=>f.state.frame.x++,f=>f.Main.modalCount++,f=>f.Main.overview.visible=true,
    f=>f.Main.sessionMode.isLocked=true,f=>f.state.opacity--,f=>f.state.translation[0]++,
    f=>f.state.scale[0]=2,f=>f.state.box.x2++,f=>f.actor.get_parent=()=>f.global.stage,
    f=>f.display.get_monitor_scale=()=>2]) {
    const f=raisedFixture(),serial=f.observer.serial;mutation(f);f.window.emit('raised');
    assert(f.observer.serial>serial);assert.equal(f.observer.baseline,null);f.observer.disable();
  }
});

test('missing/stale baseline, foreign focus, untracked or dying window never suppresses',()=>{
  for(const mutation of [f=>f.observer.baseline=null,f=>f.observer.epoch='new epoch',
    f=>f.observer.serial++,f=>f.observer.nonRaisedBarrier++,f=>f.state.focus=null,
    f=>f.observer.windows.delete(f.window),f=>f.observer.dying.add(f.window)]) {
    const f=raisedFixture();mutation(f);const serial=f.observer.serial;f.window.emit('raised');
    assert.equal(f.observer.serial,serial+1);assert.equal(f.observer.baseline,null);f.observer.disable();
  }
  const f=raisedFixture(),serial=f.observer.serial;f.observer.raised({});assert.equal(f.observer.serial,serial+1);f.observer.disable();
});

test('full actor inventory includes hidden actors; hidden transforms and inventory substitution refuse',()=>{
  const f=raisedFixture(),hidden=anotherWindow(f,{visible:false});f.observer.Read();assert(f.observer.baseline);
  assert.equal(JSON.parse(f.observer.Read()).windows.length,1);const serial=f.observer.serial;
  hidden.state.translation[0]++;f.window.emit('raised');assert.equal(f.observer.serial,serial+1);
  assert.equal(f.observer.baseline,null);f.observer.disable();
  const g=raisedFixture();g.state.actors.push(g.emitter({get_meta_window:()=>g.window}));const before=g.observer.serial;
  g.window.emit('raised');assert(g.observer.serial>before);assert.equal(g.observer.baseline,null);g.observer.disable();
});

test('actual changed window order refuses and synchronous getters are surrounded by barrier checks',()=>{
  for(const version of ['46.0','48.4','49.5','50.5']) {
    const f=raisedFixture(version);anotherWindow(f);f.observer.Read();assert(f.observer.baseline);
    const serial=f.observer.serial;f.display.sort_windows_by_stacking=windows=>[...windows].reverse();
    f.window.emit('raised');assert.equal(f.observer.serial,serial+1);assert.equal(f.observer.baseline,null);f.observer.disable();
  }
});

test('getter errors and nonfinite or unknown fingerprint data preserve invalidation',()=>{
  for(const mutation of [f=>f.actor.get_opacity=()=>{throw new Error('PRIVATE ERROR');},
    f=>f.actor.get_translation=()=>[NaN,0,0],f=>f.actor.get_scale=()=>undefined,
    f=>f.window.get_compositor_private=()=>{throw new Error('PRIVATE ERROR');}]) {
    const f=raisedFixture(),serial=f.observer.serial;mutation(f);f.window.emit('raised');
    assert.equal(f.observer.serial,serial+1);assert.equal(f.observer.baseline,null);
    assert(!f.observer.SignalDiagnostics().includes('PRIVATE'));f.observer.disable();
  }
});

test('collection reentrancy or new native tracking is detected before suppression',()=>{
  const f=raisedFixture(),serial=f.observer.serial;let nested=false;
  f.actor.get_opacity=()=>{if(!nested){nested=true;f.window.emit('raised');}return 255;};
  f.window.emit('raised');assert(f.observer.serial>serial);assert.equal(f.observer.baseline,null);
  assert(JSON.parse(f.observer.SignalDiagnostics()).records.some(record=>record.reason==='raised-reentrant'));f.observer.disable();
  const g=raisedFixture(),before=g.observer.serial;g.actor.get_opacity=()=>{g.observer.bump('tracking-window');return 255;};
  g.window.emit('raised');assert(g.observer.serial>before);assert.equal(g.observer.baseline,null);g.observer.disable();
});

test('delayed actual restack invalidates after a redundant pulse and cannot recover old serial',()=>{
  for(const version of ['46.0','48.4','49.5','50.5']) {
    const f=raisedFixture(version),serial=f.observer.serial;f.window.emit('raised');assert.equal(f.observer.serial,serial);
    f.display.emit('restacked');assert.equal(f.observer.serial,serial+1);assert.equal(f.observer.baseline,null);
    f.window.emit('raised');assert.equal(f.observer.serial,serial+2);f.observer.disable();
  }
});

test('raw scene has no volatile diagnostic fields and every unknown scene field participates in equality',()=>{
  const f=raisedFixture();const before=JSON.parse(f.observer.Read());assert.deepEqual(JSON.parse(f.observer.Read()),before);
  assert.deepEqual(Object.keys(before).sort(),['above','backend','blockedReasons','epoch','guards','inputQualified',
    'schema','screens','serial','shellVersion','window','windows','workspace']);
  const original=f.observer.snapshot;let unknown=1;
  f.observer.snapshot=function(){return {...original.call(this),unknownSafetyField:{value:unknown}};};
  f.observer.Read();assert(f.observer.baseline);const serial=f.observer.serial;unknown=2;f.window.emit('raised');
  assert.equal(f.observer.serial,serial+1);f.observer.disable();
});

test('reason diagnostics are bounded and sanitized; history gaps and counter overflow refuse suppression',()=>{
  const f=raisedFixture();const serial=f.observer.serial;
  for(let i=0;i<128;i++)f.window.emit('raised');assert.equal(f.observer.serial,serial);
  f.window.emit('raised');assert.equal(f.observer.serial,serial+1);assert.equal(f.observer.baseline,null);
  let diagnostics=JSON.parse(f.observer.SignalDiagnostics());assert.equal(diagnostics.records.length,128);
  assert(diagnostics.droppedRecords>0);assert(diagnostics.historyGap);assert(diagnostics.firstInvalidating);
  f.observer.bump('PRIVATE PAYLOAD');assert(!f.observer.SignalDiagnostics().includes('PRIVATE'));
  f.observer.Read();assert(f.observer.baseline);const renewed=f.observer.serial;
  f.window.emit('raised');assert.equal(f.observer.serial,renewed);assert(renewed>serial);
  assert(JSON.parse(f.observer.SignalDiagnostics()).historyGap);
  f.observer.signalSequence=Number.MAX_SAFE_INTEGER;
  const before=f.observer.serial;f.window.emit('raised');assert.equal(f.observer.serial,before+1);
  assert.equal(f.observer.baseline,null);diagnostics=JSON.parse(f.observer.SignalDiagnostics());assert(diagnostics.overflow);
  f.observer.disable();
});

test('serial or non-raised barrier exhaustion unexports and detaches signal handlers',()=>{
  for(const field of ['serial','nonRaisedBarrier']) {
    const f=raisedFixture();f.observer[field]=Number.MAX_SAFE_INTEGER;
    assert.throws(()=>f.display.emit('restacked'),/exhausted/);assert.equal(f.observer.baseline,null);
    assert.equal(f.actor.callbacks.size,0);assert.equal(f.window.callbacks.size,0);assert.equal(f.display.callbacks.size,0);
  }
});

test('incomplete native getter shapes cannot cache an eligible Read or suppress raised',()=>{
  for(const mutation of [f=>f.actor.get_translation=()=>[],f=>f.actor.get_translation=()=>[0,0],
    f=>f.actor.get_scale=()=>[1],f=>f.actor.get_scale=()=>[1,1,1],
    f=>f.actor.get_allocation_box=()=>({x1:0,y1:0,x2:20}),f=>f.actor.get_opacity=()=>256,
    f=>f.actor.get_opacity=()=>1.5]) {
    const f=raisedFixture();mutation(f);const read=JSON.parse(f.observer.Read());
    assert.equal(read.blockedReasons.length,0);assert.equal(f.observer.baseline,null);
    const serial=f.observer.serial;f.window.emit('raised');assert.equal(f.observer.serial,serial+1);f.observer.disable();
  }
});

test('focus or actor identity changing during synchronous collection is checked again before suppression',()=>{
  for(const version of ['46.0','48.4','49.5','50.5']) {
    const f=raisedFixture(version),serial=f.observer.serial;
    f.actor.get_opacity=()=>{f.state.focus=null;return 255;};
    f.window.emit('raised');assert.equal(f.observer.serial,serial+1);assert.equal(f.observer.baseline,null);f.observer.disable();
    const g=raisedFixture(version),before=g.observer.serial;
    g.actor.get_opacity=()=>{g.window.get_compositor_private=()=>null;return 255;};
    g.window.emit('raised');assert.equal(g.observer.serial,before+1);assert.equal(g.observer.baseline,null);g.observer.disable();
    const h=raisedFixture(version);h.actor.get_opacity=()=>{h.state.focus=null;return 255;};
    h.observer.Read();assert.equal(h.observer.baseline,null);h.observer.disable();
  }
});

test('native actor/window lifetime signals invalidate and dead actors cannot become a new baseline',()=>{
  for(const version of ['46.0','48.4','49.5','50.5']) {
    for(const signal of ['unmanaging','unmanaged']) {
      const f=raisedFixture(version),serial=f.observer.serial,barrier=f.observer.nonRaisedBarrier;
      f.window.emit(signal);assert.equal(f.observer.serial,serial+1);assert.equal(f.observer.nonRaisedBarrier,barrier+1);
      assert.equal(f.observer.baseline,null);f.observer.disable();
    }
    const f=raisedFixture(version),serial=f.observer.serial,barrier=f.observer.nonRaisedBarrier;
    f.actor.emit('destroy');assert.equal(f.observer.serial,serial+1);assert.equal(f.observer.nonRaisedBarrier,barrier+1);
    assert.equal(f.observer.baseline,null);assert(f.observer.deadActors.has(f.actor));
    f.observer.Read();assert.equal(f.observer.baseline,null);f.window.emit('raised');
    assert.equal(f.observer.serial,serial+2);f.observer.disable();
  }
});

test('fingerprint depth/size/count and unknown inventory bounds refuse without changing Read schema',()=>{
  for(const kind of ['depth','size','count','duplicate','too-many','unknown-value']) {
    const f=raisedFixture(),original=f.observer.snapshot;
    if(kind==='duplicate')f.state.actors.push(f.actor);
    else if(kind==='too-many') {
      // Fingerprint admission refuses, while snapshot keeps its existing bound/error.
      const actors=Array(201).fill(f.actor);f.global.get_window_actors=()=>actors;
      assert.throws(()=>f.observer.Read(),/Too many windows/);
    } else {
      let value;
      if(kind==='depth'){value={};let next=value;for(let i=0;i<13;i++){next.child={};next=next.child;}}
      if(kind==='size')value='x'.repeat(262145);
      if(kind==='count')value=Array(20001).fill(1);
      if(kind==='unknown-value')value=new Date();
      f.observer.snapshot=function(){return {...original.call(this),unknownSafetyField:value};};
    }
    if(kind!=='too-many')f.observer.Read();assert.equal(f.observer.baseline,null);
    const serial=f.observer.serial;f.window.emit('raised');assert.equal(f.observer.serial,serial+1);f.observer.disable();
  }
});

test('new parent or hidden actor identities refuse safe-integer exhaustion without replacing cached identities',()=>{
  for(const version of ['46.0','48.4','49.5','50.5']) {
    for(const hiddenParent of [false,true]) {
      const f=raisedFixture(version),hidden=hiddenParent ? anotherWindow(f,{visible:false}) : null;
      if(hidden)f.observer.Read();const oldId=f.observer.actorIds.get(f.actor),serial=f.observer.serial;
      const parent={};(hidden?.actor ?? f.actor).get_parent=()=>parent;
      f.observer.nextId=Number.MAX_SAFE_INTEGER;f.window.emit('raised');
      assert.equal(f.observer.serial,serial+1);assert.equal(f.observer.baseline,null);
      assert.equal(f.observer.nextId,Number.MAX_SAFE_INTEGER);assert(!f.observer.actorIds.has(parent));
      assert.equal(f.observer.actorIds.get(f.actor),oldId);assert.equal(f.observer.actorId(f.actor),oldId);
      f.observer.disable();
    }
    const f=raisedFixture(version),oldId=f.observer.actorIds.get(f.actor);
    f.observer.nextId=Number.MAX_SAFE_INTEGER;const hidden=anotherWindow(f,{visible:false});
    const read=JSON.parse(f.observer.Read());assert.equal(read.windows.length,1);assert.equal(f.observer.baseline,null);
    assert(!f.observer.actorIds.has(hidden.actor));assert.equal(f.observer.actorIds.get(f.actor),oldId);
    const serial=f.observer.serial;f.window.emit('raised');assert.equal(f.observer.serial,serial+1);f.observer.disable();
  }
});

test('new workspace identity refuses exhaustion and shared identity allocation preserves the last safe integer',()=>{
  for(const version of ['46.0','48.4','49.5','50.5']) {
    const f=raisedFixture(version),oldWorkspace=f.global.workspace_manager.get_active_workspace(),
      oldId=f.observer.workspaceIds.get(oldWorkspace),workspace={index:()=>1},serial=f.observer.serial;
    f.observer.nextId=Number.MAX_SAFE_INTEGER;f.global.workspace_manager.get_active_workspace=()=>workspace;
    f.window.emit('raised');assert.equal(f.observer.serial,serial+1);assert.equal(f.observer.baseline,null);
    assert.throws(()=>f.observer.Read(),/identity counter exhausted/);assert.equal(f.observer.baseline,null);
    assert(!f.observer.workspaceIds.has(workspace));assert.equal(f.observer.workspaceIds.get(oldWorkspace),oldId);
    f.window.emit('raised');assert.equal(f.observer.serial,serial+2);assert(!f.observer.workspaceIds.has(workspace));f.observer.disable();
    const g=raisedFixture(version),last={};g.observer.nextId=Number.MAX_SAFE_INTEGER-1;
    assert.equal(g.observer.actorId(last),Number.MAX_SAFE_INTEGER);assert.equal(g.observer.actorId(last),Number.MAX_SAFE_INTEGER);
    const nextWorkspace={index:()=>1};g.global.workspace_manager.get_active_workspace=()=>nextWorkspace;
    assert.throws(()=>g.observer.Read(),/identity counter exhausted/);assert(!g.observer.workspaceIds.has(nextWorkspace));
    assert.equal(g.observer.actorIds.get(last),Number.MAX_SAFE_INTEGER);g.observer.disable();
    const h=raisedFixture(version),lastWorkspace={index:()=>1};h.observer.nextId=Number.MAX_SAFE_INTEGER-1;
    h.global.workspace_manager.get_active_workspace=()=>lastWorkspace;h.observer.Read();assert(h.observer.baseline);
    assert.equal(h.observer.workspaceIds.get(lastWorkspace),Number.MAX_SAFE_INTEGER);
    const foreignActor={};assert.throws(()=>h.observer.actorId(foreignActor),/identity counter exhausted/);
    assert(!h.observer.actorIds.has(foreignActor));assert.equal(h.observer.workspaceIds.get(lastWorkspace),Number.MAX_SAFE_INTEGER);
    assert.equal(h.observer.baseline,null);h.observer.disable();
  }
  for(const value of [NaN,Infinity,-1,1.5,Number.MAX_SAFE_INTEGER+1]) {
    const f=raisedFixture(),oldId=f.observer.actorIds.get(f.actor),parent={};
    f.actor.get_parent=()=>parent;f.observer.nextId=value;const serial=f.observer.serial;
    f.window.emit('raised');assert.equal(f.observer.serial,serial+1);assert.equal(f.observer.baseline,null);
    assert(!f.observer.actorIds.has(parent));assert.equal(f.observer.actorIds.get(f.actor),oldId);f.observer.disable();
  }
});
