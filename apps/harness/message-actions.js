// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** UI operation ownership. Pi's session.branch and product queue own execution. */
export function createMessageActions({context,input,rpc,refresh,select,enqueue,changed,notice,id=()=>crypto.randomUUID()}){
 let busy=false,editing=null;const identities=new Map();
 const inputChanged=()=>input.dispatchEvent?.(new (input.ownerDocument?.defaultView?.Event??Event)('input',{bubbles:true}));
 const same=source=>{const now=context();return now.sessionId===source.sessionId&&now.epoch===source.epoch;};
 const available=()=>{const now=context();return !!now.sessionId&&!now.running&&!now.submitting&&!busy;};
 async function fork(source,seq,mode,edit=null){
  const key=JSON.stringify([source.sessionId,seq,mode]);
  if(!identities.has(key))identities.set(key,id());
  const row=await rpc('session.branch',{sessionId:source.sessionId,newSessionId:identities.get(key),messageSeq:seq,mode});
  await refresh();
  if(!same(source)||(edit&&editing!==edit))return null;
  if(edit)edit.childId=row.sessionId;
  await select(row.sessionId,{preserveEdit:!!edit});
  if(context().sessionId!==row.sessionId||(edit&&editing!==edit))return null;
  identities.delete(key);
  return row;
 }
 function cancel(){
  if(!editing||busy)return false;
  input.value=editing.draft;editing=null;inputChanged();changed();return true;
 }
 function reset(){if(editing&&!input.value){input.value=editing.draft;inputChanged();}editing=null;changed();}
 function edit(seq,text){
  if(!available()||context().editSeq!==seq)return false;
  const source=context();editing={source,seq,draft:editing?.draft??input.value};input.value=text;inputChanged();input.focus?.();changed();return true;
 }
 async function reply(seq){
  if(!available()||editing||!context().replies.has(seq))return false;
  const source=context();busy=true;changed();
  try{const row=await fork(source,seq,'reply');if(row)notice('New conversation created after the selected reply.');return !!row;}
  catch(error){if(same(source))notice(error.message+' No prompt was sent; nothing was retried automatically.',true);return false;}
  finally{busy=false;changed();}
 }
 async function submit(){
  if(!editing||!available())return false;
  const edit=editing,text=input.value.trim();if(!text)return false;
  const source=context();input.value='';inputChanged();busy=true;changed();let attempted=false;
  try{
   let child=edit.childId;
   if(child){if(source.sessionId!==child)throw Error('Conversation changed before the edited input was sent.');}
   else{
    if(!same(edit.source)||source.editSeq!==edit.seq)throw Error('The latest input changed. Cancel Edit and review the conversation.');
    const row=await fork(source,edit.seq,'edit',edit);if(!row)return false;child=row.sessionId;
   }
   if(editing!==edit||context().sessionId!==child)return false;
   // Once queue admission is attempted, its durable receipt owns uncertainty.
   // Never retain an editor that could silently submit another copy on retry.
   attempted=true;const accepted=await enqueue(child,text);
   if(!accepted){attempted=false;throw Error('Edited input was not submitted. Check the selected conversation.');}
   return true;
  }catch(error){if(editing===edit)notice(error.message+' Nothing was resent automatically.',true);return false;}
  finally{
   if(editing===edit){
    if(attempted){editing=null;if(context().sessionId===edit.childId&&!input.value){input.value=edit.draft;inputChanged();}}
    else if((same(source)||context().sessionId===edit.childId)&&!input.value){input.value=text;inputChanged();}
   }
   busy=false;changed();
  }
 }
 return {edit,reply,submit,cancel,reset,get busy(){return busy},get editing(){return editing}};
}
