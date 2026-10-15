// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Product binding for the public DSH question/answer vocabulary, on Pi's real tool lifecycle.
import {Type,type Static} from 'typebox';
import * as Value from 'typebox/value';
import type {ExtensionAPI} from '@earendil-works/pi-coding-agent';
import type {Interactions} from './interactions.js';

const option=Type.Object({label:Type.String({minLength:1,maxLength:1024}),description:Type.Optional(Type.String({maxLength:4096}))},{additionalProperties:false});
const question=Type.Object({id:Type.String({minLength:1,maxLength:128}),question:Type.String({minLength:1,maxLength:16000}),header:Type.Optional(Type.String({maxLength:256})),detail:Type.Optional(Type.String({maxLength:65536})),options:Type.Optional(Type.Array(option,{maxItems:16})),multiSelect:Type.Optional(Type.Boolean()),intent:Type.Optional(Type.Object({kind:Type.Literal('plan-review'),approve:Type.String({minLength:1,maxLength:1024})},{additionalProperties:false}))},{additionalProperties:false});
export const QUESTION_INPUT=Type.Object({question:Type.Optional(Type.String({minLength:1,maxLength:16000})),options:Type.Optional(Type.Array(Type.String({minLength:1,maxLength:1024}),{maxItems:16})),questions:Type.Optional(Type.Array(question,{minItems:1,maxItems:8}))},{additionalProperties:false});
export type Question=Static<typeof question>;
type Answer={answers:{id:string;selected:string[];custom?:string}[]};
export function questionInput(input:unknown):{questions:Question[];legacy:boolean}{
 if(!Value.Check(QUESTION_INPUT,input)||new TextEncoder().encode(JSON.stringify(input)).length>131072)throw Error('Invalid or oversized question request.');
 const value=input as Static<typeof QUESTION_INPUT>,legacy=value.question!==undefined;
 if(legacy===(value.questions!==undefined)||!legacy&&value.options!==undefined)throw Error('Supply either one question or a complete question batch.');
 const questions:Question[]=legacy?[{id:'answer',question:value.question!,options:value.options?.map(label=>({label}))}]:structuredClone(value.questions!);
 if(new Set(questions.map(q=>q.id)).size!==questions.length)throw Error('Question IDs must be unique.');
 for(const q of questions){
  if(!q.id.trim()||!q.question.trim()||q.options?.some(o=>!o.label.trim())||new Set(q.options?.map(o=>o.label)).size!==(q.options?.length??0))throw Error('Question choices must have unique nonempty labels.');
  if(q.intent&&(questions.length!==1||q.multiSelect||!q.detail?.trim()||!q.options?.some(o=>o.label===q.intent!.approve)||q.options.length>2))throw Error('A plan review requires one complete plan and its exact approval choice.');
 }
 return {questions,legacy};
}
export function questionAnswer(questions:Question[],value:unknown):Answer|undefined{
 if(value&&typeof value==='object'&&(value as any).cancelled===true&&Object.keys(value).length===1)return;
 const answer=(value as any)?.answer;
 if(!answer||!Array.isArray(answer.answers)||answer.answers.length!==questions.length||new TextEncoder().encode(JSON.stringify(value)).length>131072)throw Error('Answer every question exactly once, or explicitly cancel.');
 const seen=new Set<string>(),answers:Answer['answers']=[];
 for(const item of answer.answers){
  const q=questions.find(q=>q.id===item?.id);
  if(!q||seen.has(item.id)||!Array.isArray(item.selected)||item.selected.some((label:unknown)=>typeof label!=='string'||!q.options?.some(o=>o.label===label))||new Set(item.selected).size!==item.selected.length||(!q.multiSelect&&item.selected.length>1)||item.custom!==undefined&&(typeof item.custom!=='string'||item.custom.length>16000)||Object.keys(item).some(k=>!['id','selected','custom'].includes(k)))throw Error('The answer does not match this question request.');
  if(!q.multiSelect&&item.selected.length&&item.custom?.trim())throw Error('Choose one option or provide a custom answer.');
  seen.add(item.id);answers.push({id:item.id,selected:[...item.selected],...(item.custom?.trim()?{custom:item.custom}:{})});
 }
 // Request order is stable even if a client sends the complete batch reordered.
 return {answers:questions.map(q=>answers.find(a=>a.id===q.id)!)};
}
export function piQuestions(interactions:Interactions,sessionId:string,ownerId=sessionId){return (pi:ExtensionAPI)=>{
 pi.registerTool({name:'ask_user',label:'Ask user',description:'Ask for required missing information: supply question/options for one answer, or questions for a complete batch with stable IDs, optional detail and multiSelect. For one plan review use detail as the complete plan and intent {kind:"plan-review",approve:<exact offered label>}. A plan decision grants no permission to execute tools. Empty selections without custom text mean the human explicitly skipped that question. Never infer an answer after cancellation.',parameters:QUESTION_INPUT,
  async execute(toolCallId,input,signal){
   const {questions,legacy}=questionInput(input);
   const result=await interactions.ask(sessionId,'question/requested',{questions,toolName:'ask_user',toolCallId,ownerId},{signal},ownerId,value=>questionAnswer(questions,value));
   const answer=result as Answer|undefined,first=answer?.answers[0];
   return {content:[{type:'text',text:legacy?(first?.custom??first?.selected[0]??'User did not answer.'):JSON.stringify(answer??{unanswered:true})}],details:{schema:'augmentor-question-answer/1',status:answer?'answered':'unanswered',...(answer?{answer}:{})}};
  },
 });
};}
