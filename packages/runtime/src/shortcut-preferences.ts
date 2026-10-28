// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Private storage seat for the copied DSH pure preference coordinator.
 * One document spans browser device profiles; no session, tool or native bridge. */
export class ShortcutPreferences {
  private supplier=import(new URL('../vendor/dsh-shortcuts.js',import.meta.url).href);
  private seats=new Map<string,{persistence:any;definitions:string}>();
  constructor(private read:()=>string|null,private write:(raw:string)=>void){}
  private platform(value:unknown):string {
    if(!['linux','macos','windows'].includes(value as string))throw Error('Choose a supported browser device profile.');
    return value as string;
  }
  async describe(platform:unknown,definitions:unknown){
    const key=this.platform(platform),p=await this.supplier;
    if(!Array.isArray(definitions)||definitions.length>128||Buffer.byteLength(JSON.stringify(definitions))>64*1024)throw Error('Shortcut catalogue exceeds its limit.');
    const accepted=p.parseShortcutDefinitions(definitions),signature=JSON.stringify(accepted);
    let seat=this.seats.get(key);
    if(!seat){seat={persistence:new p.ShortcutPersistence({read:()=>{const raw=this.read();if(raw!==null&&Buffer.byteLength(raw)>64*1024)throw Error('Shortcut preferences exceed their limit.');return raw;},write:(raw:string)=>{if(Buffer.byteLength(raw)>64*1024)throw Error('Shortcut preferences exceed their limit.');this.write(raw);}},'web',key,true,()=>{}),definitions:''};this.seats.set(key,seat);}
    if(seat.definitions!==signature){seat.persistence.setDefinitions(accepted);seat.definitions=signature;}
    return seat.persistence.readCurrent();
  }
  async edit(platform:unknown,edit:unknown,revision:unknown){
    const key=this.platform(platform),p=await this.supplier,seat=this.seats.get(key);
    if(!seat||typeof revision!=='string'||revision.length>64)throw Error('Read the current shortcut catalogue before editing.');
    return seat.persistence.edit(p.parseShortcutEdit(edit),revision);
  }
}
