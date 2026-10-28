// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Draft-only operation over the existing Pi owner and shared instruction store.
export class DshPromptImprovement {
  constructor(deps){this.deps=deps;this.active=null;this.undo=null;this.listeners=new Set();this.value={busy:false,canUndo:false,note:''};}
  subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};
  getSnapshot=()=>this.value;
  publish(note=''){this.value={busy:!!this.active,canUndo:!!this.undo,note};for(const fn of this.listeners)fn();}
  matches(value){const now=this.deps.read();return now.scope===value.scope&&now.revision===value.revision&&now.text===value.text;}
  sync(){if(this.active&&!this.matches(this.active))this.cancel();if(this.undo&&!this.matches(this.undo)){this.undo=null;this.publish();}}
  cancel(){const job=this.active;if(!job)return;this.active=null;job.animation?.stop();this.publish('Prompt improvement cancelled.');void this.deps.rpc('prompt.cancelImprovement',{requestId:job.id,scopeId:job.id}).catch(()=>{});}
  async run(){
    this.sync();if(this.active){this.cancel();return;}
    if(this.undo){const original=this.undo.original;this.undo=null;this.deps.replace(original);this.publish('Original wording restored.');this.deps.focus();return;}
    const current=this.deps.read();if(!current.available||!current.text.trim()||current.text.length>6000||current.references)return;
    const job={...current,id:crypto.randomUUID(),animation:null};this.active=job;this.undo=null;this.publish('Improving prompt…');
    try{
      job.animation=this.deps.animate(job.text);
      const instructions=(await this.deps.rpc('prompts.list')).improvement;
      if(this.active!==job||!this.matches(job))return;
      const result=await this.deps.rpc('prompt.improve',{sessionId:job.sessionId,selection:job.selection,text:job.text,requestId:job.id,scopeId:job.id,expectedInstructionsRevision:instructions.revision});
      if(this.active!==job||!this.matches(job))return;
      if(result.kind!=='rewrite'||typeof result.text!=='string'||!result.text.trim())throw Error('Invalid prompt improvement; the original draft is preserved.');
      if(!await job.animation.settle(result.text)||this.active!==job||!this.matches(job))return;
      this.active=null;job.animation.stop();
      if(result.text!==job.text){this.deps.replace(result.text);this.undo={...this.deps.read(),original:job.text};this.publish('Prompt improved. Undo is available.');}
      else this.publish('The original wording is already clear.');
      this.deps.focus();
    }catch(error){if(this.active===job){this.cancel();this.publish('Could not improve the prompt. Your draft is unchanged.');this.deps.notice(error.message);}}
    finally{if(this.active===job)this.cancel();}
  }
}
