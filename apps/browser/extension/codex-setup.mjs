// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import {presentSettingsForm} from './settings-form.mjs'

export function codexSetupDialog(doc,send,container){
  const make=(tag,text)=>{const e=doc.createElement(tag);if(text)e.textContent=text;return e}
  const dialog=make('dialog');dialog.className='shared-prompt-editor memory-dialog codex-setup'
  const form=make('fieldset'),fields={}
  for(const [name,label,type] of [['profile','Saved connection','select'],['kind','Connection type','select'],['name','Connection name','text'],['endpoint','Endpoint URL','url'],['model','Model ID','text'],['credential','API key','password'],['remove','Remove the saved key','checkbox']]){
    const row=make('label',label),input=make(type==='select'?'select':'input');if(type!=='select')input.type=type
    input.setAttribute('aria-label',label);row.append(input);form.append(row);fields[name]=input
  }
  for(const [value,label] of [['api','API provider'],['local','Local model'],['chatgpt-plan','ChatGPT plan']]){const option=make('option',label);option.value=value;fields.kind.append(option)}
  fields.credential.placeholder='Optional; blank keeps the saved key'
  fields.endpoint.placeholder='https://provider.example/v1 or http://127.0.0.1:8080/v1'
  const modelChoices=make('datalist');modelChoices.id='codex-account-models-'+crypto.randomUUID();fields.model.setAttribute('list',modelChoices.id);form.append(modelChoices)
  const note=make('p'),actions=make('div');note.setAttribute('role','status')
  let rows=[],profileId=null,busy=false,dirty=false,closed=false,profileAccountId=null
  const accountForm=make('fieldset'),accountSelect=make('select'),accountNote=make('p'),accountActions=make('div')
  accountSelect.setAttribute('aria-label','ChatGPT account');accountNote.setAttribute('role','status');accountForm.append(make('legend','ChatGPT account'),accountSelect,accountNote,accountActions)
  let accountStatus={},accountBusy=false,ownedAttempt=null,pollTimer=null
  const view=doc.defaultView
  const request=async payload=>{const result=await send('codexSetup',{request:payload});if(!result.ok)throw Error(result.error);return result.result}
  const accountControls=()=>{
    const pending=['opening','waiting','saving'].includes(accountStatus.attempt?.state),allowed=accountStatus.enabled===true&&!pending&&!accountBusy&&!busy
    signIn.disabled=!allowed;allowPlan.disabled=!allowed||!accountSelect.value;cancelLogin.disabled=!pending||accountBusy;signOut.disabled=!accountSelect.value||pending||accountBusy||busy
    accountSelect.disabled=pending||accountBusy||busy
    fields.kind.querySelector('[value="chatgpt-plan"]').disabled=accountStatus.enabled!==true
    const plan=fields.kind.value==='chatgpt-plan',account=accountStatus.accounts?.find(row=>row.id===accountSelect.value),ready=!plan||(accountStatus.enabled===true&&account?.signedIn===true&&account?.planUsage===true)
    if(!plan||!ready)modelChoices.replaceChildren()
    for(const field of [fields.endpoint,fields.credential,fields.remove])field.disabled=plan
    save.disabled=busy||!ready;check.disabled=busy||dirty||!profileId||!ready;imageCheck.disabled=check.disabled
    loadModels.hidden=!plan;loadModels.disabled=!plan||!ready||!allowed
    providerNotice.textContent=plan?'This connection uses the selected ChatGPT plan. Connection checks consume plan usage and send only synthetic test input. No API key is used. Enter a model ID and check its availability before starting a chat.':apiNotice
  }
  const controls=()=>{form.disabled=busy;save.disabled=busy;check.disabled=busy||dirty||!profileId;imageCheck.disabled=check.disabled;close.disabled=busy;accountControls()}
  const button=(label,fn)=>{const b=make('button',label);b.type='button';b.onclick=fn;actions.append(b);return b}
  const run=async fn=>{if(busy)return;busy=true;controls();try{await fn()}catch(error){if(!closed)note.textContent=error.message}finally{busy=false;if(!closed)controls()}}
  const selected=()=>{
    profileId=fields.profile.value||null;const row=rows.find(row=>row.id===profileId)||{}
    profileAccountId=row.accountId||null;if(profileAccountId)accountSelect.value=profileAccountId
    fields.name.value=row.name||'My Codex model';fields.kind.value=row.kind||'api';fields.endpoint.value=row.endpoint||'';fields.model.value=row.model||'';fields.credential.value='';fields.remove.checked=false;dirty=false
    note.textContent=row.toolsVerified?'Codex tool check passed for this connection.':row.imageValidatedAt?'Image response checked; screenshots are available in new chats.':row.validation==='responses-text'?'Text response checked; tool compatibility is not verified.':'Save a connection, then check it with Codex.';controls()
  }
  const load=async()=>{
    rows=(await request({action:'profiles'})).profiles
    fields.profile.replaceChildren();for(const row of [{id:'',name:'New connection'},...rows]){const option=make('option',row.name);option.value=row.id;fields.profile.append(option)}
    fields.profile.value=profileId||'';selected()
  }
  const showAccounts=value=>{
    if(closed)return
    accountStatus=value;const selected=profileAccountId||accountSelect.value
    accountSelect.replaceChildren();for(const row of [{id:'',label:'Add a ChatGPT account'},...value.accounts||[]]){const option=make('option',row.label+(row.active?' · selected':''));option.value=row.id;accountSelect.append(option)}
    accountSelect.value=[...accountSelect.options].some(row=>row.value===selected)?selected:''
    const attempt=value.attempt
    accountNote.textContent=value.reason?value.reason+(value.notice?' '+value.notice:''):value.notice||attempt?.message||(['opening','waiting'].includes(attempt?.state)?'Complete sign-in in your browser.':attempt?.state==='saving'?'Saving the verified account…':'Account login is available. Model connections are configured separately.')
    if(attempt?.id===ownedAttempt&&!['opening','waiting','saving'].includes(attempt.state))ownedAttempt=null
    accountControls()
  }
  const cancelOwned=()=>{const id=ownedAttempt;ownedAttempt=null;if(id)void request({action:'account-cancel',account:{attemptId:id}}).catch(()=>{})}
  const accountRun=async fn=>{
    if(accountBusy||closed)return;accountBusy=true;accountControls()
    try{await fn()}catch(error){if(!closed)accountNote.textContent=error.message}
    finally{accountBusy=false;if(!closed)accountControls()}
  }
  const pollAccounts=async()=>{
    if(closed)return
    await accountRun(async()=>showAccounts(await request({action:'account-status'})))
    if(!closed)pollTimer=view.setTimeout(pollAccounts,1000)
  }
  const accountButton=(label,fn)=>{const b=make('button',label);b.type='button';b.onclick=fn;accountActions.append(b);return b}
  const startLogin=plan=>accountRun(async()=>{
    const account={requestPlanUsage:plan};if(accountSelect.value)account.accountId=accountSelect.value
    const value=await request({action:'account-start',account});ownedAttempt=value.attempt.id
    if(closed){cancelOwned();return}showAccounts({...accountStatus,notice:undefined,attempt:value.attempt})
  })
  const signIn=accountButton('Sign in with ChatGPT',()=>startLogin(false))
  const allowPlan=accountButton('Allow ChatGPT plan usage',()=>startLogin(true))
  const cancelLogin=accountButton('Cancel sign-in',()=>accountRun(async()=>{await request({action:'account-cancel',account:{attemptId:accountStatus.attempt.id}});showAccounts(await request({action:'account-status'}))}))
  const signOut=accountButton('Sign out',()=>accountRun(async()=>{
    const value=await request({action:'account-sign-out',account:{accountId:accountSelect.value}});showAccounts(value.status)
    if(!closed)accountNote.textContent=value.remoteRevocationConfirmed&&value.localCleanupConfirmed?'Signed out; remote revocation and local cleanup confirmed.':
      'Signed out. '+(!value.remoteRevocationConfirmed?'Remote revocation is unconfirmed. ':'')+(!value.localCleanupConfirmed?'Unlock the OS credential store to finish local cleanup.':'')
  }))
  accountSelect.onchange=()=>{profileAccountId=null;modelChoices.replaceChildren();if(fields.kind.value==='chatgpt-plan')dirty=true;accountControls()}
  const close=button('Close',()=>dialog.close())
  const check=button('Check Codex connection',()=>run(async()=>{note.textContent='Checking Codex chat and tool support…';await request({action:'test',id:profileId,capability:'agent'});note.textContent='Codex chat and the test tool worked. Browser and desktop tasks still need their own checks.'}))
  const imageCheck=button('Check image response',()=>run(async()=>{note.textContent='Checking a synthetic image…';await request({action:'test',id:profileId,capability:'image'});await load();note.textContent='Image response verified. Start a new chat to use browser screenshots. General vision and tool accuracy still need a chat test.'}))
  const save=button('Save connection',()=>run(async()=>{
    const profile={id:profileId||crypto.randomUUID(),kind:fields.kind.value,name:fields.name.value.trim(),endpoint:fields.endpoint.value.trim(),model:fields.model.value.trim()}
    if(fields.kind.value==='chatgpt-plan')profile.accountId=accountSelect.value
    else if(fields.remove.checked)profile.credential=null;else if(fields.credential.value)profile.credential=fields.credential.value
    note.textContent='Saving connection…';const row=await request({action:'configure',profile});profileId=row.id;fields.credential.value=''
    await load();const refreshed=await send('models-refresh');if(!refreshed.ok)throw Error('Connection saved. Refresh the model picker to use it. '+(refreshed.error||''))
  }))
  const loadModels=button('Load ChatGPT models',()=>run(async()=>{
    const accountId=accountSelect.value;modelChoices.replaceChildren();note.textContent='Loading models for the selected ChatGPT account…'
    const result=await request({action:'account-models',account:{accountId}})
    if(closed||fields.kind.value!=='chatgpt-plan'||accountSelect.value!==accountId||result.accountId!==accountId)return
    for(const row of result.models){const option=make('option',row.name);option.value=row.id;option.label=row.name;modelChoices.append(option)}
    note.textContent=result.models.length?'Account models loaded. Choose a model, save the connection and check it before starting a chat.':'This account returned no models to display.'
  }))
  for(const [key,field] of Object.entries(fields)){if(key==='profile')continue;field.oninput=()=>{
    if(key==='kind'&&fields.kind.value==='chatgpt-plan'){fields.endpoint.value='https://api.openai.com/v1';fields.credential.value='';fields.remove.checked=false}
    if(key==='kind')modelChoices.replaceChildren()
    dirty=true;controls()
  }}
  fields.profile.onchange=selected
  const apiNotice='Keys are stored in the operating system credential store. Checks send a short tool exercise or a synthetic image that your provider may charge for. The Codex check uses one harmless test tool and sends no personal files or chat history. The image check enables screenshots for new chats.',providerNotice=make('p',apiNotice)
  dialog.append(make('h3','Connect a model · Codex'),make('p','Use a Responses-compatible API provider or local model. ChatGPT account availability is shown below.'),form,accountForm,providerNotice,note,actions)
  dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault()})
  dialog.addEventListener('close',()=>{closed=true;view.clearTimeout(pollTimer);cancelOwned();fields.credential.value='';dialog.remove()})
  doc.body.append(dialog);presentSettingsForm(dialog,container);accountControls();void run(load);void pollAccounts();return dialog
}
