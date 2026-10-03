// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {mkdirSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

export function privateDirectory(path) {
  if(process.platform!=='win32'){mkdirSync(path,{recursive:true,mode:0o700});return;}
  if(!process.env.AUGMENTOR_PYTHON)throw Error('Launch workspace administration through the verified product Python adapter');
  const script=fileURLToPath(new URL('../../scripts/app-sdk-private.py',import.meta.url));
  const result=spawnSync(process.env.AUGMENTOR_PYTHON,[script,'directory',path],
    {encoding:'utf8',windowsHide:true,timeout:15000,stdio:['ignore','pipe','pipe']});
  if(result.error||result.status!==0)throw Error('The workspace directory does not have verified owner-only access');
}
