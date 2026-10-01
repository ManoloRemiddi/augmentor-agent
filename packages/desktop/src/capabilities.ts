// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {componentEnvironment,pythonExecutable} from '../../platform/src/index.js';

export interface LinuxDiscovery {
 schema:1; available:boolean; backend:'kde-wayland-portal'|null; reason:string|null;
 permission:'not-requested'; functionalTested:false;
}
const unavailable:LinuxDiscovery={schema:1,available:false,backend:null,reason:'probe-unavailable',permission:'not-requested',functionalTested:false};
const discovery=fileURLToPath(new URL('../../../services/desktop/capabilities.py',import.meta.url));
let cached:{key:string;expires:number;value:LinuxDiscovery}|undefined;
function linuxDiscovery(env:NodeJS.ProcessEnv):LinuxDiscovery {
 const childEnv={...componentEnvironment(),...env};
 const key=JSON.stringify(['AUGMENTOR_PYTHON','DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','XDG_CURRENT_DESKTOP','XDG_SESSION_TYPE'].map(k=>childEnv[k]));
 if(cached?.key===key&&cached.expires>Date.now())return cached.value;
 let value=unavailable;
 try {
  const result=spawnSync(pythonExecutable(),[discovery],{env:childEnv,encoding:'utf8',timeout:5000,maxBuffer:16384,stdio:['ignore','pipe','ignore']});
  if(result.status===0){
   const observed=JSON.parse(result.stdout);
   if(observed?.schema===1&&typeof observed.available==='boolean'&&['kde-wayland-portal',null].includes(observed.backend)&&
      (observed.reason===null||typeof observed.reason==='string')&&observed.permission==='not-requested'&&observed.functionalTested===false&&
      (!observed.available||(observed.backend==='kde-wayland-portal'&&observed.reason===null)))value=observed;
  }
 }catch{/* Missing runtimes, closed buses and bounded-query failures never grant availability. */}
 cached={key,expires:Date.now()+5000,value};return value;
}

/** Backend availability is separate from the user's live OS permission grant. */
export function desktopCapabilities(platform:NodeJS.Platform=process.platform,env:NodeJS.ProcessEnv=process.env,present:(path:string)=>boolean=existsSync,probe:(env:NodeJS.ProcessEnv)=>LinuxDiscovery=linuxDiscovery){
 const mac=platform==='darwin';
 const helper=env.AUGMENTOR_MACOS_HELPER??fileURLToPath(new URL('../../../native/augmentor-desktop-control',import.meta.url));
 const enabled=env.AUGMENTOR_PI_LINUX_TOOLS!=='0';
 const linux=platform==='linux'&&enabled?probe(env):undefined;
 const available=enabled&&(platform==='linux'?linux?.available===true:mac&&present(helper));
 return {available,preview:true,backend:mac?'macos-screencapturekit':linux?.backend??null,reason:!enabled?'disabled':linux?.reason??(available?null:mac?'helper-unavailable':'unsupported-platform'),permission:'not-requested' as const,functionalTested:false as const,monitors:1,text:mac?'Unicode':'ASCII',requiresImageModel:true,requiresUserConsent:true};
}
