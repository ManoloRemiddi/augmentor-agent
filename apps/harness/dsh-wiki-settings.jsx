// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useEffect,useMemo,useSyncExternalStore} from 'react';
import {SettingsForm,SettingsValueField,Button} from '@deepseek-ai/dsh-client-ui-primitives';
import {DeveloperToolsRow} from '@dsh-gui/ui-settings-general/src/client/DeveloperToolsRow.tsx';
import {DshWikiProfile} from './dsh-wiki-profile.mjs';
/** Original supplier form/control chrome; only the Pi settings owner is adapted. */
export function WikiSettings({controller}){
 const profile=useMemo(()=>new DshWikiProfile(controller),[controller]);useEffect(()=>()=>profile.close(),[profile]);
 const s=useSyncExternalStore(profile.subscribe,profile.getSnapshot),d=s.draft;let invalid=false;try{profile.proposed();}catch{invalid=true;}
 const t=key=>({'developerTools.title':'Wiki tools and skills','developerTools.description':'Six original Wiki tools and nine skills for Native conversations. Changes apply when saved; the vault is never created by Settings.','developerTools.error':'The change could not be staged.'}[key]??key);
 const field=(name,label,hint,numeric=false)=><SettingsValueField key={name} id={'augmentor-wiki-'+name} label={label} hint={hint} text={d?.[name]??''} numeric={numeric} overridden={false} invalid={false} overriddenLabel="Configured" resetLabel="Reset" invalidLabel="Check this value" disabled={!s.writable||s.busy} onEdit={value=>profile.edit(name,value)} onReset={()=>{}}/>;
 return <div aria-label="Wiki settings"><SettingsForm labels={{unavailable:'Wiki settings require a connected Linux operator view.',readOnly:s.busy?'Loading Wiki settings…':'Refresh to confirm Wiki settings before saving.',saveFailed:'The save was not confirmed. Inspect the stored profile before trying again.',save:'Save Wiki settings',saving:'Applying Wiki settings…'}} state={{available:s.available,writable:s.writable,dirty:profile.dirty(),invalid:invalid||!s.writable,saving:s.busy,failed:!!s.error}} onSave={()=>void profile.apply().catch(()=>{})} onDiscard={()=>{}}>
 <DeveloperToolsRow t={t} useDeveloperTools={select=>select(d?.enabled??false)} setEnabled={async enabled=>profile.edit('enabled',enabled)} disabled={!s.writable||s.busy}/>
 {field('vaultPath','Wiki vault path','Choose an absolute path to your vault. Existing data stays in place.')}
 {field('maxQueryResults','Maximum query results','From 1 to 100 pages per standard query.',true)}
 {field('typeFolders','Page type folders','JSON mapping, for example {"concept":"wiki/concepts"}. Leave {} for the original routing.')}
 {s.accepted&&<p role="status">{s.accepted.pending?'Stored profile awaiting application.':s.accepted.value.enabled?'Wiki enabled.':'Wiki disabled.'} Applied to {s.accepted.appliedSessions} of {s.accepted.loadedSessions} loaded Native conversations.</p>}
 </SettingsForm>{s.error&&<p role="alert">{s.error}</p>}<Button disabled={!profile.current()||s.busy} onClick={()=>void profile.load()}>Refresh Wiki settings</Button>{s.accepted?.pending&&<Button disabled={!s.writable||s.busy||profile.dirty()} onClick={()=>void profile.apply(true).catch(()=>{})}>Apply stored Wiki settings</Button>}</div>;
}
