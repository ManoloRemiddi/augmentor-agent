// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';

const source=readFileSync(new URL('../services/desktop/cinnamon-extension/bridge@augmentoragent.com/extension.js',import.meta.url),'utf8');
const name='org.cinnamon.ScreenSaver';

function fixture({version='6.6.4',wayland=false}={}) {
  const calls=[],signals=new Map();let next=0,exported=null;
  const bus={
    call(destination,path,iface,method,args,type,flags,timeout,cancel,callback) {
      calls.push({destination,path,iface,method,args,type,flags,timeout,cancel,callback});
    },
    call_finish(result) {if(result.error)throw result.error;return {deep_unpack:()=>result.values};},
    signal_subscribe(sender,iface,signal,path,arg,flags,callback) {
      const id=++next;signals.set(id,{sender,iface,signal,path,arg,callback});return id;
    },
    signal_unsubscribe(id) {signals.delete(id);},
    connect() {return 1234;},disconnect() {},
  };
  const manager={bindings:new Map([[1,{name:'media-key',bindings:['<Control>l'],callback:()=>{throw Error('Never export/invoke');}}]]),applet_bindings:new Map()};
  const context=vm.createContext({Map,imports:{byteArray:{fromString:value=>Buffer.from(value,'utf8')},
    gi:{
      Gio:{DBus:{session:bus},DBusCallFlags:{NONE:0,NO_AUTO_START:1},DBusSignalFlags:{NONE:0},
        Cancellable:class {cancel(){this.cancelled=true;}},DBusError:{get_remote_error:error=>error.remote},
        DBusExportedObject:{wrapJSObject:(xml,obj)=>({export(){exported={xml,obj};},unexport(){exported=null;}})}},
      GLib:{uuid_string_random:()=> '11111111-2222-3333-4444-555555555555',Variant:class {constructor(type,values){this.type=type;this.values=values;}},
        VariantType:class {constructor(type){this.type=type;}},ChecksumType:{SHA256:1},
        compute_checksum_for_string:(_kind,value)=>createHash('sha256').update(value).digest('hex')},
      Meta:{is_wayland_compositor:()=>wayland},
    },misc:{config:{PACKAGE_VERSION:version}},ui:{main:{keybindingManager:manager}},
  }});
  vm.runInContext(source,context);
  function enable(){vm.runInContext('enable()',context);return exported.obj;}
  function disable(){vm.runInContext('disable()',context);}
  function take(method){const index=calls.findIndex(c=>c.method===method);assert.notEqual(index,-1,method);return calls.splice(index,1)[0];}
  function finish(call,values,error){call.callback(bus,{values,error});}
  function reply(method,values,error){const c=take(method);finish(c,values,error);return c;}
  function owner(old,nextOwner){for(const s of [...signals.values()])if(s.signal==='NameOwnerChanged')s.callback(bus,'org.freedesktop.DBus','','','',{deep_unpack:()=>[name,old,nextOwner]});}
  function active(sender,value){for(const s of [...signals.values()])if(s.signal==='ActiveChanged'&&s.sender===sender)s.callback(bus,sender,'','','',{deep_unpack:()=>[value]});}
  return {enable,disable,take,finish,reply,owner,active,manager,calls,signals,exported:()=>exported};
}

function settle(f,owner=':1.20',active=false){
  f.reply('GetNameOwner',[owner]);
  const q=f.reply('GetActive',[active]);assert.equal(q.destination,owner);assert.equal(q.flags,1);
  f.reply('GetNameOwner',[owner]);
}

test('strict unsupported running profile exports no bridge',()=>{
  for(const options of [{version:'6.6.5'},{version:'7.0.0'},{wayland:true}]){
    const f=fixture(options);assert.throws(()=>f.enable(),/6\.6\.4 X11/);assert.equal(f.exported(),null);assert.equal(f.signals.size,0);
  }
});

test('activation reply is discovery only; owner-pinned reply grants fresh inactivity',()=>{
  const f=fixture(),b=f.enable();assert.equal(JSON.parse(b.Status()).lock.state,'unknown');
  assert.equal(JSON.parse(b.RefreshLock()).lock.state,'unknown');
  f.reply('GetNameOwner',null,{remote:'org.freedesktop.DBus.Error.NameHasNoOwner'});
  const activation=f.take('GetActive');assert.equal(activation.destination,name);assert.equal(activation.flags,0);
  f.owner('',':1.20');f.finish(activation,[false]);assert.equal(JSON.parse(b.Status()).lock.state,'unknown');
  const pinned=f.reply('GetActive',[false]);assert.equal(pinned.destination,':1.20');
  f.reply('GetNameOwner',[':1.20']);assert.equal(JSON.parse(b.Status()).lock.state,'inactive');
});

