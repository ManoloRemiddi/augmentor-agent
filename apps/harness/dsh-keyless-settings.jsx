// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useState} from 'react';
import {SettingsForm,SettingsValueField,DisclosureRow,Button} from '@deepseek-ai/dsh-client-ui-primitives';
import {DeveloperToolsRow} from '@dsh-gui/ui-settings-general/src/client/DeveloperToolsRow.tsx';
import {KEYLESS_CHOICES} from './dsh-keyless-form.mjs';
/** Existing DSH form, field, disclosure and switch bodies; no new layout/CSS. */
export function KeylessSettings({scope,state:s}){
 const [advanced,setAdvanced]=useState(false),d=s.keylessDraft;let invalid=false,problem='';try{scope.proposedKeyless();}catch(e){invalid=true;problem=e.message;}
 const field=(name,label,hint,numeric=false)=><SettingsValueField key={name} id={'augmentor-keyless-'+name} label={label} hint={hint} text={d?.[name]??''} numeric={numeric} overridden={false} invalid={false} overriddenLabel="Configured" resetLabel="Reset" invalidLabel="Check this value" disabled={!s.writable||s.busy} onEdit={value=>scope.editKeyless(name,value)} onReset={()=>{}}/>;
 const t=key=>({'developerTools.title':'Fetch public pages','developerTools.description':'Read page content without API keys or browser cookies.','developerTools.error':'The fetch preference could not be staged.'}[key]??key);
 return <div aria-label="Keyless engine settings"><SettingsForm labels={{unavailable:'Connect to edit keyless search settings.',readOnly:s.busy?'Loading Search settings…':'Refresh to confirm Search settings before saving.',saveFailed:'The save was not confirmed. Refresh to inspect the stored settings.',save:'Save keyless settings',saving:'Saving keyless settings…'}} state={{available:s.status!=='unavailable'&&scope.modes(),writable:s.writable,dirty:scope.keylessDirty(),invalid:invalid||!s.writable,saving:s.busy,failed:!!s.error}} onSave={()=>void scope.saveKeyless()} onDiscard={()=>{}}>
 {KEYLESS_CHOICES.map(([key,label])=>field('order_'+key,label+' position','Lower numbers run first. Use 1–5; leave blank to disable.',true))}
 {field('maxResults','Maximum search results','From 1 to 20 sources per query.',true)}
 <DeveloperToolsRow t={t} useDeveloperTools={select=>select(d?.enableFetch??true)} setEnabled={async enabled=>scope.editKeyless('enableFetch',enabled)} disabled={!s.writable||s.busy}/>
 <DisclosureRow icon={null} title="Advanced keyless settings" open={advanced} expandable onToggle={()=>setAdvanced(!advanced)}>
 {field('region','Search region','DuckDuckGo region, such as wt-wt or it-it.')}
 {field('lang','Search language','en, zh, ru, ja, de, fr, es or ko.')}
 {field('timeoutSeconds','Search timeout (seconds)','From 0.1 to 30 seconds per engine request.')}
 {field('searxngInstances','SearXNG instances','Public base URLs separated by commas. Leave empty to make no SearXNG requests.')}
 {field('blockedDomains','Blocked source domains','Domain names separated by commas.')}
 {field('fetchMB','Maximum page download (MB)','Up to 10 MB of downloaded page data.')}
 {field('fetchChars','Maximum page characters','Up to 1,000,000 characters; larger bodies are visibly truncated.',true)}
 {field('fetchSeconds','Page timeout (seconds)','From 0.1 to 30 seconds.')}
 {field('fetchRedirects','Maximum page redirects','From 0 to 10. Each destination must be public.',true)}
 {field('fetchAgent','Page request user agent','The identity sent to page servers.')}
 </DisclosureRow>
 {problem&&s.keylessDraft&&<p role="alert">{problem}</p>}
 </SettingsForm><Button disabled={!s.writable||s.busy||!scope.keylessDirty()} onClick={()=>scope.discardKeyless()}>Discard keyless changes</Button><Button disabled={!s.writable||s.busy} onClick={()=>void scope.clearKeyless()}>Reset keyless defaults</Button></div>;
}
