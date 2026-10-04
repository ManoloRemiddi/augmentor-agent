// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Cold Python verifies every byte and versions; Node refuses a stale selection before child exec. */
import {createHash} from 'node:crypto';
import {closeSync,fstatSync,lstatSync,openSync,readSync,constants,type Stats} from 'node:fs';
import {homedir,userInfo} from 'node:os';
import {dirname,isAbsolute,join,resolve} from 'node:path';

const sha=(raw:string|Buffer)=>createHash('sha256').update(raw).digest('hex');
const identity=(s:Stats)=>[s.dev,s.ino,s.mode,s.uid,s.gid,s.nlink,s.size,s.mtimeMs,s.ctimeMs].join(':');
function privateDirectory(path:string){
  if(!isAbsolute(path)||resolve(path)!==path)throw Error('Recipient path must be absolute and normalized.');
  const info=lstatSync(path);
  if(!info.isDirectory()||info.uid!==userInfo().uid||(info.mode&0o077))throw Error('Recipient directory must be private and user-owned.');
  for(let parent=dirname(path);;parent=dirname(parent)){
    if(lstatSync(parent).isSymbolicLink())throw Error('Recipient ancestors cannot be symlinks.');
    if(parent===dirname(parent))break;
  }
}
function read(path:string,privateFile=true):Buffer {
  const fd=openSync(path,constants.O_RDONLY|constants.O_NOFOLLOW|constants.O_NONBLOCK);
  try{
    const before=fstatSync(fd);
    if(!before.isFile()||before.nlink!==1||before.size>8*1024*1024||(before.mode&0o022)||privateFile&&(before.uid!==userInfo().uid||(before.mode&0o077)))throw Error('Invalid recipient file identity.');
    const raw=Buffer.alloc(before.size);let count=0;
    while(count<raw.length){const n=readSync(fd,raw,count,raw.length-count,null);if(!n)break;count+=n;}
    if(count!==raw.length||identity(before)!==identity(fstatSync(fd))||identity(before)!==identity(lstatSync(path)))throw Error('Recipient file changed during validation.');
    return raw;
  }finally{closeSync(fd);}
}
export function recipientSelectionPath(app:string,env:NodeJS.ProcessEnv){
  const data=env.XDG_DATA_HOME??join(env.HOME??homedir(),'.local/share');
  if(!isAbsolute(data))throw Error('XDG_DATA_HOME must be absolute.');
  return join(data,'augmentor/recipient-runtimes','selection-'+sha(resolve(app))+'.json');
}
export function selectedRecipientPython(app:string,env:NodeJS.ProcessEnv,official:(env:NodeJS.ProcessEnv)=>string|undefined):string|undefined {
  // No valid explicit choice can be created under a relative data home. Preserve
  // the legacy non-declared-runtime fallback; declared policies still reject it.
  if(env.XDG_DATA_HOME&&!isAbsolute(env.XDG_DATA_HOME)&&!env.AUGMENTOR_RECIPIENT_RECEIPT)return undefined;
  const selectionPath=recipientSelectionPath(app,env);
  try{lstatSync(selectionPath);}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT'){
    if(env.AUGMENTOR_RECIPIENT_RECEIPT)throw Error('Recipient environment has no explicit selection.');
    return undefined;
  }throw error;}
  privateDirectory(dirname(selectionPath));
  const selectionRaw=read(selectionPath),selection=JSON.parse(selectionRaw.toString());
  if(Object.keys(selection).sort().join(',')!=='app,format,officialPython,receipt,receiptSha256'||selection.format!=='augmentor-recipient-runtime-selection/1')throw Error('Malformed recipient selection.');
  const appIdentity={root:resolve(app),releaseSha256:sha(read(join(app,'release.json'),false)),policySha256:sha(read(join(app,'linux-python-runtime.json'),false))};
  if(JSON.stringify(selection.app)!==JSON.stringify(appIdentity))throw Error('Recipient selection belongs to a stale application.');
  const receiptPath=selection.receipt;
  if(typeof receiptPath!=='string'||receiptPath!==join(dirname(receiptPath),'augmentor-recipient-runtime.json'))throw Error('Invalid recipient receipt path.');
  const root=dirname(receiptPath);privateDirectory(root);
  const raw=read(receiptPath),receipt=JSON.parse(raw.toString()),digest=sha(raw);
  if(digest!==selection.receiptSha256||env.AUGMENTOR_RECIPIENT_RECEIPT!==receiptPath||env.AUGMENTOR_RECIPIENT_RECEIPT_SHA256!==digest||env.AUGMENTOR_RECIPIENT_SELECTION_SHA256!==sha(selectionRaw)||env.AUGMENTOR_OFFICIAL_PYTHON!==selection.officialPython)throw Error('Recipient needs its verified selection/environment before Node starts.');
  const value=JSON.parse(read(join(app,'linux-python-runtime.json'),false).toString());
  if(!['noble-cp312-x86_64-source-qt-voice','mint223-cp312-x86_64-source-qt-voice'].includes(value.profile))throw Error('Recipient requires the existing source Qt profile.');
  const base=dirname(dirname(selection.officialPython));
  const baseEnv:NodeJS.ProcessEnv={...env,AUGMENTOR_PYTHON:selection.officialPython};
  for(const [key,path] of Object.entries({LD_LIBRARY_PATH:'lib',QT_PLUGIN_PATH:'plugins',QT_QPA_PLATFORM_PLUGIN_PATH:'plugins/platforms',QML_IMPORT_PATH:'qml',QML2_IMPORT_PATH:'qml'}))baseEnv[key]=join(base,'qt',path);
  if(official(baseEnv)!==selection.officialPython)throw Error('Recipient official base differs from the current contract.');
  const officialRaw=read(join(base,'augmentor-python-runtime.json'),false),officialReceipt=JSON.parse(officialRaw.toString());
  const expectedAbi={pythonAbi:value.pythonAbi,qtVersion:value.sourceQt.qtVersion,pysideVersion:'6.8.2.1',shibokenVersion:'6.8.2.1'};
  if(Object.keys(receipt).sort().join(',')!=='abi,app,files,format,officialLockIdentity,officialPython,officialReceiptSha256,python,root'||receipt.format!=='augmentor-recipient-runtime/1'||JSON.stringify(receipt.app)!==JSON.stringify(appIdentity)||receipt.officialPython!==selection.officialPython||receipt.officialReceiptSha256!==sha(officialRaw)||receipt.officialLockIdentity!==officialReceipt.lockIdentity||receipt.root!==root||receipt.python!==join(root,'bin/python3')||JSON.stringify(receipt.abi)!==JSON.stringify(expectedAbi))throw Error('Recipient receipt differs from its app, official base or ABI.');
  const files=receipt.files as Record<string,string>,baseFiles=officialReceipt.files as Record<string,string>;
  if(!files||Object.keys(files).sort().join('\n')!==Object.keys(baseFiles).sort().join('\n'))throw Error('Recipient file set differs from the official base.');
  const prefix='lib/python'+value.pythonAbi.join('.')+'/site-packages/';
  for(const [name,original] of Object.entries(baseFiles)){
    const row=files[name],first=name.startsWith(prefix)?name.slice(prefix.length).split('/')[0]:'';
    const permitted=name.startsWith('qt/')||['PySide6','shiboken6','PySide6-6.8.2.1.dist-info','shiboken6-6.8.2.1.dist-info'].includes(first);
    if(typeof row!=='string'||row!==original&&(!permitted||row.startsWith('link:')||original.startsWith('link:')))throw Error('Recipient changed a non-Qt file or link.');
  }
  for(const name of ['pyvenv.cfg','wheel-lock.txt','qt/stage-inventory.json'])if(sha(read(join(root,name),false))!==files[name])throw Error('Recipient configuration changed.');
  if(env.AUGMENTOR_PYTHON!==receipt.python||env.LD_PRELOAD||env.LD_AUDIT||Object.entries({LD_LIBRARY_PATH:'lib',QT_PLUGIN_PATH:'plugins',QT_QPA_PLATFORM_PLUGIN_PATH:'plugins/platforms',QML_IMPORT_PATH:'qml',QML2_IMPORT_PATH:'qml'}).some(([key,path])=>env[key]!==join(root,'qt',path)))throw Error('Recipient executable/native environment changed.');
  if(sha(read(selectionPath))!==sha(selectionRaw)||sha(read(receiptPath))!==digest)throw Error('Recipient selection changed during validation.');
  return receipt.python;
}
