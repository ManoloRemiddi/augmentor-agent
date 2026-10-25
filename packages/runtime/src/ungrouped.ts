// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {mkdirSync,lstatSync,realpathSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {identifier} from '../../protocol/src/index.js';
import {privateDir} from './storage.js';

/** A fresh SDK session and a private working directory per quick chat. This is
 * organisation/context separation, not an OS sandbox or a new memory store. */
export function ungroupedDirectory(state: string, sessionId: unknown): string {
  const id=identifier(sessionId), root=resolve(state,'ungrouped');
  for(const directory of [root,join(root,id)]){
    if(process.platform==='win32')privateDir(directory);else mkdirSync(directory,{recursive:true,mode:0o700});
    const info=lstatSync(directory);
    if(!info.isDirectory()||info.isSymbolicLink()||realpathSync(directory)!==directory||process.getuid&&info.uid!==process.getuid()||(process.platform!=='win32'&&(info.mode&0o077)))throw Error('Ungrouped chats require private owned working directories.');
  }
  return join(root,id);
}