test('owner loss invalidates in-flight inactive reply without automatic restart',()=>{
  const f=fixture(),b=f.enable();b.RefreshLock();f.reply('GetNameOwner',[':1.20']);const old=f.take('GetActive');
  const generation=JSON.parse(b.Status()).lock.generation;f.owner(':1.20','');f.finish(old,[false]);
  const state=JSON.parse(b.Status()).lock;assert.equal(state.state,'unknown');assert.equal(state.owner,null);
  assert(state.generation>generation);assert.equal(f.calls.length,0);assert.equal(state.queryPending,false);
});

test('active event supersedes negative query; negative event needs a fresh pinned query',()=>{
  const f=fixture(),b=f.enable();b.RefreshLock();f.reply('GetNameOwner',[':1.20']);const old=f.take('GetActive');
  f.active(':1.20',true);f.finish(old,[false]);assert.equal(JSON.parse(b.Status()).lock.state,'active');
  f.active(':1.20',false);assert.equal(JSON.parse(b.Status()).lock.state,'unknown');
  b.RefreshLock();settle(f);assert.equal(JSON.parse(b.Status()).lock.state,'inactive');
});

test('replacement while final owner check is pending rejects old inactivity',()=>{
  const f=fixture(),b=f.enable();b.RefreshLock();f.reply('GetNameOwner',[':1.20']);f.reply('GetActive',[false]);
  const old=f.take('GetNameOwner');f.owner(':1.20',':1.21');f.finish(old,[':1.20']);
  assert.equal(JSON.parse(b.Status()).lock.state,'unknown');f.reply('GetActive',[false]);f.reply('GetNameOwner',[':1.21']);
  assert.equal(JSON.parse(b.Status()).lock.owner,':1.21');assert.equal(JSON.parse(b.Status()).lock.state,'inactive');
});

test('disable cancels discovery and late replies cannot recreate export',()=>{
  const f=fixture(),b=f.enable();b.RefreshLock();const old=f.take('GetNameOwner');f.disable();f.finish(old,[':1.20']);
  assert.equal(f.exported(),null);assert.equal(f.signals.size,0);assert.throws(()=>b.Status(),/disabled/);assert.equal(f.calls.length,0);
});

test('fresh bounded snapshots omit callbacks and report deferred spice registration',()=>{
  const f=fixture(),b=f.enable();const before=JSON.parse(b.ShortcutBindings());
  assert.deepEqual(before.bindings,[{name:'media-key',accelerators:['<Control>l']}]);
  assert.equal(before.inputQualified,false);assert.equal(before.completeRegistryHistoryTracking,false);
  f.manager.applet_bindings.set('spice',new Map([['commitTimeoutId',7]]));
  f.manager.bindings.set(2,{name:'spice',bindings:['<Super>k'],callback:()=>{throw Error('Never invoke');}});
  const next=JSON.parse(b.ShortcutBindings());assert.equal(next.registryPending,true);
  assert(next.registrySerial>before.registrySerial);assert.notEqual(next.snapshotSignature,before.snapshotSignature);
  f.manager.bindings.get(2).bindings=[{}];assert.throws(()=>b.ShortcutBindings(),/invalid entry/);
});

test('failed or malformed lock replies remain unknown and can be queried freshly',()=>{
  const f=fixture(),b=f.enable();b.RefreshLock();f.reply('GetNameOwner',[':1.20']);f.reply('GetActive',['false']);
  assert.equal(JSON.parse(b.Status()).lock.state,'unknown');assert.equal(JSON.parse(b.Status()).lock.queryPending,false);
  b.RefreshLock();settle(f);assert.equal(JSON.parse(b.Status()).lock.state,'inactive');
});

test('oversized Unicode registry refuses by actual UTF8 bytes without truncation',()=>{
  const f=fixture(),b=f.enable();
  f.manager.bindings.set(2,{name:'unicode-a',bindings:Array(64).fill('☃'.repeat(512)),callback:()=>{}});
  f.manager.bindings.set(3,{name:'unicode-b',bindings:Array(64).fill('☃'.repeat(512)),callback:()=>{}});
  assert.throws(()=>b.ShortcutBindings(),/too large/);
});

test('startup negative signal cannot grant inactivity and supersedes the old query',()=>{
  const f=fixture(),b=f.enable();b.RefreshLock();f.reply('GetNameOwner',[':1.20']);const old=f.take('GetActive');
  f.active(':1.20',false);f.finish(old,[false]);assert.equal(JSON.parse(b.Status()).lock.state,'unknown');
  const fresh=f.reply('GetActive',[false]);assert.equal(fresh.destination,':1.20');assert.equal(fresh.timeout,3000);
  f.reply('GetNameOwner',[':1.20']);assert.equal(JSON.parse(b.Status()).lock.state,'inactive');
});
