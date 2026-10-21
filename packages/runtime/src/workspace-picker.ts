// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {opendir,stat,mkdir} from 'node:fs/promises';
import {homedir} from 'node:os';
import {basename,dirname,isAbsolute,join,resolve} from 'node:path';
import {text} from '../../protocol/src/index.js';
const pathOf=(value:unknown)=>{const path=value===undefined?homedir():text(value,4096);if(!isAbsolute(path)||path.includes('\0'))throw Error('Choose an absolute folder path.');return resolve(path);};
/** Explicit operator folder picker, never called by a model or a read-only inspector. */
export async function listWorkspaceDirectory(value:unknown){
  const path=pathOf(value),crumbs=[];let current=path;
  for(;;){crumbs.unshift({name:basename(current)||current,path:current,hidden:false});const parent=dirname(current);if(parent===current)break;current=parent;}
  const entries=[];let count=0;
  for await(const entry of await opendir(path)){
    if(++count>20000)throw Error('This folder is too large to browse. Enter a more specific path.');
    const child=join(path,entry.name);
    if(entry.isDirectory()||entry.isSymbolicLink()&&await stat(child).then(s=>s.isDirectory(),()=>false))entries.push({name:entry.name,path:child,hidden:entry.name.startsWith('.')});
  }
  entries.sort((a,b)=>a.name.localeCompare(b.name));return {path,home:homedir(),crumbs,entries:entries.slice(0,2000),truncated:entries.length>2000};
}
export async function createWorkspaceDirectory(value:unknown,name:unknown){
  const parent=pathOf(value),child=text(name,255);
  if(child==='.'||child==='..'||child!==basename(child)||/[\\/\0]/.test(child))throw Error('Supply one folder name.');
  if(!(await stat(parent)).isDirectory())throw Error('The parent must be an existing folder.');
  const target=join(parent,child);await mkdir(target);return {path:target};
}
