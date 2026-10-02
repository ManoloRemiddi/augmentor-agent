// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Read-only runtime selection. Full import/file verification happens at preparation and cold launch. */
import {createHash} from 'node:crypto';
import {lstatSync,readFileSync,realpathSync} from 'node:fs';
import {homedir,userInfo} from 'node:os';
import {dirname,isAbsolute,join,resolve,basename} from 'node:path';

type Wheel={name:string,version:string,file:string,sha256:string,bytes:number,source?:string,url?:string};
type Policy={format:string,profile:string,target:string,python:string,pythonAbi:number[],architecture:string,systemSitePackages:boolean,wheels:Wheel[],sourceQt?:Record<string,unknown>,systemQtStack?:Record<string,unknown>,qualified?:boolean,licenseReviewComplete?:boolean,embeddedSourceCoverageComplete?:boolean};
const SOURCE_PROFILE='noble-cp312-x86_64-source-qt-voice';
const SOURCE_QT={format:'augmentor-source-qt-runtime-input/1',directory:'source-qt',qtVersion:'6.8.2',
  manifestSha256:'c49faf50a992daca825c51929715c6114017e6b29ac54af17f9656db41e73364',
  derivationReceipt:{file:'source-pyside-derivation.json',sha256:'de6edc207b0ce7279de6972b5694d3063161f4fd9c46b865245ca0c471d2990c',bytes:1063}};
const SOURCE_WHEELS:Record<string,[string,string,number]>={
  pyside6:['PySide6-6.8.2.1-6.8.2augmentor2-cp37-abi3-manylinux_2_39_x86_64.whl','5cb05190ddf1db3e2915662b8c744f56922f40bd03b84683b6651742cfb1c951',10312884],
  shiboken6:['shiboken6-6.8.2.1-6.8.2-cp37-abi3-manylinux_2_39_x86_64.whl','a908c5696e620b4390ecd12267d28dbe6f759547df84fffd3745e85e59492c92',205749]};
