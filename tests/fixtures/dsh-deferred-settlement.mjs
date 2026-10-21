// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {authoredSettlementDshProject} from './dsh-settlement-project.mjs';
/** Independent native-envelope fixture: settlement/answer precede the catalogue,
 * as after the public v3-to-v4 finish stage. No historical source is borrowed. */
export function authoredDeferredSettlement(cwd){
 const f=authoredSettlementDshProject(cwd),rows=f.session.records,index=rows.findIndex(r=>r.event.type==='subagent/catalog'),[catalogue]=rows.splice(index,1);
 catalogue.event.data.label='AUTHORED-FUTURE-CATALOGUE-CONTENT';rows.push(catalogue);const reply={type:'event',event:{type:'assistant/message',seq:0,time:1700000000200,surfaceOp:'append',data:{turn:1,step:3,message:{role:'assistant',content:[{type:'text',text:'RECORDED-CLOSING-REPLY after the settlement.'}]}}}};rows.splice(rows.findIndex(r=>r.event.type==='turn/end'),0,reply);rows.forEach((r,i)=>r.event.seq=i);f.session.opening.cursor=rows.length-1;
 return {...f,catalogue,reply};
}
