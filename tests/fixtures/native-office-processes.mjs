// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readFile,readdir} from 'node:fs/promises';
/** Inspect only descendants of the calling authored fixture. Identity tokens
 * protect cleanup signals against PID reuse; no process environment is read. */
export async function processIdentity(pid){
 try{const value=await readFile('/proc/'+pid+'/stat','utf8'),fields=value.slice(value.lastIndexOf(')')+2).split(' ');return {pid,group:Number(fields[2]),start:fields[19],state:fields[0],name:await readFile('/proc/'+pid+'/comm','utf8').then(v=>v.trim())};}catch(error){if(error.code==='ENOENT'||error.code==='ESRCH')return;throw error;}
}
export async function ownedProcesses(parent=process.pid){
 const pending=[parent],found=new Map();while(pending.length){const pid=pending.pop();let threads;try{threads=await readdir('/proc/'+pid+'/task');}catch(error){if(error.code==='ENOENT')continue;throw error;}for(const thread of threads){let children;try{children=await readFile('/proc/'+pid+'/task/'+thread+'/children','utf8');}catch(error){if(error.code==='ENOENT')continue;throw error;}for(const child of children.trim().split(/\s+/).filter(Boolean).map(Number))if(!found.has(child)){const identity=await processIdentity(child);if(identity){found.set(child,identity);pending.push(child);}}}}return [...found.values()];
}
export async function signalOwned(identity,signal){const current=await processIdentity(identity.pid);if(current?.start===identity.start){try{process.kill(identity.pid,signal);}catch(error){if(error.code!=='ESRCH')throw error;}}}
export async function stillOwned(identity){const current=await processIdentity(identity.pid);return current?.start===identity.start;}
