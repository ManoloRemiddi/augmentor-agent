// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Repeat preparation within the caller's deadline; never retry a dispatched click.
export async function harnessPointerClick(panel,expression,until){
 let point,diagnostic;
 try{await until(async()=>{
  const result=await panel.evaluate('(async()=>{const find=()=>('+expression+');const describe=e=>e?{tag:e.tagName,id:e.id,text:e.textContent?.slice(0,100)}:null;let e=find();const fail=reason=>({reason,target:describe(e),viewport:{width:innerWidth,height:innerHeight}});if(!e||!e.isConnected||e.disabled)return fail("unavailable");const original=e;e.scrollIntoView({block:"center",inline:"nearest"});await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));e=find();if(e!==original||!e?.isConnected||e.disabled)return fail("changed during scroll");const r=e.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2,hit=document.elementFromPoint(x,y);if(!r.width||!r.height||!e.contains(hit))return {...fail("center not hit"),rect:{x:r.x,y:r.y,width:r.width,height:r.height},hit:describe(hit)};return {point:{x,y}};})()');
  diagnostic=result;point=result?.point;return !!point;
 },'pointer ready: '+expression);}catch(error){error.message+=' '+JSON.stringify(diagnostic);throw error;}
 await panel.call('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});
 await panel.call('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});
}
