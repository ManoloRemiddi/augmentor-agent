// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Bind the original MIT persisted store to its actual conversation, without a second answer channel.
function legacyProgress(value,questions){
 if(!value||!Array.isArray(questions)||!questions.length||questions.length>8||!Number.isInteger(value.index)||value.index<0||value.index>=questions.length||!Array.isArray(value.drafts)||value.drafts.length!==questions.length||value.wait!==undefined&&!['editing','waiting'].includes(value.wait))return;
 const drafts=[];
 for(const [i,draft] of value.drafts.entries()){
  const offered=new Set((questions[i].options??[]).map(x=>x.label));
  if(!draft||!Array.isArray(draft.selected)||draft.selected.length>16||new Set(draft.selected).size!==draft.selected.length||draft.selected.some(x=>typeof x!=='string'||!offered.has(x))||typeof draft.custom!=='string'||draft.custom.length>16000||typeof draft.skipped!=='boolean')return;
  drafts.push({selected:[...draft.selected],custom:draft.custom,skipped:draft.skipped});
 }
 return {index:value.index,drafts,...(value.wait?{wait:value.wait}:{})};
}
export function scopedQuestionDrafts(handle,sessionId,frames,storage){
 const store=handle.create(sessionId);
 try{
  storage??=globalThis.localStorage;
  if(!storage||typeof handle.spec?.persist!=='string')return store;
  const live=frames.filter(f=>f.method==='question/requested'&&f.payload?.sessionId===sessionId&&typeof f.rpcId==='string'&&!Object.hasOwn(store.getSnapshot().progressByRequest,f.rpcId));
  if(!live.length)return store;
  const raw=storage.getItem(handle.spec.persist);if(typeof raw!=='string'||raw.length>131072||new TextEncoder().encode(raw).length>131072)return store;
  const saved=JSON.parse(raw)?.progressByRequest;if(!saved||typeof saved!=='object'||Array.isArray(saved))return store;
  for(const frame of live){if(!Object.hasOwn(saved,frame.rpcId))continue;const progress=legacyProgress(saved[frame.rpcId],frame.payload.questions);if(progress)store.actions.replace(frame.rpcId,progress);}
 }catch{/* Browser storage can be unavailable. Keep the original in-memory controls and legacy record. */}
 // Preserve the old shared record: another still-open client may own its unsent content.
 return store;
}
/** Prune only after an authoritative pending snapshot for the selected operator conversation. */
export function syncQuestionDrafts(stores,createHandle,state,storage){
 if(state.phase!=='ready'||state.readOnly||!state.sessionId)return;
 const sid=state.sessionId,frames=state.interactions??[];
 if(!stores.has(sid))stores.set(sid,scopedQuestionDrafts(createHandle(),sid,frames,storage));
 const store=stores.get(sid),keep=frames.filter(f=>f.method==='question/requested'&&f.payload?.sessionId===sid).map(f=>f.rpcId),live=new Set(keep);
 if(Object.keys(store.getSnapshot().progressByRequest).some(key=>!live.has(key)))store.actions.prune(keep);
 return store;
}