const normalized=(name:string)=>name.toLowerCase().replace(/[-_.]+/g,'-');
// Match Python's sort_keys=True, default separators and ensure_ascii=True.
export function pythonJson(value:unknown):string {
  if(Array.isArray(value))return '['+value.map(pythonJson).join(', ')+']';
  if(value!==null&&typeof value==='object')return '{'+Object.entries(value).sort(([a],[b])=>a<b?-1:a>b?1:0).map(([key,val])=>pythonJson(key)+': '+pythonJson(val)).join(', ')+'}';
  return JSON.stringify(value).replace(/[\u007f-\uffff]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'));
}
const sha=(value:string|Buffer)=>createHash('sha256').update(value).digest('hex');
export function pythonRuntimeIdentity(value:Policy):string {
  const contract:Record<string,unknown>={};
  for(const key of ['profile','target','python','pythonAbi','architecture','systemSitePackages'] as const)contract[key]=value[key];
  contract.wheels=[...value.wheels].sort((a,b)=>normalized(a.name).localeCompare(normalized(b.name))).map(row=>({name:row.name,version:row.version,file:row.file,sha256:row.sha256,bytes:row.bytes}));
  if(value.profile===SOURCE_PROFILE)contract.sourceQt=value.sourceQt;
  if(value.systemQtStack!==undefined)contract.systemQtStack=value.systemQtStack;
  return sha(pythonJson(contract));
}
export function declaredLinuxPython(app:string,env:NodeJS.ProcessEnv=process.env):string|undefined {
  if(process.platform!=='linux')return undefined;
  const marker=join(resolve(app),'linux-python-runtime.json');
  let markerInfo;
  try{markerInfo=lstatSync(marker);}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return undefined;throw error;}
  if(!markerInfo.isFile())throw Error('Linux Python policy must be a regular artifact file.');
  const value=JSON.parse(readFileSync(marker,'utf8')) as Policy;
  const names=['pyside6-essentials','shiboken6','pygments','keyring','sounddevice'];
  if(value.profile==='noble-cp312-x86_64-voice')names.push('onnxruntime','protobuf');
  else if(value.profile===SOURCE_PROFILE){
    names[0]='pyside6';names.push('onnxruntime','protobuf');
    if(pythonJson(value.sourceQt)!==pythonJson(SOURCE_QT)||value.qualified!==false||value.licenseReviewComplete!==false||value.embeddedSourceCoverageComplete!==false)throw Error('Source Qt requires its exact unqualified native payload contract.');
    for(const row of value.wheels){
      const source=SOURCE_WHEELS[normalized(row.name)];
      if(source&&(pythonJson([row.file,row.sha256,row.bytes])!==pythonJson(source)||row.version!=='6.8.2.1'||row.source!=='reviewed-offline'||row.url!==undefined))throw Error('Source bindings require their exact reviewed offline wheel identities.');
      if(!source&&(!row.url?.startsWith('https://files.pythonhosted.org/packages/')||row.source!==undefined))throw Error('Invalid locked wheel record.');
    }
  }
  else if(value.profile!=='noble-cp312-x86_64')throw Error('Unsupported Linux Python runtime policy.');
  if(value.systemQtStack!==undefined)throw Error('This profile cannot declare a distro Qt stack.');
  if(value.profile!==SOURCE_PROFILE&&value.sourceQt!==undefined)throw Error('A vendor profile cannot declare source Qt.');
  if(value.format!=='augmentor-linux-python-wheels/1'||value.target!=='ubuntu24.04-amd64'||value.python!=='/usr/bin/python3.12'||pythonJson(value.pythonAbi)!=='[3, 12]'||value.architecture!=='x86_64'||process.arch!=='x64'||value.systemSitePackages!==true||!Array.isArray(value.wheels)||value.wheels.length!==names.length||names.some(name=>value.wheels.filter(row=>normalized(row.name)===name).length!==1))throw Error('Unsupported Linux Python runtime policy.');
  for(const row of value.wheels)if(basename(row.file)!==row.file||!row.file.endsWith('.whl')||!/^\w[\w.+-]*$/.test(row.version)||!/^[a-f0-9]{64}$/.test(row.sha256)||!Number.isSafeInteger(row.bytes)||row.bytes<=0)throw Error('Invalid locked wheel record.');
  const release=readFileSync('/etc/os-release','utf8');
  const field=(name:string)=>release.split('\n').find(line=>line.startsWith(name+'='))?.slice(name.length+1).replace(/^"|"$/g,'');
  if(field('ID')!=='ubuntu'||field('VERSION_ID')!=='24.04')throw Error('This runtime policy requires Ubuntu 24.04.');
  const data=env.XDG_DATA_HOME??join(env.HOME??homedir(),'.local/share');
  if(!isAbsolute(data))throw Error('XDG_DATA_HOME must be an absolute path.');
  const identity=pythonRuntimeIdentity(value),name=value.profile+'-'+identity.slice(0,16);
  const python=env.AUGMENTOR_PYTHON??join(data,'augmentor/python-runtimes',name,'bin/python3');
  const root=dirname(dirname(python));
  if(!isAbsolute(python)||basename(root)!==name||python!==join(root,'bin/python3'))throw Error('The selected Python does not match this artifact runtime policy.');
  const uid=userInfo().uid,info=lstatSync(root),receiptPath=join(root,'augmentor-python-runtime.json'),receiptInfo=lstatSync(receiptPath);
  if(!info.isDirectory()||info.uid!==uid||(info.mode&0o077)||!receiptInfo.isFile()||receiptInfo.uid!==uid||receiptInfo.nlink!==1)throw Error('Runtime directory/receipt identity is invalid.');
  const receipt=JSON.parse(readFileSync(receiptPath,'utf8'));
  if(receipt.format!=='augmentor-linux-python-runtime/1'||receipt.lockIdentity!==identity||receipt.root!==root||receipt.python!==python||receipt.target!==value.target||receipt.profile!==value.profile||pythonJson(receipt.wheels)!==pythonJson(value.wheels)||!receipt.files||receipt.artifactSha256!==sha(pythonJson(receipt.files)))throw Error('Runtime receipt differs from its path or wheel contract.');
  if(value.profile===SOURCE_PROFILE){
    const manifest=join(root,'qt/stage-inventory.json');
    if(pythonJson(receipt.sourceQt)!==pythonJson(SOURCE_QT)||!lstatSync(manifest).isFile()||sha(readFileSync(manifest))!==SOURCE_QT.manifestSha256||receipt.files['qt/stage-inventory.json']!==SOURCE_QT.manifestSha256)throw Error('Source Qt native manifest changed; prepare a new runtime.');
    const paths={LD_LIBRARY_PATH:'lib',QT_PLUGIN_PATH:'plugins',QT_QPA_PLATFORM_PLUGIN_PATH:'plugins/platforms',QML_IMPORT_PATH:'qml',QML2_IMPORT_PATH:'qml'};
    if(env.LD_PRELOAD||env.LD_AUDIT||Object.entries(paths).some(([name,path])=>env[name]!==join(root,'qt',path)))throw Error('Source Qt needs its verified native environment before Node starts.');
  }
  for(const file of ['pyvenv.cfg','wheel-lock.txt']){
    const path=join(root,file);
    if(!lstatSync(path).isFile()||sha(readFileSync(path))!==receipt.files[file])throw Error('Managed runtime configuration changed; prepare a new runtime.');
  }
  if(realpathSync(python)!==realpathSync(value.python))throw Error('Managed runtime interpreter differs from its system ABI.');
  return python;
}
