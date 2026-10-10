// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Settings are explicit, revision guarded and owned by the existing Pi host.
export function attachReasoning({button,rpc,current,notice}){
 let dialog,epoch=0;
 const el=(tag,text)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;return node;};
 const action=(label,fn)=>{const button=el('button',label);button.type='button';button.onclick=fn;return button;};
 const select=(label,values,value)=>{const wrapper=el('label',label),input=el('select');input.setAttribute('aria-label',label);for(const [key,title] of values){const option=el('option',title);option.value=key;input.append(option);}input.value=value;wrapper.append(input);return {wrapper,input};};
 const checkbox=(label,value)=>{const wrapper=el('label'),input=el('input');input.type='checkbox';input.checked=value;input.setAttribute('aria-label',label);wrapper.append(input,document.createTextNode(' '+label));return {wrapper,input};};
 const close=()=>{epoch++;dialog?.close();dialog?.remove();dialog=undefined;};
 async function open(){
  close();const ticket=epoch,context=current();
  if(!context.ready||!context.sessionId){notice('Select a ready conversation before changing reasoning.',true);return;}
  dialog=el('dialog');dialog.className='reasoning-dialog';dialog.setAttribute('aria-label','Reasoning settings');
  const content=el('div'),status=el('p','Loading reasoning settings…');status.setAttribute('role','status');
  dialog.append(el('h2','Reasoning'),content,status,action('Done',close));document.body.append(dialog);dialog.showModal();dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
  const valid=()=>ticket===epoch&&current().sessionId===context.sessionId&&current().epoch===context.epoch;
  const safe=()=>{if(!valid()||!current().ready)throw Error('The selected conversation changed. Reopen reasoning settings.');};
  try{
   let [session,policy,catalog]=await Promise.all([rpc('session.reasoning',{sessionId:context.sessionId}),rpc('reasoning.describe'),rpc('models.list')]);if(!valid())return;
   const models=catalog.groups.flatMap(group=>group.models).filter(model=>model.available);
   const levelNames=session.availableLevels.map(level=>[level,level]);
   const mode=select('Reasoning mode',[['adaptive','Adaptive'],['manual','Manual']],session.mode),level=select('Saved thinking effort',levelNames,session.thinkingLevel);
   const effective=el('p'),conversation=el('fieldset');conversation.append(el('legend','This conversation'),mode.wrapper,level.wrapper,effective);
   const describe=()=>{effective.textContent='Adaptive status: '+session.adaptiveStatus+'. Saved effort: '+session.thinkingLevel+'.'+(session.lastDecision?' Last request: '+session.lastDecision.thinkingLevel+' ('+session.lastDecision.reason+').':' No reasoning decision recorded in this process.');};describe();
   conversation.append(el('small','Adaptive uses your explicit mappings below. Saved effort applies in Manual mode and when Adaptive has no matching route. Model changes never silently lower it.'));
   const saveSession=action('Save conversation',async()=>{saveSession.disabled=true;try{safe();session=await rpc('session.selectReasoning',{sessionId:context.sessionId,expectedRevision:session.revision,mode:mode.input.value,thinkingLevel:level.input.value});if(valid()){describe();status.textContent='Conversation reasoning saved.';}}catch(error){if(valid())status.textContent=error.message;}finally{if(valid())saveSession.disabled=false;}});
   conversation.append(saveSession);content.append(conversation);
   const global=el('fieldset');global.append(el('legend','Adaptive policy for this Pi profile'));
   const enabled=checkbox('Enable Adaptive Reasoning',policy.config.enabled),textOnly=checkbox('Use tools only when needed for supplied-text transformations',policy.config.textOnly);
   const linux=checkbox('Desktop and Harness conversations',policy.config.presets.includes('augmentor-linux-pi')),browser=checkbox('Browser conversations',policy.config.presets.includes('augmentor-browser-pi'));
   global.append(enabled.wrapper,textOnly.wrapper,linux.wrapper,browser.wrapper);
   const routeArea=el('div'),routes=[];
   const tierLabels={off:'Greeting / simple text',low:'Short summary',medium:'Analysis',high:'Complex work'};
   function addRoute(route){
    const row=el('fieldset'),name=el('legend',route.provider+'/'+route.model),controls={};
    const model=models.find(model=>model.provider===route.provider&&model.model===route.model),levels=model?.thinkingLevels??['off','minimal','low','medium','high','xhigh','max'];
    row.append(name);for(const tier of ['off','low','medium','high']){const field=select(tierLabels[tier],levels.map(level=>[level,level]),route.efforts[tier]);if(!levels.includes(route.efforts[tier])){const option=el('option',route.efforts[tier]+' (unavailable)');option.value=route.efforts[tier];field.input.append(option);field.input.value=route.efforts[tier];}controls[tier]=field.input;row.append(field.wrapper);}
    const item={route,controls,row};routes.push(item);row.append(action('Remove mapping',()=>{routes.splice(routes.indexOf(item),1);row.remove();}));routeArea.append(row);
   }
   policy.config.routes.forEach(addRoute);
   const modelChoice=select('Model to map',models.map(model=>[JSON.stringify([model.provider,model.model]),model.provider+'/'+model.model]),models.length?JSON.stringify([models[0].provider,models[0].model]):'');
   global.append(el('p','Map each task tier to an effort supported by the exact model. An unmapped model keeps its existing effort. No extra classification model is called.'),routeArea,modelChoice.wrapper,action('Add mapping',()=>{try{const [provider,model]=JSON.parse(modelChoice.input.value);if(routes.some(row=>row.route.provider===provider&&row.route.model===model))throw Error('This model already has a mapping.');const levels=models.find(item=>item.provider===provider&&item.model===model).thinkingLevels;addRoute({provider,model,efforts:Object.fromEntries(['off','low','medium','high'].map(tier=>[tier,levels.includes(tier)?tier:levels.at(-1)]))});status.textContent='Mapping added to the unsaved draft.';}catch(error){status.textContent=error.message;}}));
   const savePolicy=action('Save adaptive policy',async()=>{savePolicy.disabled=true;try{safe();policy=await rpc('reasoning.configure',{expectedRevision:policy.revision,config:{enabled:enabled.input.checked,textOnly:textOnly.input.checked,presets:[...(linux.input.checked?['augmentor-linux-pi']:[]),...(browser.input.checked?['augmentor-browser-pi']:[])],routes:routes.map(({route,controls})=>({provider:route.provider,model:route.model,efforts:Object.fromEntries(Object.entries(controls).map(([tier,input])=>[tier,input.value]))}))}});if(valid()){session=await rpc('session.reasoning',{sessionId:context.sessionId});if(valid()){describe();status.textContent='Adaptive policy saved.';}}}catch(error){if(valid())status.textContent=error.message;}finally{if(valid())savePolicy.disabled=false;}});
   global.append(savePolicy);content.append(global,action('Reload saved settings',open));status.textContent='Changes apply to subsequent requests. Save is refused while a conversation is working. Reload discards this settings draft.';
  }catch(error){if(valid())status.textContent=error.message;}
 }
 button.onclick=()=>open();
 return {changed(){if(dialog){const context=current();if(!context.sessionId||!context.ready)close();}},close};
}
