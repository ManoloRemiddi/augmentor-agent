// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,rmSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';
import {readDiscovery} from '../discovery.mjs';
test('discovery snapshots never confer authority or expose extra fields and reject oversized inventories',t=>{
 const dir=mkdtempSync(join(tmpdir(),'home-discovery-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));
 assert.deepEqual(readDiscovery(dir),{devices:[],scanned_at:null});
 const file=join(dir,'discovered-devices.json');
 writeFileSync(file,JSON.stringify({scanned_at:new Date().toISOString(),devices:[{name:'Lamp',host:'192.0.2.1',model:'fixture',status:'control',control:true,key:'must-not-leak',entity_id:'switch.injected'}]}));
 assert.deepEqual(readDiscovery(dir).devices,[{name:'Lamp',host:'192.0.2.1',model:'fixture',status:'needs_setup'}]);
 writeFileSync(file,'x'.repeat(131073));assert.throws(()=>readDiscovery(dir),/too large/);
});
