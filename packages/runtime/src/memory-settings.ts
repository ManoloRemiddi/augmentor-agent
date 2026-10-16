// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {promptCall} from '../../prompt-library/src/client.js';

const PROTOCOL='augmentor-memory-settings/1';
const count=(value:unknown)=>typeof value==='number'&&Number.isSafeInteger(value)&&value>=0;
/** Operator metadata/control only: never forward identities, configuration or activity leases. */
export class MemorySettings {
  constructor(readonly call:typeof promptCall=promptCall){}
  async describe(){
    try{
      const row=await this.call('memory.dual.describe',{},undefined,AbortSignal.timeout(5000));
      if(row?.protocol!=='augmentor-dual-memory/1'||(typeof row.enabled!=='number'&&typeof row.enabled!=='boolean')||!count(row.events)||!count(row.pending)||!count(row.failures))throw Error('Invalid memory status');
      if(typeof row.enabled==='number'&&row.enabled!==0&&row.enabled!==1)throw Error('Invalid capture state');
      const processingKnown=typeof row.processing?.paused==='boolean'&&typeof row.processing?.active==='boolean';
      const configured=row.configured===true;
      const gatewayBlocked=row.processingIssue==='gateway-in-use';
      return {protocol:PROTOCOL,connected:true as const,enabled:!!row.enabled,configured,available:!gatewayBlocked&&row.available===true,
        requestMode:configured?(['default','off'].includes(row.requestMode)?row.requestMode:'unknown'):'unconfigured',
        requestModeSource:'configured-memory-engine',events:row.events,pending:row.pending,stopped:row.failures,
        actions:{capture:row.configurationGuards?.capture===1,processing:!gatewayBlocked&&processingKnown&&row.configurationGuards?.processing===1},
        processing:{known:processingKnown,paused:processingKnown?row.processing.paused:null,active:processingKnown?row.processing.active:null,
          ...(gatewayBlocked?{issue:'gateway-in-use' as const}:{})}};
    }catch{return {protocol:PROTOCOL,connected:false as const,message:'Memory status is unavailable. Refresh to check it again.'};}
  }
  async configure(value:unknown,expected:unknown){
    if(typeof value!=='boolean'||typeof expected!=='boolean')throw Error('Choose a confirmed memory capture state.');
    const before=await this.describe();
    if(!before.connected||!('actions' in before)||!before.actions.capture||before.enabled!==expected)throw Error('Memory capture state changed or cannot be confirmed. Refresh before choosing again.');
    try{await this.call('memory.dual.configure',{enabled:value,expectedEnabled:expected},undefined,AbortSignal.timeout(5000));}
    catch{throw Error('The memory change could not be confirmed. Refresh its status before choosing again. Nothing was retried.');}
    const row=await this.describe();
    if(!row.connected||!('enabled' in row)||row.enabled!==value)throw Error('The memory change could not be confirmed. Refresh its status before choosing again. Nothing was retried.');
    return row;
  }
  async processing(value:unknown,expected:unknown){
    if(typeof value!=='boolean'||typeof expected!=='boolean')throw Error('Choose a confirmed memory processing state.');
    const before=await this.describe();
    if(!before.connected||!('actions' in before)||!before.actions.processing||before.processing.paused!==expected)throw Error('Memory processing state changed or cannot be confirmed. Refresh before choosing again.');
    try{await this.call('memory.dual.processing',{paused:value,expectedPaused:expected},undefined,AbortSignal.timeout(5000));}
    catch{throw Error('The memory processing change could not be confirmed. Refresh its status before choosing again. Nothing was retried.');}
    const row=await this.describe();
    if(!row.connected||!('processing' in row)||!row.processing.known||row.processing.paused!==value)throw Error('The memory processing change could not be confirmed. Refresh its status before choosing again. Nothing was retried.');
    return row;
  }
}
