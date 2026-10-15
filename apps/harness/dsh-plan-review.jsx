// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Existing MIT DSH plan presentation, with only its scoped Pi data/navigation binding.
import React,{useMemo,useSyncExternalStore} from 'react';
import {extractMarkdownPlainText} from '@deepseek-ai/dsh-client-ui-primitives';
import {PlanCards,PlanReviewOpen} from '@dsh-gui/ui-plan/src/client/PlanCard.tsx';
import {PlanPreview,PlanTitle} from '@dsh-gui/ui-plan/src/client/PlanPreview.tsx';
import {createPlanReviewStore} from '@dsh-gui/ui-plan/src/client/review-store.ts';
import {reviewPreviewAddress} from '@dsh-gui/ui-plan/src/client/review-preview.ts';
import {en} from '@dsh-gui/ui-plan/src/client/locales.ts';
import {en as commonEn} from '@dsh-gui/locale/src/locales/en.ts';
import {questionInput,questionAnswer} from '../../packages/runtime/src/questions.ts';
const t=(key,args={})=>String(en[key]??commonEn[key]??key).replace(/\{(\w+)\}/g,(_,k)=>String(args[k]??''));
const id='@deepseek-ai/dsh-client-ui-plan',none=()=>({status:'none'});
export function bindPlanReview(previews){
 previews.registry.register({id,kind:'plan',patterns:['dsh-resource://plan-review/**'],priority:'builtin',title:()=>t('preview.title')});
 previews.slots.set('sidebar.right.pane.tab::'+id,props=><PlanPreview {...props} useResource={none} t={t}/>);
 previews.slots.set('sidebar.right.pane.tab.title::'+id,props=><PlanTitle {...props} useResource={none}/>);
 const stores=new Map();
 const open=(sessionId,epoch,review,key)=>{
  if(!previews.valid(sessionId,epoch))return;
  const address=reviewPreviewAddress(sessionId,key),planReview={markdown:review.plan,title:extractMarkdownPlainText(review.plan,{mode:'first-line'})};
  previews.sidebar.actions.openContent(sessionId,{kind:'plan',contentId:address,title:planReview.title},tab=>previews.domain.navigate(sessionId,tab,{address,params:{planReview}}));
 };
 function Actions({review,requestKey,state}){
  const sessionId=state.sessionId,epoch=previews.controller.epoch;
  if(!stores.has(sessionId))stores.set(sessionId,createPlanReviewStore().create());
  const store=stores.get(sessionId),openReview=useMemo(()=>(review,key)=>open(sessionId,epoch,review,key),[sessionId,epoch]);
  const useStore=(selector=x=>x)=>selector(useSyncExternalStore(store.subscribe,store.getSnapshot));
  return <PlanReviewOpen review={review} requestKey={requestKey} openReview={openReview} useSidebarMounted={selector=>selector(previews.valid(sessionId,epoch)?sessionId:undefined)} useStore={useStore} actions={store.actions} t={t}/>;
 }
 function Recorded({data,state}){
  const plan=useMemo(()=>{
   if(data.name!=='ask_user'||data.result?.details?.schema!=='augmentor-question-answer/1')return null;
   try{const {questions}=questionInput(data.call?.arguments),q=questions[0];if(questions.length!==1||!q.intent)return null;
    if(data.result.details.status==='answered')questionAnswer(questions,{answer:data.result.details.answer});
    return {callId:String(data.seq),title:extractMarkdownPlainText(q.detail,{mode:'first-line'}),markdown:q.detail};
   }catch{return null;}
  },[data.call,data.result,data.seq]);
  if(!plan||state.readOnly)return null;
  const sessionId=state.sessionId,epoch=previews.controller.epoch;
  return <PlanCards turn={{turn:0}} usePlans={()=>[plan]} openPlan={()=>open(sessionId,epoch,{plan:plan.markdown},'recorded:'+data.seq)} t={t}/>;
 }
 return {Actions,Recorded};
}
