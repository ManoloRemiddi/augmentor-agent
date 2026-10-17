// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {resolve,join,basename} from 'node:path';
import {fileURLToPath} from 'node:url';
import {OfficeToPdfError} from '../vendor/dsh-office/errors.js';
const run=promisify(execFile),helper=fileURLToPath(new URL('./office-scratch-journal.py',import.meta.url));
export interface LinuxOfficeScratchState {readonly stateDirectory:string;readonly parent:string;}
async function journal(stateDirectory:string,selection:string[]=[]){
 try{
  const {stdout}=await run('/usr/bin/python3',['-I','-B',helper,String(process.pid),stateDirectory,...selection],{timeout:10000,maxBuffer:16384,env:{PATH:'/usr/bin:/bin',LANG:'C.UTF-8',LC_ALL:'C.UTF-8'}});
  const result=JSON.parse(stdout),parent=join(stateDirectory,'office-scratch','v1','data');
  if(result.parent!==parent||!Number.isSafeInteger(result.recovered)||result.recovered<0||result.recovered>128)throw Error('Invalid Office recovery receipt.');
  return {stateDirectory,parent};
 }catch{throw new OfficeToPdfError('unavailable','Office preview cleanup could not verify its private recovery state. Preserved files require inspection.');}
}
export async function prepareLinuxOfficeScratchState(stateDirectory:string):Promise<LinuxOfficeScratchState>{
 if(typeof stateDirectory!=='string'||!stateDirectory||resolve(stateDirectory)!==stateDirectory)throw new OfficeToPdfError('unavailable','Office preview recovery requires its private application state.');
 return journal(stateDirectory);
}
export async function cleanupLinuxOfficeScratchState(state:LinuxOfficeScratchState,directory:string,identity:{dev:bigint;ino:bigint}){
 if(join(state.parent,basename(directory))!==directory||!/^dsh-office-to-pdf-[a-f0-9]{24}$/.test(basename(directory)))throw new OfficeToPdfError('unavailable','Office scratch cleanup identity changed.');
 await journal(state.stateDirectory,[basename(directory),String(identity.dev),String(identity.ino)]);
}
