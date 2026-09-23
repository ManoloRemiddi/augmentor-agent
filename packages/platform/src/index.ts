// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Shared executable and environment discovery, including externally launched DSH. */
import {existsSync,lstatSync,mkdirSync} from 'node:fs';
import {homedir,userInfo} from 'node:os';
import {dirname,join,delimiter} from 'node:path';
import {fileURLToPath} from 'node:url';

const root=fileURLToPath(new URL('../../../',import.meta.url));
export function pythonExecutable(){
  if(process.env.AUGMENTOR_PYTHON)return process.env.AUGMENTOR_PYTHON;
  const bundled=join(root,'python/bin/python3');
  return existsSync(bundled)?bundled:process.platform==='linux'?'/usr/bin/python3':'python3';
}
export function componentEnvironment():NodeJS.ProcessEnv {
  const env:NodeJS.ProcessEnv={...process.env,AUGMENTOR_PYTHON:pythonExecutable(),PYTHONDONTWRITEBYTECODE:'1'};
  const node=join(root,'node/bin/node');
  if(existsSync(node))env.AUGMENTOR_PI_NODE??=node;
  env.PATH=[...(existsSync(node)?[dirname(node)]:[]),dirname(pythonExecutable()),env.PATH??''].join(delimiter);
  if(process.platform==='darwin'){
    const base=join(homedir(),'Library/Application Support/Augmentor');
    env.XDG_CONFIG_HOME??=join(base,'config');env.XDG_DATA_HOME??=join(base,'data');env.XDG_STATE_HOME??=join(base,'state');
    env.XDG_RUNTIME_DIR??='/tmp/augmentor-'+userInfo().uid;
    mkdirSync(env.XDG_RUNTIME_DIR,{recursive:true,mode:0o700});
    const info=lstatSync(env.XDG_RUNTIME_DIR);
    if(!info.isDirectory()||info.uid!==userInfo().uid||(info.mode&0o077))throw new Error('Augmentor needs a private runtime directory owned by this user.');
    env.AUGMENTOR_PI_SOCKET??=join(env.XDG_RUNTIME_DIR,'pi.sock');
    env.AUGMENTOR_SHARED_STATE??=join(env.XDG_RUNTIME_DIR,'shared');
  }
  return env;
}
