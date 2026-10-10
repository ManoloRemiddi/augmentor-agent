// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readFile} from 'node:fs/promises';
import {join} from 'node:path';
/** File creation alone can expose an empty/partial record. Require the actual
 * browser endpoint and page response inside each caller's existing deadline.
 */
export async function chromiumPort(profile){
 const [port,browser]=(await readFile(join(profile,'DevToolsActivePort'),'utf8')).trim().split('\n');
 if(!/^[1-9]\d{0,4}$/.test(port??'')||Number(port)>65535||!/^\/devtools\/browser\/[a-zA-Z0-9-]+$/.test(browser??''))return;
 const response=await fetch('http://127.0.0.1:'+port+'/json');if(!response.ok)return;
 const targets=await response.json();
 if(Array.isArray(targets)&&targets.some(target=>target.type==='page'&&typeof target.webSocketDebuggerUrl==='string'))return port;
}
