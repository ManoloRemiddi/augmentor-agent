// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomBytes} from 'node:crypto';
import {lstat} from 'node:fs/promises';

/** Explicit MX candidate only. No system service, privilege escalation or fallback. */
export async function officeProcessScope(timeoutMs:number){
 if(process.platform!=='linux'||!Number.isSafeInteger(timeoutMs)||timeoutMs<1||timeoutMs>60000)throw Error('Office managed scope is unavailable.');
 const uid=process.getuid!(),runtime='/run/user/'+uid;
 const directory=await lstat(runtime),bus=await lstat(runtime+'/bus');
 if(!directory.isDirectory()||directory.uid!==uid||(directory.mode&0o777)!==0o700||!bus.isSocket()||bus.uid!==uid)throw Error('Office user manager is unavailable.');
 const unit='augmentor-office-'+randomBytes(16).toString('hex')+'.scope';
 return {executable:'/usr/bin/systemd-run',unit,env:{XDG_RUNTIME_DIR:runtime,DBUS_SESSION_BUS_ADDRESS:'unix:path='+runtime+'/bus'},args:[
  '--user','--scope','--quiet','--collect','--no-ask-password','--expand-environment=no','--unit='+unit,
  '--property=MemoryMax=3221225472','--property=MemorySwapMax=0','--property=OOMPolicy=kill',
  '--property=TasksMax=128','--property=CPUQuota=100%',
  '--property=RuntimeMaxSec='+String(timeoutMs+2000)+'ms','--property=TimeoutStopSec=2s',
  '--property=KillMode=control-group','--property=SendSIGKILL=yes',
 ]};
}
