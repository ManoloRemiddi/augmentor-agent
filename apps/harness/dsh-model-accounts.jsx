// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Pi credential metadata and supported logout, using original DSH cards/dialog/CSS.
import React,{useState,useSyncExternalStore} from 'react';
import {SignOutDialog} from '@dsh-gui/ui-settings-account/src/client/SignOutDialog.tsx';
import css from '@dsh-gui/ui-settings-models/src/client/ModelsSection.module.css';

export function DshModelAccounts({scope}){
 const state=useSyncExternalStore(scope.subscribe,scope.getSnapshot),[target,setTarget]=useState(null);
 if(state.status!=='ready'||!state.writable||scope.controller.state.capabilities?.modelAccountLogout!==true)return null;
 const account=state.accounts.find(row=>row.provider===target);
 const copy={signOut:'Sign out '+target+'?',close:'Close',cancel:'Cancel',failed:'Sign-out could not be confirmed. Refresh model settings before trying again.',signOutDescription:'Remove the OAuth credential currently stored in this Pi profile for '+target+'. Provider settings, profile API keys and environment credentials are kept. This signs out locally; it does not revoke access at the provider.'};
 return <section className={css.section} aria-label="Stored Pi accounts">
  <h3 className={css.title}>Stored Pi accounts</h3>
  <p className={css.intro}>OAuth credentials in this Pi profile. Account identity and tokens stay private. Pause queued prompts and goals before signing out.</p>
  {state.accounts.length===0?<p className={css.intro}>No stored OAuth accounts.</p>:<ul className={css.rows}>{state.accounts.map(row=><li key={row.provider} className={css.rowCard}>
   <div className={css.rowHead}><span className={css.rowIdentity}><span className={css.rowName}>{row.provider}</span><span className={css.rowTag}>OAuth stored</span></span>
    <button type="button" className={css.secondaryButton} aria-label={'Sign out '+row.provider} disabled={!row.registered} onClick={()=>setTarget(row.provider)}>Sign out</button></div>
   {!row.registered&&<p className={css.notice}>Register this provider in Pi before managing its stored account.</p>}
  </li>)}</ul>}
  {account&&<SignOutDialog running={false} close={()=>setTarget(null)} signOut={()=>scope.logoutAccount(account.provider)} t={key=>copy[key]??key}/>}
 </section>;
}
