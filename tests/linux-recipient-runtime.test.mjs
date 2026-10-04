// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,chmodSync,rmSync,symlinkSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {recipientSelectionPath,selectedRecipientPython} from '../dist/platform/src/recipient.js';

const sha=raw=>createHash('sha256').update(raw).digest('hex');
function fixture(t){
  const home=mkdtempSync(join(tmpdir(),'recipient-node-'));t.after(()=>rmSync(home,{recursive:true,force:true}));
  const app=join(home,'app'),base=join(home,'official'),root=join(home,'modified');
  for(const path of [app,base,root])mkdirSync(path,{mode:0o700});
  const write=(path,value,mode=0o644)=>{writeFileSync(path,typeof value==='string'?value:JSON.stringify(value));chmodSync(path,mode);return sha(readFileSync(path));};
  const policy={profile:'noble-cp312-x86_64-source-qt-voice',pythonAbi:[3,12],sourceQt:{qtVersion:'6.8.2'}};
  const identity={root:app,releaseSha256:write(join(app,'release.json'),{source:'synthetic',version:'0.2.13'}),policySha256:write(join(app,'linux-python-runtime.json'),policy)};
  mkdirSync(join(root,'qt'));
  const files={};for(const name of ['pyvenv.cfg','wheel-lock.txt','qt/stage-inventory.json'])files[name]=write(join(root,name),'unchanged '+name);
  files['qt/lib/libQt6Core.so.6.8.2']=sha('changed recipient core');
  files['lib/python3.12/site-packages/keyring/__init__.py']=sha('unchanged keyring');
  const baseFiles={...files,'qt/lib/libQt6Core.so.6.8.2':sha('official core')};
  const baseReceipt={files:baseFiles,lockIdentity:'official identity'};
  const receipt={format:'augmentor-recipient-runtime/1',app:identity,officialPython:join(base,'bin/python3'),
    officialReceiptSha256:write(join(base,'augmentor-python-runtime.json'),baseReceipt,0o600),officialLockIdentity:baseReceipt.lockIdentity,
    root,python:join(root,'bin/python3'),abi:{pythonAbi:[3,12],qtVersion:'6.8.2',pysideVersion:'6.8.2.1',shibokenVersion:'6.8.2.1'},files};
  const env={HOME:home,XDG_DATA_HOME:join(home,'data'),AUGMENTOR_PYTHON:receipt.python,AUGMENTOR_OFFICIAL_PYTHON:receipt.officialPython,
    AUGMENTOR_RECIPIENT_RECEIPT:join(root,'augmentor-recipient-runtime.json')};
  const selection={format:'augmentor-recipient-runtime-selection/1',app:identity,officialPython:receipt.officialPython,receipt:env.AUGMENTOR_RECIPIENT_RECEIPT};
  const path=recipientSelectionPath(app,env);mkdirSync(join(home,'data/augmentor/recipient-runtimes'),{recursive:true,mode:0o700});
  const bind=()=>{
    selection.receiptSha256=write(selection.receipt,receipt,0o600);
    env.AUGMENTOR_RECIPIENT_RECEIPT_SHA256=selection.receiptSha256;
    env.AUGMENTOR_RECIPIENT_SELECTION_SHA256=write(path,selection,0o600);
  };bind();
  for(const [key,name] of Object.entries({LD_LIBRARY_PATH:'lib',QT_PLUGIN_PATH:'plugins',QT_QPA_PLATFORM_PLUGIN_PATH:'plugins/platforms',QML_IMPORT_PATH:'qml',QML2_IMPORT_PATH:'qml'}))env[key]=join(root,'qt',name);
  let calls=0;const official=baseEnv=>{calls++;assert.equal(baseEnv.AUGMENTOR_PYTHON,receipt.officialPython);assert.equal(baseEnv.LD_LIBRARY_PATH,join(base,'qt/lib'));return receipt.officialPython;};
  return {app,base,root,receipt,env,selection,path,bind,official,write,calls:()=>calls};
}

test('Node uses the explicit recipient executable after checking its official base and matching environment',t=>{
  const f=fixture(t);assert.equal(selectedRecipientPython(f.app,f.env,f.official),f.receipt.python);assert.equal(f.calls(),1);
});
test('direct Node without a cold verified environment refuses an explicit selection',t=>{
  const f=fixture(t);delete f.env.AUGMENTOR_RECIPIENT_RECEIPT_SHA256;
  assert.throws(()=>selectedRecipientPython(f.app,f.env,f.official),/verified selection/);assert.equal(f.calls(),0);
});
test('changed receipt and changed application identity are refused before official callback',t=>{
  const f=fixture(t);writeFileSync(f.selection.receipt,readFileSync(f.selection.receipt)+'\n');
  assert.throws(()=>selectedRecipientPython(f.app,f.env,f.official),/verified selection/);f.bind();
  f.write(join(f.app,'release.json'),{source:'different app'});
  assert.throws(()=>selectedRecipientPython(f.app,f.env,f.official),/stale application/);assert.equal(f.calls(),0);
});
test('even a newly rebound receipt cannot use a wrong ABI or changed non-Qt bytes',t=>{
  const f=fixture(t);f.receipt.abi.pythonAbi=[3,13];f.bind();
  assert.throws(()=>selectedRecipientPython(f.app,f.env,f.official),/ABI/);
  f.receipt.abi.pythonAbi=[3,12];f.receipt.files['lib/python3.12/site-packages/keyring/__init__.py']=sha('changed');f.bind();
  assert.throws(()=>selectedRecipientPython(f.app,f.env,f.official),/non-Qt/);
});
test('native paths, configuration, malformed selection and symlink receipt cannot be adopted',t=>{
  const f=fixture(t);const env={...f.env,LD_LIBRARY_PATH:'/foreign'};
  assert.throws(()=>selectedRecipientPython(f.app,env,f.official),/environment changed/);
  f.write(join(f.root,'pyvenv.cfg'),'changed config');
  assert.throws(()=>selectedRecipientPython(f.app,f.env,f.official),/configuration changed/);
  f.write(join(f.root,'pyvenv.cfg'),'unchanged pyvenv.cfg');
  f.write(f.path,[] ,0o600);assert.throws(()=>selectedRecipientPython(f.app,f.env,f.official),/Malformed/);f.bind();
  const raw=readFileSync(f.selection.receipt);rmSync(f.selection.receipt);f.write(join(f.root,'alias'),raw.toString(),0o600);symlinkSync(join(f.root,'alias'),f.selection.receipt);
  assert.throws(()=>selectedRecipientPython(f.app,f.env,f.official),/ELOOP/);
});
test('selection replacement during official verification refuses before any child launch',t=>{
  const f=fixture(t);const official=env=>{const result=f.official(env);writeFileSync(f.path,readFileSync(f.path)+'\n');return result;};
  assert.throws(()=>selectedRecipientPython(f.app,f.env,official),/changed during validation/);
});
