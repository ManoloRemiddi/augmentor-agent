// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Shared input/review vocabulary, without a Node or agent owner in the GUI.
import {questionInput} from './questions.js';
export function planCommand(text:string){
 const match=/^\/plan(?:\s+([\s\S]*))?$/.exec(text.trim());if(!match)return;
 const message=(match[1]??'').trim();return {active:message!=='off',message:message==='off'?'':message};
}
export function planReviewInput(plan:unknown){
 if(typeof plan!=='string'||!/^#[ \t]+\S/.test(plan.trim())||plan.length>65536)throw Error('Present the complete Markdown plan starting with a # heading (at most 65,536 characters).');
 return questionInput({questions:[{id:'plan-review',header:'Plan review',question:'Approve this plan and leave plan mode?',detail:plan,
  options:[{label:'Approve',description:'Leave plan mode; carry out the plan from the next step.'},{label:'Keep planning',description:'Stay in plan mode and revise the plan with your feedback.'}],intent:{kind:'plan-review',approve:'Approve'}}]});
}
