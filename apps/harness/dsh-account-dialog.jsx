// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useState,useSyncExternalStore} from 'react';
import {SignInDialog} from '@dsh-gui/ui-settings-account/src/client/SignInDialog.tsx';
import {Button} from '@deepseek-ai/dsh-client-ui-primitives';
import css from '@dsh-gui/ui-settings-account/src/client/SignInDialog.module.css';
import fields from '@dsh-gui/ui-settings-models/src/client/ModelsSection.module.css';

function AccountPrompt({scope,requestId,prompt}){
 const [value,setValue]=useState(prompt.type==='select'?prompt.options?.[0]?.id??'':''),[busy,setBusy]=useState(false),[failed,setFailed]=useState(false);
 const submit=async event=>{event.preventDefault();if(busy)return;setBusy(true);setFailed(false);try{await scope.respond(requestId,prompt.id,value);}catch{setFailed(true);}finally{setBusy(false);}};
 return <form onSubmit={submit} className={css.description}>
  <label className={fields.field}><span className={fields.fieldLabel}>{prompt.message}</span>
   {prompt.type==='select'?<select className={fields.input} aria-label={prompt.message} value={value} disabled={busy} onChange={event=>setValue(event.target.value)}>{prompt.options.map(option=><option key={option.id} value={option.id}>{option.label}</option>)}</select>:<input className={fields.input} aria-label={prompt.message} type={['secret','manual_code'].includes(prompt.type)?'password':'text'} autoComplete="off" spellCheck={false} placeholder={prompt.placeholder} value={value} disabled={busy} onChange={event=>setValue(event.target.value)}/>}
  </label>
  {prompt.type==='select'&&prompt.options.find(option=>option.id===value)?.description&&<p>{prompt.options.find(option=>option.id===value).description}</p>}
  {failed&&<p role="alert">The answer could not be confirmed. Inspect the current account step before continuing. Nothing was resubmitted.</p>}
  <Button variant="outline" type="submit" disabled={busy}>Continue</Button>
 </form>;
}
export function DshAccountDialog({scope,provider,close}){
 const state=useSyncExternalStore(scope.subscribe,scope.getSnapshot);
 const [requestId,setRequestId]=useState(()=>state.busy&&state.receipt?.provider===provider?state.receipt.requestId:null);
 const owns=!!requestId&&state.receipt?.requestId===requestId&&state.receipt?.provider===provider;
 const row=owns?state.receipt:null,interaction=owns?state.interaction:null,active=owns&&state.busy;
 const uncertain=state.status==='error'||state.needsRefresh&&!state.busy;
 const account={view:uncertain&&!active?undefined:{status:row?.state==='completed'?'credential-stored':'idle',...(row?{attempt:{id:row.requestId,phase:active?'waiting-browser':row.state==='completed'?'complete':'failed',authorizeUrl:interaction?.authorizationUrl}}:{})},failed:uncertain||!!row&&!active&&row.state!=='completed'};
 const copy={loginTitle:'Sign in to '+provider,loginDescription:'Pi will use this provider’s sign-in flow. A successful sign-in replaces the credential currently stored for this provider. Profile and environment keys are kept.',signIn:'Sign in',failureTitle:'Account sign-in needs review',failed:'Sign-in could not be confirmed. Close this dialog, inspect account status and refresh model settings before trying again. Nothing was retried.',noResponse:'No provider response was confirmed. Refresh model settings before trying again.',browserTitle:'Sign in to '+provider,browserPrompt:'Open the provider page or ',copyLink:'copy sign-in link',copiedLink:'link copied',copyFailed:'could not copy link',browserDescription:active?'Complete the current provider step below.':'',timeoutTitle:'Account sign-in expired',timeoutDescription:'Inspect account status and refresh model settings before another attempt.',close:'Close',cancel:'Cancel',addApiKey:'Close',waiting:'Waiting for provider',retry:'Sign in'};
 const start=async()=>{const id=crypto.randomUUID();setRequestId(id);await scope.start(provider,id);};
 return <SignInDialog account={account} retryDisabled={uncertain} colorScheme={document.documentElement.dataset.theme==='dark'?'dark':'light'} start={start} cancel={id=>scope.cancel(id)} close={close} useApiKey={close} t={key=>copy[key]??key}>
  {interaction?.message&&<p className={css.description}>{interaction.message}</p>}
  {interaction?.authorizationUrl&&<p className={css.description}><a className={css.link} href={interaction.authorizationUrl} target="_blank" rel="noopener noreferrer">Open sign-in page</a></p>}
  {interaction?.deviceCode&&<p className={css.description}>Device code: <strong>{interaction.deviceCode}</strong>{interaction.verificationUri&&<> · <a className={css.link} href={interaction.verificationUri} target="_blank" rel="noopener noreferrer">Open verification page</a></>}</p>}
  {interaction?.links?.map(link=><p className={css.description} key={link.url}><a className={css.link} href={link.url} target="_blank" rel="noopener noreferrer">{link.label??'Open provider information'}</a></p>)}
  {interaction?.prompt&&<AccountPrompt key={interaction.prompt.id} scope={scope} requestId={requestId} prompt={interaction.prompt}/>}
 </SignInDialog>;
}
