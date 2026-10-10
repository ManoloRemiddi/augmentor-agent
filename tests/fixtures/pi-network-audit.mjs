// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Synthetic qualification only. Observe/block TCP before any runtime imports.
import net from 'node:net';
import {appendFileSync} from 'node:fs';
const file=process.env.AUGMENTOR_PI_TEST_NETWORK_LOG;
if(!file)throw Error('Network proof requires an isolated log');
const original=net.Socket.prototype.connect;
net.Socket.prototype.connect=function(...args){
  const first=Array.isArray(args[0])?args[0][0]:args[0];
  let host,port;
  if(first&&typeof first==='object'&&!first.path){host=first.host||'localhost';port=first.port;}
  else if(typeof first==='number'){host=typeof args[1]==='string'?args[1]:'localhost';port=first;}
  if(port!==undefined){
    const allowed=['localhost','127.0.0.1','::1'].includes(host);
    appendFileSync(file,JSON.stringify({host,port:Number(port),allowed})+'\n',{mode:0o600});
    if(!allowed)throw Error('Unrequested external network connection in the isolated Pi contract: '+host);
  }
  return original.apply(this,args);
};
