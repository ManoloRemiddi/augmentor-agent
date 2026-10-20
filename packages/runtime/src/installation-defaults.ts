// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {constants,openSync,writeFileSync,fsyncSync,closeSync,lstatSync,realpathSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {blankMetafolders} from '../../protocol/src/metafolders.js';

/** First-install defaults, or an explicit operator upgrade. Never replace a
 * saved choice, provider, secret, library or workspace grouping. */
export function provisionHarnessDefaults(configDir:string){
 if(!['linux','darwin'].includes(process.platform))throw Error('Harness installation defaults currently support Linux and macOS.');
 const info=lstatSync(configDir);
 if(!info.isDirectory()||info.isSymbolicLink()||info.uid!==process.getuid!()||(info.mode&0o077)||realpathSync(configDir)!==resolve(configDir))throw Error('Harness defaults require a private owned configuration directory.');
 const created:string[]=[],preserved:string[]=[];
 const seed=(name:string,value:unknown)=>{
  const file=join(configDir,name);let fd:number;
  try{fd=openSync(file,constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|constants.O_NOFOLLOW,0o600);}
  catch(error){if((error as NodeJS.ErrnoException).code==='EEXIST'){const old=lstatSync(file);if(!old.isFile()||old.isSymbolicLink()||old.nlink!==1||old.uid!==process.getuid!()||(old.mode&0o077))throw Error('An existing Harness default is unsafe; its original was preserved.');preserved.push(name);return;}throw error;}
  try{writeFileSync(fd,JSON.stringify(value,null,2)+'\n');fsyncSync(fd);}finally{closeSync(fd);}created.push(name);
 };
 seed('harness-metafolders.json',{schema:'augmentor-harness-metafolders/1',revision:1,value:{...blankMetafolders(),enabled:true}});
 seed('free-search.json',{schema:'augmentor-free-search/1',enabled:true,mode:'keyless',keyless:{},config:{}});
 const fd=openSync(configDir,constants.O_RDONLY|constants.O_DIRECTORY|constants.O_NOFOLLOW);try{fsyncSync(fd);}finally{closeSync(fd);}
 return {created,preserved,builtIn:['metafolders','prompt-library','prompt-improvement','model-picker','context-insights','adaptive-reasoning','web-search','web-fetch'],privateModels:'operator-configured; never bundled',personalPrompts:'preserved; never bundled'};
}
