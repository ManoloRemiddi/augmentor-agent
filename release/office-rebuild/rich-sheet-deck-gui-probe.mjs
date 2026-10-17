// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual original spreadsheet/PDF controls with authored rich fixtures, in a private Host.
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {mkdtemp,readFile,writeFile,rm,mkdir,lstat} from 'node:fs/promises';
import {join,resolve,dirname} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {chromiumPort} from '../../tests/fixtures/chromium-ready.mjs';
import {harnessCdp} from '../../tests/fixtures/harness-cdp.mjs';
import {harnessPointerClick} from '../../tests/fixtures/harness-pointer.mjs';

const root=fileURLToPath(new URL('../..',import.meta.url)),[appArg,fixturesArg,outputArg,...extra]=process.argv.slice(2);
if(!appArg||!fixturesArg||!outputArg||extra.length)throw Error('Usage: rich-sheet-deck-gui-probe.mjs UNSELECTED_THIN_APP AUTHORED_FIXTURES NEW_OUTPUT');
assert.equal(process.platform,'linux');assert.equal(process.version,'v24.19.0');
const app=resolve(appArg),fixtures=resolve(fixturesArg),destination=resolve(outputArg),outputs=join(root,'outputs');
assert(app.startsWith(outputs+'/')&&fixtures.startsWith(outputs+'/')&&dirname(destination)===outputs);
for(const name of [join(app,'desktop-release.json'),destination]){
  try{await lstat(name);throw Error('Refuse sealed app or existing output.');}catch(error){if(error.code!=='ENOENT')throw error;}
}
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const manifest=JSON.parse(await readFile(join(fixtures,'fixtures.json'),'utf8'));
assert.equal(manifest.schema,'augmentor-rich-office-fixtures/1');
const proof=JSON.parse(await readFile(join(root,'release/office-rebuild/thin-engine-qualification.json'),'utf8'));
assert.equal(JSON.parse(await readFile(join(app,'dist/runtime/vendor/office-entry/package.json'),'utf8')).version,'0.1.3-augmentor.thin.1');
assert.equal(sha(await readFile(join(app,'node_modules/@augmentor/office-engine-wasm/assets/soffice.wasm'))),proof.build.assets['soffice.wasm'].sha256);
const {PiConnection}=await import(pathToFileURL(join(app,'dist/client/src/socket.js')));
const {localConnect}=await import(pathToFileURL(join(app,'dist/platform/src/transport.js')));
await mkdir(destination,{mode:0o700});
async function until(fn,label){
  const end=Date.now()+12000;let last;
  while(Date.now()<end){try{if(await fn())return;}catch(error){last=error;}await new Promise(r=>setTimeout(r,30));}
  throw Error(label+(last?' '+last.message:''));
}
test('rich legacy/modern sheets and decks retain actual original controls, parsers, readonly state and native evidence',
  {timeout:120000},async t=>{
  const profile=await mkdtemp(join(tmpdir(),'augmentor-rich-sheet-deck-'));
  let fixture,chrome,panel,owner,link,output='',stderr='';
  t.after(async()=>{
    owner?.close();panel?.close();
    for(const child of [chrome,fixture])if(child?.pid&&child.exitCode===null){const end=once(child,'exit');child.kill('SIGTERM');await end;}
    await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});
  });
  const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(key)));
  if(process.env.AUGMENTOR_PYTHON)env.AUGMENTOR_PYTHON=process.env.AUGMENTOR_PYTHON;
  fixture=spawn(process.execPath,[join(root,'scripts/harness-ui-proof.mjs')],{cwd:app,
    env:{...env,AUGMENTOR_PI_TEST_ROOT:app,AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS:'1',AUGMENTOR_HARNESS_PROOF_FILE_PREVIEWS:'1'},stdio:['ignore','pipe','pipe']});
  fixture.stdout.on('data',bytes=>output+=bytes);fixture.stderr.on('data',bytes=>stderr+=bytes);
  await until(()=>{assert.equal(fixture.exitCode,null,stderr);try{link=JSON.parse(output.split('\n').find(l=>l.startsWith('{"fixture"')));return !!link;}catch{return false;}},'private Host ready');
  const url=new URL(link.url),token=new URLSearchParams(url.hash.slice(1)).get('token'),sid='rich-sheet-deck';
  const rpc=async(method,params={})=>{
    const response=await fetch(url.origin+'/api/rpc',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({id:crypto.randomUUID(),method,params})});
    const frame=await response.json();if(frame.error)throw Error(frame.error.message);return frame.result;
  };
  const socket=localConnect(join(link.state,'runtime.sock'));await once(socket,'connect');owner=new PiConnection(socket);await owner.call('host.hello',{protocol:'augmentor-pi/1'});
  const selection=(await rpc('models.list')).default;
  await rpc('session.create',{sessionId:sid,cwd:link.workspace,selection});
  await rpc('session.prompt',{sessionId:sid,requestId:'authored-rich-seed',content:[{type:'text',text:'Independent fixture seed; no Office content.'}]});
  await until(async()=>(await rpc('session.history',{sessionId:sid})).events.some(row=>row.event.type==='turn/end'),'synthetic seed settled');
  const history=await rpc('session.history',{sessionId:sid}),requests=await readFile(link.requestLog,'utf8');
  const meta=JSON.parse(await readFile(join(link.state,'sessions',sid+'.meta.json'),'utf8')),native=await readFile(meta.file);
  const scope=new URLSearchParams(url.hash.slice(1));scope.set('session',sid);url.hash=scope.toString();
  chrome=spawn(process.env.CHROMIUM_BIN??'chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,url.href],{env,stdio:'ignore'});
  let port;await until(async()=>{try{port=await chromiumPort(profile);return !!port;}catch{return false;}},'Chrome ready');
  const target=(await fetch('http://127.0.0.1:'+port+'/json').then(r=>r.json())).find(row=>row.type==='page');
  panel=await harnessCdp(target.webSocketDebuggerUrl);
  for(const domain of ['Runtime','Log','Network','Page'])await panel.call(domain+'.enable');
  await panel.call('Page.addScriptToEvaluateOnNewDocument',{source:`(()=>{const WorkerBase=window.Worker,draw=CanvasRenderingContext2D.prototype.fillText;window.__richDraws=[];window.__richWorkers=[];CanvasRenderingContext2D.prototype.fillText=function(text,...args){window.__richDraws.push(String(text));return draw.call(this,text,...args);};window.Worker=class extends WorkerBase{constructor(url,options){super(url,options);this.observation={url:String(url),native:this instanceof WorkerBase,terminated:false};window.__richWorkers.push(this.observation);}terminate(){this.observation.terminated=true;return super.terminate();}};})();`});
  await panel.reload();
  const visible=expression=>until(()=>panel.evaluate('Boolean('+expression+')'),expression).catch(async error=>{error.message+=' '+JSON.stringify({body:await panel.evaluate('document.body.innerText'),errors:panel.errors,stderr});throw error;});
  const click=expression=>harnessPointerClick(panel,expression,until),composer='document.querySelector("[contenteditable=true]")';
  const parse=async(bytes,format)=>panel.evaluate(`new Promise((resolve,reject)=>{const worker=new Worker('/dsh-excel-worker-0.2.1-alpha.2.mjs',{type:'module'}),timer=setTimeout(()=>{worker.terminate();reject(Error('Parser observation expired'));},12000);worker.onmessage=e=>{clearTimeout(timer);worker.terminate();resolve(e.data);};worker.onerror=()=>{clearTimeout(timer);worker.terminate();reject(Error('Actual parser Worker failed'));};const bytes=Uint8Array.from(${JSON.stringify([...bytes])});worker.postMessage({bytes,format:${JSON.stringify(format)},limits:{maxBytes:16777216,maxCells:250000,timeoutMs:15000}},[bytes.buffer]);})`);
  const results=[];
  for(const extension of ['xlsx','xls','pptx','ppt']){
    await panel.call('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});
    await visible(composer+'&&!'+composer+'.hasAttribute("aria-disabled")');
    const specification=manifest.fixtures.find(row=>row.extension===extension),body=await readFile(join(fixtures,specification.file));
    assert.equal(sha(body),specification.sha256);
    const filename='rich-'+(['xlsx','pptx'].includes(extension)?'modern':'legacy')+'.'+extension,file=join(link.workspace,filename);
    await writeFile(file,body);
    const sheets=extension==='xlsx'||extension==='xls';let parsed;
    if(sheets){
      parsed=await parse(body,extension);assert.equal(parsed.ok,true,JSON.stringify(parsed));
      assert.deepEqual(parsed.value.sheets.map(row=>row.name),['Numbers','Review']);
      const cell=(sheet,r,c)=>sheet.celldata.find(row=>row.r===r&&row.c===c)?.v;
      const [numbers,review]=parsed.value.sheets;
      assert.equal(cell(numbers,2,3).v,58.5);assert.equal(cell(numbers,2,3).f,'=B3*C3');
      assert.equal(cell(numbers,4,3).v,83);assert.equal(cell(numbers,4,3).f,'=SUM(D3:D4)');
      assert.equal(cell(review,0,1).v,41.5);assert.equal(cell(review,0,1).f,'=Numbers!D5/2');
      assert.equal(cell(review,1,1).v,'=2+2 is literal text');assert.equal(cell(review,1,1).f,undefined);
      assert.equal(numbers.config.merge['0_0'].cs,4);assert(numbers.config.rowhidden['5']!==undefined);
    }
    if(await panel.evaluate(composer+'.textContent.trim()!==""||'+composer+'.querySelector("[data-composer-chip=reference]")!==null')){
      await click(composer);
      for(const type of ['keyDown','keyUp'])await panel.call('Input.dispatchKeyEvent',{type,key:'a',code:'KeyA',windowsVirtualKeyCode:65,modifiers:2});
      for(const type of ['keyDown','keyUp'])await panel.call('Input.dispatchKeyEvent',{type,key:'Backspace',code:'Backspace',windowsVirtualKeyCode:8});
    }
    await visible(composer+'.textContent.trim()===""&&!'+composer+'.querySelector("[data-composer-chip=reference]")');
    await click(composer);
    await visible(composer+'===document.activeElement||'+composer+'.contains(document.activeElement)');
    await panel.call('Input.insertText',{text:' @'+filename});
    await visible(composer+'.textContent.includes('+JSON.stringify(filename)+')');
    const option='Array.from(document.querySelectorAll("[data-trigger-menu] [role=option]")).find(row=>row.textContent.includes('+JSON.stringify(filename)+'))';
    await visible(option);await click(option);await click('document.querySelector("[data-composer-chip=reference]")');
    if(sheets){
      await visible('document.querySelector("[data-excel-preview]")&&window.__richDraws.includes("RICH_ITEM_ALPHA")');
      await visible('window.__richDraws.includes("83.00")');
      assert.equal(await panel.evaluate('document.querySelector(".fortune-fx-input").getAttribute("contenteditable")'),'false');
      const before=await panel.evaluate('document.querySelector(".fortune-fx-input").textContent');
      await click('document.querySelector(".fortune-fx-input")');await panel.call('Input.insertText',{text:'EDIT_ATTEMPT'});
      assert.equal(await panel.evaluate('document.querySelector(".fortune-fx-input").textContent'),before);
      await click('Array.from(document.querySelectorAll(".luckysheet-sheets-item")).find(row=>row.textContent.includes("Review"))');
      await visible('window.__richDraws.includes("RICH_SECOND_SHEET")&&window.__richDraws.includes("41.50")&&window.__richDraws.includes("=2+2 is literal text")');
      await click('Array.from(document.querySelectorAll(".luckysheet-sheets-item")).find(row=>row.textContent.includes("Numbers"))');
    }else{
      const first='document.querySelector("[data-pdf-page=\\"1\\"]")';
      await visible('document.querySelector("[data-pdf-preview]")&&'+first+'.querySelector("canvas").width>0&&'+first+'.innerText.includes("RICH_DECK_PAGE_1")');
      assert.equal(await panel.evaluate('document.querySelectorAll("[data-pdf-page]").length'),3);
      await panel.evaluate('document.querySelector("[data-pdf-page=\\"3\\"]").scrollIntoView({block:"center"})');
      await visible('document.querySelector("[data-pdf-page=\\"3\\"]").innerText.includes("RICH_DECK_PAGE_3")');
      assert(!await panel.evaluate('document.querySelector("[data-pdf-preview]").innerText.includes("RICH_NOTES_SHOULD_NOT_RENDER")'));
      await click('document.querySelector("[data-document-zoom-controls] button[aria-label=\\"Choose zoom\\"]")');
      await click('Array.from(document.querySelectorAll("[role=menuitem]")).find(row=>row.textContent.trim()==="100%")');
      await visible('document.querySelector("[data-document-zoom-mode=fixed]")');
      await panel.evaluate('document.querySelector("[data-pdf-page=\\"1\\"]").scrollIntoView({block:"start"})');
    }
    await writeFile(join(destination,extension+'.png'),Buffer.from((await panel.call('Page.captureScreenshot',{format:'png'})).data,'base64'),{flag:'wx',mode:0o600});
    assert.deepEqual(await readFile(file),body);
    await panel.call('Emulation.setDeviceMetricsOverride',{width:513,height:715,deviceScaleFactor:1,mobile:false});
    await visible('document.querySelector("[data-sidebar-right-panel=fullscreen]")');
    await click('Array.from(document.querySelectorAll("[data-dockkit-tab]")).find(row=>row.textContent.includes('+JSON.stringify(filename)+')).querySelector("[data-dockkit-tab-close]")');
    await visible('!document.querySelector("'+(sheets?'[data-excel-preview]':'[data-pdf-preview]')+'")');
    await until(async()=>{const h=await owner.call('host.describe');return h.activeOfficePreviews===0&&h.activeFilePreviews===0&&h.activeHarnessRequests===0;},'preview HTTP/converter cleanup settled');
    await visible('window.__richWorkers.every(row=>row.native&&row.terminated)');
    assert.deepEqual(await rpc('session.history',{sessionId:sid}),history);assert.deepEqual(await readFile(meta.file),native);assert.equal(await readFile(link.requestLog,'utf8'),requests);
    results.push({extension,inputSha256:specification.sha256,savedFormulaAndLiteralChecks:sheets,mergeHiddenRowsAndSheetControls:sheets,readOnlyFormulaBar:sheets,threeSlidePagesAndNotesExcluded:!sheets,originalZoom:!sheets,narrowFullscreenClose:true,sourceAndNativeEvidenceUnchanged:true});
    await writeFile(join(destination,'progress.json'),JSON.stringify(results,null,2)+'\n');
  }
  const workers=await panel.evaluate('window.__richWorkers');assert(workers.every(row=>row.native&&row.terminated));
  assert(!panel.urls.some(value=>/^https?:/.test(value)&&!value.startsWith(url.origin+'/')));
  assert.deepEqual(panel.errors,[]);
  await writeFile(join(destination,'result.json'),JSON.stringify({schema:'augmentor-rich-sheet-deck-gui/1',cases:results,syntheticSeedUsed:true,realProviderInference:false,officeContentSentToModel:false,nativeHistoryAndRequestLogUnchanged:true,observedBrowserErrors:0,unexpectedObservedHttpDestinations:0,actualWorkerRetirement:true,workerCount:workers.length,engineBuildsStarted:0,installedChanges:0,publicRedistributionQualified:false},null,2)+'\n',{flag:'wx',mode:0o600});
});
