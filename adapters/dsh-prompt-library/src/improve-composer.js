// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Uses DSH's public composer slot, draft actions, and model directory.
export function registerImproveComposer(ctx,React){
 const h=React.createElement;
 function Improve({useInput,inputActions,directory}){
  const input=useInput(s=>s),latest=React.useRef(input);latest.current=input;
  const [busy,setBusy]=React.useState(false),[preview,setPreview]=React.useState(''),[settling,setSettling]=React.useState(false),[note,setNote]=React.useState(''),[undo,setUndo]=React.useState(null);
  const button=React.useRef(null),active=React.useRef(null),[geometry,setGeometry]=React.useState(null);
  const cancel=()=>{active.current?.abort();active.current=null;setBusy(false);setSettling(false);setPreview('')};
  React.useEffect(()=>()=>{active.current?.abort();active.current=null},[]);
  React.useEffect(()=>{if(active.current&&!active.current.committing&&input?.draftRev!==active.current.revision)cancel()},[input?.draftRev]);
  React.useEffect(()=>{
   if(!busy)return;
   const card=button.current?.closest('[data-composer-card]'),editor=card?.querySelector('[contenteditable]');
   if(!card||!editor)return;
   const position=()=>{const c=card.getBoundingClientRect(),r=editor.getBoundingClientRect(),style=getComputedStyle(editor);setGeometry({left:r.left-c.left,top:r.top-c.top,width:r.width,height:r.height,font:style.font,lineHeight:style.lineHeight,padding:style.padding,color:getComputedStyle(card).color})};
   position();const observer=new ResizeObserver(position);observer.observe(editor);
   const key=e=>{if(e.key==='Enter'){e.preventDefault();e.stopPropagation()}else if(e.key==='Escape'){e.preventDefault();e.stopPropagation();cancel()}};
   card.addEventListener('keydown',key,true);return()=>{observer.disconnect();card.removeEventListener('keydown',key,true)};
  },[busy]);
  const improve=async()=>{
   if(active.current){cancel();return}
   const original=latest.current;
   if(!original?.draft.trim()||original.phase!=='plain'||original.occurrences?.length)return;
   const request=new AbortController();request.revision=original.draftRev;const timeout=setTimeout(()=>{if(active.current===request){cancel();setNote('Prompt improvement timed out. Try again.')}},75000);active.current=request;setBusy(true);setPreview(original.draft);setSettling(false);setNote('');setUndo(null);
   try{
    const model=await directory.load();if(!model.current)throw Error('Select a model first.');
    const response=await fetch('/api/augmentor-prompts',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({action:'improve',text:original.draft,provider:model.current.provider,model:model.current.model}),signal:request.signal});
    const result=await response.json();if(!response.ok||!result.ok)throw Error(result.error||'Could not improve the prompt.');
    if(active.current!==request)return;
    if(latest.current.draftRev!==original.draftRev){cancel();return;}
    if(result.kind!=='rewrite'){setNote(result.text);cancel();return}
    setPreview(result.text);setSettling(true);
    await new Promise(resolve=>setTimeout(resolve,700));
    if(active.current!==request)return;
    if(latest.current.draftRev!==original.draftRev){cancel();return;}
    request.committing=true;inputActions.setDraft(result.text);setUndo({original:original.draft,replacement:result.text,revision:original.draftRev});active.current=null;setBusy(false);setSettling(false);setPreview('');setNote('');
    button.current?.closest('[data-composer-card]')?.querySelector('[contenteditable]')?.focus();
   }catch(error){if(active.current===request){cancel();if(error.name!=='AbortError')setNote(error.message)}}finally{clearTimeout(timeout)}
  };
  const canUndo=Boolean(undo&&input?.draft===undo.replacement);
  React.useEffect(()=>{if(undo&&input?.draftRev>undo.revision&&input?.draft!==undo.replacement)setUndo(null)},[input?.draft,input?.draftRev,undo]);
  const undoImprovement=()=>{inputActions.setDraft(undo.original);setUndo(null);setNote('');button.current?.closest('[data-composer-card]')?.querySelector('[contenteditable]')?.focus()};
  const disabled=!inputActions||!input?.draft.trim()||input.phase!=='plain'||Boolean(input.occurrences?.length);
  return h(React.Fragment,null,
   h('style',null,`.augmentor-improve{position:absolute;right:8px;top:8px;z-index:12;pointer-events:auto;width:24px;height:24px;border:0;border-radius:5px;background:transparent;color:inherit;font-size:16px;cursor:pointer}.augmentor-improve:hover{background:rgba(127,150,150,.18)}.augmentor-improve:disabled{opacity:.35;cursor:default}[data-composer-card]:has(.augmentor-improve) [contenteditable]{padding-right:42px!important}[data-composer-card]:has(.augmentor-improve-busy) [contenteditable]{color:transparent!important;caret-color:transparent!important}.augmentor-letter-preview{position:absolute;z-index:10;pointer-events:none;white-space:pre-wrap;overflow-wrap:anywhere;overflow:hidden;box-sizing:border-box}.augmentor-letter-cell{display:inline-block;position:relative;height:1.3em;vertical-align:bottom;overflow:hidden}.augmentor-letter-width{visibility:hidden}.augmentor-letter-wheel{position:absolute;inset:0;animation:augmentor-letter-roll var(--speed) linear infinite;animation-delay:var(--delay)}.augmentor-letter-wheel span{display:block;height:1.3em}.augmentor-letter-preview.settle .augmentor-letter-wheel{animation:none;transform:translateY(0);transition:transform .3s}.augmentor-improve-status{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}@keyframes augmentor-letter-roll{from{transform:translateY(0)}to{transform:translateY(-2.6em)}}@media(prefers-reduced-motion:reduce){.augmentor-letter-wheel{animation:none}}`),
   h('button',{ref:button,type:'button',className:'augmentor-improve'+(busy?' augmentor-improve-busy':''),'aria-label':busy?'Cancel prompt improvement':canUndo?'Undo prompt improvement':'Improve prompt',disabled:!busy&&!canUndo&&disabled,onClick:canUndo&&!busy?undoImprovement:improve},busy?'×':canUndo?'↶':note?'!':'✦'),
   busy&&geometry&&h('div',{className:'augmentor-letter-preview'+(settling?' settle':''),style:geometry,'aria-hidden':true},Array.from(preview).map((char,i)=>/\s/.test(char)?char:h('span',{key:i,className:'augmentor-letter-cell',style:{'--speed':`${.28+(i%7)*.05}s`,'--delay':`${-i*.071}s`}},h('span',{className:'augmentor-letter-width'},char),h('span',{className:'augmentor-letter-wheel'},[char,String.fromCharCode(97+(i*13)%26),char].map((c,j)=>h('span',{key:j},c)))))),
   note&&h('span',{className:'augmentor-improve-status',role:'status'},note));
 }
 ctx.inject(['modelDirectories'],scope=>scope.slots.inject('conversation.input.overlay',()=>scope.slots.register({name:'conversation.input.overlay',id:'augmentor-improve-prompt',order:90,inject:sessionId=>({directory:scope.modelDirectories.directoryFor(sessionId)})},Improve)));
}
