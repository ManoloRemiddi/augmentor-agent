// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Pi credential metadata and supported logout, using original DSH cards/dialog/CSS.
import React,{useState,useSyncExternalStore,useMemo,useEffect} from 'react';
import {SignOutDialog} from '@dsh-gui/ui-settings-account/src/client/SignOutDialog.tsx';
import css from '@dsh-gui/ui-settings-models/src/client/ModelsSection.module.css';
import {DshAccountScope} from './dsh-account-scope.mjs';
import {DshAccountDialog} from './dsh-account-dialog.jsx';

export function DshModelAccounts({scope}){
 const state=useSyncExternalStore(scope.subscribe,scope.getSnapshot),[target,setTarget]=useState(null),[signIn,setSignIn]=useState(null),[provider,setProvider]=useState('');
 const login=useMemo(()=>new DshAccountScope(scope),[scope]),auth=useSyncExternalStore(login.subscribe,login.getSnapshot);
 useEffect(()=>{void login.load();return()=>login.close();},[login]);
 if(!scope.current()||scope.controller.state.capabilities?.modelAccountLogout!==true)return null;
 const loginSupported=scope.controller.state.capabilities?.modelAccountLogin===true;
 const editable=state.status==='ready'&&state.writable&&scope.accepted&&(!loginSupported||auth.available&&!auth.busy&&!auth.needsRefresh);
 const selected=auth.providers.some(row=>row.provider===provider)?provider:auth.providers[0]?.provider||'';
 const account=state.accounts.find(row=>row.provider===target);
 const copy={signOut:'Sign out '+target+'?',close:'Close',cancel:'Cancel',failed:'Sign-out could not be confirmed. Refresh model settings before trying again.',signOutDescription:'Remove the OAuth credential currently stored in this Pi profile for '+target+'. Provider settings, profile API keys and environment credentials are kept. This signs out locally; it does not revoke access at the provider.'};
 return <section className={css.section} aria-label="Stored Pi accounts">
  <h3 className={css.title}>Stored Pi accounts</h3>
  <p className={css.intro}>OAuth credentials in this Pi profile. Account identity and tokens stay private. Pause queued prompts and goals before signing out.</p>
  {state.status!=='ready'||!state.writable?<p className={css.intro}>Refresh model settings to confirm stored accounts after the current action settles.</p>:state.accounts.length===0?<p className={css.intro}>No stored OAuth accounts.</p>:<ul className={css.rows}>{state.accounts.map(row=><li key={row.provider} className={css.rowCard}>
   <div className={css.rowHead}><span className={css.rowIdentity}><span className={css.rowName}>{row.provider}</span><span className={css.rowTag}>OAuth stored</span></span>
    <button type="button" className={css.secondaryButton} aria-label={'Sign out '+row.provider} disabled={!row.registered||!editable} onClick={()=>setTarget(row.provider)}>Sign out</button></div>
   {!row.registered&&<p className={css.notice}>Register this provider in Pi before managing its stored account.</p>}
  </li>)}</ul>}
  {loginSupported&&<>
   <label className={css.field}><span className={css.fieldLabel}>Account provider</span><select className={css.input} aria-label="Account provider" value={selected} disabled={!editable} onChange={event=>setProvider(event.target.value)}>{auth.providers.map(row=><option key={row.provider} value={row.provider}>{row.name||row.provider}</option>)}</select></label>
   <div className={css.rowActions}><button type="button" className={css.secondaryButton} aria-label={'Sign in with '+selected} disabled={!editable||!selected} onClick={()=>setSignIn(selected)}>Sign in</button><button type="button" className={css.secondaryButton} onClick={()=>void login.load()}>Refresh account status</button></div>
   {auth.busy&&<p className={css.notice} role="status">{auth.receipt?.state==='cancel-requested'?'Waiting for Pi to settle account cancellation.':'Account sign-in is active for '+auth.receipt?.provider+'.'} {auth.receipt?.state==='running'&&<button type="button" className={css.secondaryButton} onClick={()=>setSignIn(auth.receipt.provider)}>Continue sign-in</button>} {auth.receipt?.requestId&&<button type="button" className={css.secondaryButton} onClick={()=>void login.cancel(auth.receipt.requestId).catch(()=>{})}>Cancel sign-in</button>}</p>}
   {auth.needsRefresh&&!auth.busy&&<p className={css.notice}>Inspect the account result, then use Refresh model settings before starting work or another sign-in.</p>}
   {auth.error&&<p className={css.error} role="alert">{auth.error}</p>}
   {auth.receipt&&!auth.busy&&<p className={css.intro}>Last sign-in for {auth.receipt.provider}: {auth.receipt.state==='completed'?'Pi stored the account credential.':auth.receipt.state==='cancelled'?'Cancellation settled; inspect the stored account before continuing.':auth.receipt.state==='interrupted'?'Pi stopped before the sign-in outcome was confirmed.':'Sign-in needs review before continuing.'}</p>}
   {signIn&&<DshAccountDialog scope={login} provider={signIn} close={()=>setSignIn(null)}/>}
  </>}
  {account&&editable&&<SignOutDialog running={false} close={()=>setTarget(null)} signOut={()=>scope.logoutAccount(account.provider)} t={key=>copy[key]??key}/>}
 </section>;
}
