// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,rmSync,existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {installProfile,recoverInstall} from '../services/workspaces/install.mjs';
import {preferences,profileStatePath} from '../services/workspaces/profiles.mjs';
import {spawn,spawnSync} from 'node:child_process';
import {once} from 'node:events';
import {guardWorkspaceMethod} from '../services/workspaces/policy.mjs';
import {apply} from '../adapters/dsh-workspace/policy.mjs';
const root=new URL('..',import.meta.url).pathname;
function fixture(t){const dir=mkdtempSync(join(tmpdir(),'sdk-product-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));const home=join(dir,'dsh'),profilesDir=join(dir,'profiles');mkdirSync(join(home,'.agent-presets/augmentor-browser-product'),{recursive:true});mkdirSync(profilesDir);writeFileSync(join(home,'.agent-presets/augmentor-browser-product/agent.cordis.yml'),JSON.stringify([{id:'persona',config:{prefix:'Base'}}]));writeFileSync(join(dir,'role.md'),'Fixture role');const profile={schemaVersion:1,sdkProtocol:'augmentor-app/1',id:'fixture',name:'Fixture',preset:'augmentor-fixture',cwd:dir,memory:{person:'fixture',project:dir},parentOrigin:'http://127.0.0.1:9876',publicPath:'/augmentor/',instructions:[join(dir,'role.md')],tools:[],policy:{tools:['fixture_read'],voice:false,sharedSettings:false}};return {dir,home,profilesDir,profile,root};}
test('installation rolls back all registered state after a mid-commit failure',t=>{
 const f=fixture(t);installProfile(f.profile,f);const before=readFileSync(join(f.profilesDir,'fixture.json'),'utf8');
 assert.throws(()=>installProfile({...f.profile,name:'Changed'},{...f,fault:i=>{if(i===2)throw Error('Injected interrupted write');}}),/Injected/);
 assert.equal(readFileSync(join(f.profilesDir,'fixture.json'),'utf8'),before);assert.equal(existsSync(join(f.profilesDir,'fixture.installing')),false);
 assert.equal(existsSync(join(f.profilesDir,'.install.lock')),false);
});
test('registration rejects preset collisions and accidental memory migrations',t=>{
 const f=fixture(t);installProfile(f.profile,f);
 assert.throws(()=>installProfile({...f.profile,id:'other'},f),/another workspace/);
 assert.throws(()=>installProfile({...f.profile,memory:{person:'personal',project:f.dir}},f),/preserved/);
});
test('SDK workspaces cannot administer shared runtime or enable tools through settings',t=>{
 const f=fixture(t);process.env.XDG_STATE_HOME=f.dir;
 for(const method of ['settings.mutate','augmentor/dsh','augmentor/home','augmentor/diagnostics','augmentor/surface'])assert.throws(()=>guardWorkspaceMethod(f.profile,method),/cannot administer/);
 assert.throws(()=>guardWorkspaceMethod(f.profile,'augmentor/voice/start'),/disabled/);
 guardWorkspaceMethod(f.profile,'session.prompt');guardWorkspaceMethod(f.profile,'augmentor/voice/control');
});
test('monotonic tool guard denies ungranted tools and wrong workspace; revocation is read live',t=>{
 const f=fixture(t);process.env.AUGMENTOR_WORKSPACE_PROFILES=f.profilesDir;installProfile(f.profile,f);let guard;
 apply({tools:{guard:g=>{guard=g;},presentAs:()=>{}}},{profileId:'fixture'});
 const exec={name:'fixture_read',agent:{session:{header:{agentPreset:f.profile.preset,cwd:f.dir}}}};
 assert.equal(guard(exec),undefined);assert.match(guard({...exec,name:'bash'}),/not granted/);
 assert.match(guard({...exec,agent:{session:{header:{agentPreset:'personal',cwd:f.dir}}}}),/does not belong/);
 writeFileSync(join(f.profilesDir,'fixture.json'),JSON.stringify({...f.profile,policy:{...f.profile.policy,tools:[]}}));assert.match(guard(exec),/not granted/);
});
test('SDK profile fails closed if DSH lacks the monotonic guard API',t=>{
 const f=fixture(t);process.env.AUGMENTOR_WORKSPACE_PROFILES=f.profilesDir;installProfile(f.profile,f);
 assert.throws(()=>apply({tools:{}},{profileId:'fixture'}),/lacks/);
});
test('a killed installer leaves a recoverable transaction and preserves the previous profile',t=>{
 const f=fixture(t);installProfile(f.profile,f);const before=readFileSync(join(f.profilesDir,'fixture.json'),'utf8');
 const code=`import {installProfile} from ${JSON.stringify(new URL('../services/workspaces/install.mjs',import.meta.url).href)};const f=${JSON.stringify(f)};installProfile({...f.profile,name:'Interrupted'},{...f,fault:i=>{if(i===2)process.exit(99)}});`;
 assert.equal(spawnSync(process.execPath,['--input-type=module','-e',code]).status,99);
 assert.equal(existsSync(join(f.profilesDir,'fixture.installing')),true);
 assert.equal(recoverInstall(f),true);assert.equal(readFileSync(join(f.profilesDir,'fixture.json'),'utf8'),before);
 assert.equal(existsSync(join(f.profilesDir,'fixture.installing')),false);
});
test('workspace installation cannot overwrite an unregistered preset',t=>{
 const f=fixture(t);mkdirSync(join(f.home,'.agent-presets',f.profile.preset));assert.throws(()=>installProfile(f.profile,f),/outside this workspace/);
});
test('preferences remain writable after a competing writer is killed',async t=>{
 const f=fixture(t);process.env.XDG_STATE_HOME=f.dir;preferences(f.profile,{set:{preserved:true}});
 const file=profileStatePath(f.profile)+'.lock.sqlite';
 const child=spawn(process.execPath,['--input-type=module','-e',`import {DatabaseSync} from 'node:sqlite';const db=new DatabaseSync(${JSON.stringify(file)});db.exec('BEGIN IMMEDIATE');process.stdout.write('locked');setInterval(()=>{},1000);`],{stdio:['ignore','pipe','ignore']});
 t.after(()=>child.kill());await once(child.stdout,'data');const exit=once(child,'exit');child.kill('SIGKILL');await exit;
 assert.deepEqual(preferences(f.profile,{set:{next:true}}),{preserved:true,next:true});
 assert.throws(()=>preferences(f.profile,{remove:'preserved'}),/Invalid/);
});
