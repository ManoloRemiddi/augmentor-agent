// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Read-only identities for the original Fleet presentation. A native fork is
 * not a delegated agent. The exact parent's retained job catalogue and the
 * child's saved delegation identity must agree before a link is presented. */
export interface FamilyMeta {
 id:string;title:string;cwd:string;running:boolean;updatedAt:number;
 delegation?:{parentId:string;jobId:string};
}
export interface FamilyJob {
 id:string;owner:string;kind:string;state:string;createdAt:number;updatedAt:number;
 childId?:string;requests:number;tools:number;outputTokens:number;
 usageRecorded?:boolean;usageAccounted?:boolean;
}
const active=new Set(['starting','running','stopping']);
const states=new Set([...active,'completed','failed','cancelled','unknown']);
const stamp=(value:number)=>Number.isSafeInteger(value)&&value>=0?value:0;
const counter=(value:number)=>Number.isSafeInteger(value)&&value>=0?value:null;
const title=(meta:FamilyMeta)=>({title:meta.title.slice(0,512),titleTruncated:meta.title.length>512});
export function sessionFamily(parent:FamilyMeta,jobs:readonly FamilyJob[],metaOf:(id:string)=>FamilyMeta|undefined,problem?:string){
 if(parent.delegation)throw Error('Delegated conversations are controlled by their parent job.');
 const scope='retained-exact-parent-job-catalogue; forks and shell commands are not agents; reads do not run or account work';
 if(problem)return {available:false,reason:problem,scope,items:[],coverage:null};
 const root={sessionId:parent.id,relation:'root',...title(parent),cwd:parent.cwd,running:parent.running,updatedAt:stamp(parent.updatedAt)};
 const items:Record<string,unknown>[]=[root];
 let pendingChildren=0,unavailableChildren=0,agentJobs=0;
 const seen=new Set<string>();
 for(const job of [...jobs].sort((a,b)=>a.createdAt-b.createdAt||a.id.localeCompare(b.id))){
  if(job.owner!==parent.id)throw Error('Job catalogue belongs to another conversation.');
  if(job.kind!=='delegate'&&job.kind!=='desktop')continue;
  agentJobs++;
  if(!job.childId){if(active.has(job.state))pendingChildren++;else unavailableChildren++;continue;}
  const child=metaOf(job.childId);
  if(!child||child.id!==job.childId||child.id===parent.id||seen.has(child.id)||child.delegation?.parentId!==parent.id||child.delegation.jobId!==job.id||!states.has(job.state)){unavailableChildren++;continue;}
  seen.add(child.id);
  items.push({sessionId:child.id,parentId:parent.id,relation:'delegation',jobId:job.id,kind:job.kind,...title(child),running:active.has(job.state),updatedAt:Math.max(stamp(child.updatedAt),stamp(job.updatedAt)),reportedState:job.state,reportedRequests:counter(job.requests),reportedTools:counter(job.tools),reportedOutputTokens:counter(job.outputTokens),usageRecorded:job.usageRecorded===true,usageAccounted:job.usageAccounted===true});
 }
 return {available:true,scope,items,coverage:{retainedJobs:jobs.length,agentJobs,verifiedChildren:items.length-1,pendingChildren,unavailableChildren,historicalCompleteness:'not-established; removed receipts are not rediscovered',completion:'reported producer disposition; task success is not established'}};
}
