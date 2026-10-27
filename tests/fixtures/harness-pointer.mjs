// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Repeat preparation within the caller's deadline; never retry a dispatched click.
// Original rail/dock controls can remain hit-testable while their positions move.
export async function harnessPointerClick(panel,expression,until){
 // The owner-restored bottom composer has an explicit Send control; the old
 // supplier button remains hidden. Exercise the visible control with real input.
 expression=expression.replaceAll('Send message','Send to AH');
 expression=expression.replaceAll('Stop generating','Stop current turn');
 let point,diagnostic;
 try{await until(async()=>{
  const result=await panel.evaluate(`(async()=>{
   const find=()=>(${expression});
   const describe=e=>e?{tag:e.tagName,id:e.id,text:e.textContent?.slice(0,100)}:null;
   let e=find();const fail=reason=>({reason,target:describe(e),viewport:{width:innerWidth,height:innerHeight}});
   if(!e||!e.isConnected||(e.disabled||e.matches(":disabled")))return fail("unavailable");
   const original=e;e.scrollIntoView({block:"center",inline:"nearest"});let previous=e.getBoundingClientRect();
   for(let frame=0;frame<2;frame++){
    await new Promise(requestAnimationFrame);e=find();
    if(e!==original||!e?.isConnected||(e.disabled||e.matches(":disabled")))return fail("changed during scroll");
    const next=e.getBoundingClientRect();
    if(["x","y","width","height"].some(key=>Math.abs(next[key]-previous[key])>.1))return fail("control geometry is moving");
    previous=next;
   }
   for(let ancestor=e;ancestor;ancestor=ancestor.parentElement){
    if(ancestor.getAnimations().some(animation=>{const timing=animation.effect?.getComputedTiming();return (animation.playState==="running"||animation.pending)&&Number.isFinite(timing?.endTime)&&timing.progress!==null;}))return fail("finite control or ancestor animation is active");
   }
   const r=e.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2,hit=document.elementFromPoint(x,y);
   if(!r.width||!r.height||!e.contains(hit))return {...fail("center not hit"),rect:{x:r.x,y:r.y,width:r.width,height:r.height},hit:describe(hit)};
   return {point:{x,y}};
  })()`);
  diagnostic=result;point=result?.point;return !!point;
 },'pointer ready: '+expression);}catch(error){error.message+=' '+JSON.stringify(diagnostic);throw error;}
 await panel.call('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});
 await panel.call('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});
}

// Hover-only supplier actions need the row and control prepared together.
// Row scrolling/hover may repeat; the single eventual click never does.
export async function harnessHoverPointerClick(panel,rowExpression,controlExpression,until){
 let point,diagnostic;
 const stable=(expression,scroll)=>`(async()=>{
  const find=()=>(${expression});let e=find();
  const fail=reason=>({reason,target:e?{tag:e.tagName,id:e.id,text:e.textContent?.slice(0,100)}:null});
  if(!e||!e.isConnected||(e.disabled||e.matches(":disabled")))return fail("hover target unavailable");
  const original=e;${scroll?'e.scrollIntoView({block:"center",inline:"nearest"});':''}let previous=e.getBoundingClientRect();
  for(let n=0;n<2;n++){
   await new Promise(requestAnimationFrame);e=find();if(e!==original||!e?.isConnected||(e.disabled||e.matches(":disabled")))return fail("hover target replaced");
   const next=e.getBoundingClientRect();if(["x","y","width","height"].some(k=>Math.abs(next[k]-previous[k])>.1))return fail("hover geometry is moving");previous=next;
  }
  for(let p=e;p;p=p.parentElement)if(p.getAnimations().some(a=>{const t=a.effect?.getComputedTiming();return (a.playState==="running"||a.pending)&&Number.isFinite(t?.endTime)&&t.progress!==null;}))return fail("hover ancestor animation is active");
  const r=e.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2;
  if(!r.width||!r.height||!e.contains(document.elementFromPoint(x,y)))return {...fail("hover center not hit"),rect:{x:r.x,y:r.y,width:r.width,height:r.height}};
  return {point:{x,y},rect:{x:r.x,y:r.y,width:r.width,height:r.height}};
 })()`;
 try{await until(async()=>{
  const row=await panel.evaluate(stable(rowExpression,true));diagnostic={row};if(!row.point)return false;
  await panel.call('Input.dispatchMouseEvent',{type:'mouseMoved',...row.point});
  const control=await panel.evaluate(stable(controlExpression,false));
  const current=await panel.evaluate(`(()=>{const row=(${rowExpression}),control=(${controlExpression});if(!row||!control)return null;const r=row.getBoundingClientRect();return {hovered:row.matches(":hover"),contains:row.contains(control),rect:{x:r.x,y:r.y,width:r.width,height:r.height}};})()`);
  diagnostic={row,control,current};if(!control.point||!current?.hovered||!current.contains||Object.keys(row.rect).some(k=>Math.abs(row.rect[k]-current.rect[k])>.1))return false;
  point=control.point;return true;
 },'hover pointer ready: '+controlExpression);}catch(error){error.message+=' '+JSON.stringify(diagnostic);throw error;}
 await panel.call('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});
 await panel.call('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});
}

// Opaque frame controls need both coordinate spaces ready before one dispatch.
export async function harnessFramePointerClick(panel,frameEvaluate,iframeExpression,controlExpression,until){
 const geometry=expression=>`(async()=>{
  const e=(${expression});if(!e||!e.isConnected||(e.disabled||e.matches(":disabled")))return null;
  e.scrollIntoView({block:"center",inline:"nearest"});let previous=e.getBoundingClientRect();
  for(let n=0;n<2;n++){await new Promise(requestAnimationFrame);if(!e.isConnected||e.disabled||e.matches(":disabled"))return null;const now=e.getBoundingClientRect();if(["x","y","width","height"].some(k=>Math.abs(now[k]-previous[k])>.1))return null;previous=now;}
  for(let p=e;p;p=p.parentElement)if(p.getAnimations().some(a=>{const t=a.effect?.getComputedTiming();return (a.playState==="running"||a.pending)&&Number.isFinite(t?.endTime)&&t.progress!==null;}))return null;
  const r=e.getBoundingClientRect();if(!r.width||!r.height||!e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)))return null;
  return {x:r.x,y:r.y,width:r.width,height:r.height};
 })()`;
 let point,diagnostic;
 await until(async()=>{
  const outer=await panel.evaluate(geometry(iframeExpression)),inner=await frameEvaluate(geometry(controlExpression));if(!outer||!inner){diagnostic={outer,inner};return false;}
  const fresh=await panel.evaluate(`(()=>{const f=(${iframeExpression});if(!f)return null;const r=f.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};})()`);
  if(!fresh||Object.keys(outer).some(k=>Math.abs(outer[k]-fresh[k])>.1)){diagnostic={outer,inner,fresh};return false;}
  point={x:outer.x+inner.x+inner.width/2,y:outer.y+inner.y+inner.height/2};
  const hit=await panel.evaluate(`(()=>{const f=(${iframeExpression});return f===document.elementFromPoint(${point.x},${point.y});})()`);diagnostic={outer,inner,point,hit};return hit;
 },'frame pointer ready').catch(error=>{error.message+=' '+JSON.stringify(diagnostic);throw error;});
 await panel.call('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});
 await panel.call('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});
}
