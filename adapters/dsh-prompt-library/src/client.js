import {registerImproveComposer} from './improve-composer.js';
// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// DSH's public settings.section slot and settings RPC are the only host seams.
window.__ModuleLoader__.load({
  id: 'dsh-prompt-library',
  factory(require) {
    const React = require('react'), h = React.createElement;
    const NS = 'prompt-library';
    function apply(ctx) {
      registerImproveComposer(ctx,React);
      const service=async(action,params={})=>{
        const response=await fetch('/api/augmentor-prompts',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({action,...params})});
        const result=await response.json();if(!result.ok)throw new Error(result.error);return result.library;
      };
      const unwrap = response => {
        if (!response?.result?.ok) throw new Error(response?.result?.error?.message || 'DSH could not load the prompt library.');
        return response.result.value;
      };
      function ImprovementPage() {
        const [current,setCurrent]=React.useState(null),[text,setText]=React.useState(''),[note,setNote]=React.useState('Loading instructions…'),[busy,setBusy]=React.useState(false);
        const alive=React.useRef(true);
        const load=async()=>{setBusy(true);try{const value=(await service('list')).improvement;if(!value)throw Error('Restart the prompt service to load these settings.');if(alive.current){setCurrent(value);setText(value.content);setNote('Changes take effect after saving.')}}catch(e){if(alive.current)setNote(e.message)}finally{if(alive.current)setBusy(false)}};
        React.useEffect(()=>{alive.current=true;load();return()=>{alive.current=false}},[]);
        const save=async()=>{if(!current||busy)return;setBusy(true);try{const result=await service('improvement.save',{content:text,expectedRevision:current.revision});if(alive.current){setCurrent(result.improvement);setNote('Instructions saved.')}}catch(e){if(alive.current)setNote(e.message)}finally{if(alive.current)setBusy(false)}};
        return h('div',null,h('p',null,'Instructions for ✦ Improve prompt in the input box. These are separate from saved /prompts.'),
          h('textarea',{'aria-label':'Prompt improvement instructions',rows:14,maxLength:8000,disabled:busy||!current,value:text,onChange:e=>setText(e.target.value)}),
          h('div',{className:'pl-bar'},
            h('button',{type:'button',disabled:busy||!current,onClick:save},'Save instructions'),
            h('button',{type:'button',disabled:busy,onClick:load},'Reload'),
            h('button',{type:'button',disabled:busy||!current,onClick:()=>{setText(current.defaultContent);setNote('Default loaded. Save to apply it.')}},'Use default')),
          h('p',{role:'status'},note));
      }
      function LibraryPage() {
        const [section,setSection]=React.useState('saved');
        const [library, setLibrary] = React.useState(null);
        const [form, setForm] = React.useState({id: null, name: '', content: ''});
        const [editing, setEditing] = React.useState(false);
        const [dirty, setDirty] = React.useState(false);
        const textRef=React.useRef(null);
        const [query, setQuery] = React.useState('');
        const [status, setStatus] = React.useState('Loading prompts…');
        const [busy, setBusy] = React.useState(false);
        const alive = React.useRef(true), busyRef = React.useRef(false), formRef = React.useRef(form), editingRef = React.useRef(false);
        formRef.current = form; editingRef.current = editing;
        const load = async (syncForm = true) => {
          const result=await service('list');
          const next={revision:result.revision,value:result};
          if (!next) throw new Error('The Prompt library plugin is not running.');
          if (alive.current) {
            setLibrary(next);
            if (syncForm && !editingRef.current && formRef.current.id) setForm(next.value.prompts.find(p => p.id === formRef.current.id) || {id: null, name: '', content: ''});
          }
          return next;
        };
        React.useEffect(() => {
          alive.current = true;
          load().then(() => { if (alive.current) setStatus(''); }, error => { if (alive.current) setStatus(error.message); });
          const timer=setInterval(()=>{if(!busyRef.current)load(!editingRef.current).catch(error=>{if(alive.current)setStatus(error.message);});},1500);
          return ()=>{alive.current=false;clearInterval(timer);};
        }, []);
        const select = item => {
          if (dirty && !window.confirm('Discard your unsaved prompt changes?')) return;
          setForm(item || {id: null, name: '', content: ''}); setEditing(!item); setDirty(false); setStatus('');
        };
        const cancelEdit = () => {
          setForm(library?.value.prompts.find(p => p.id === form.id) || {id: null, name: '', content: ''});
          setEditing(false); setDirty(false); setStatus('');
        };
        const edit = (key, value) => { setForm(prev => ({...prev, [key]: value})); setDirty(true); };
        const save = async remove => {
          if (!library || busyRef.current) return;
          if (remove && !window.confirm('Delete /' + form.name + '?')) return;
          busyRef.current = true; setBusy(true);
          try {
            const item={id:form.id,name:form.name.trim().replace(/^\//,''),content:form.content,expectedRevision:form.revision};
            const result=await service(remove?'delete':'save',item);
            const committed=result.prompts.find(p=>p.id===form.id||p.name===item.name);
            await load();
            if (!alive.current) return;
            setForm(remove ? {id: null, name: '', content: ''} : committed); setEditing(false); setDirty(false);
            setStatus(remove ? 'Prompt deleted.' : 'Saved. Type /' + item.name + ' in either Augmentor app.');
          } catch (error) { if (alive.current) setStatus(error.message); }
          finally { busyRef.current = false; if (alive.current) setBusy(false); }
        };
        const prompts = library?.value.prompts || [];
        const matches = prompts.filter(p => p.name.includes(query.toLowerCase().replace(/^\//, ''))).sort((a,b) => a.name.localeCompare(b.name));
        return h('section', {className: 'dsh-prompt-library', 'aria-label': 'Prompt library'},
          h('style', null, `.dsh-prompt-library{max-width:760px;padding:8px 4px 24px;font:14px/1.5 inherit}.dsh-prompt-library h2{margin:0 0 8px;font-size:21px}.dsh-prompt-library p{opacity:.8}.dsh-prompt-library input,.dsh-prompt-library textarea{display:block;width:100%;box-sizing:border-box;color:inherit;background:rgba(128,128,128,.08);border:1px solid rgba(128,128,128,.35);border-radius:10px;padding:10px 12px;font:inherit}.dsh-prompt-library textarea{resize:vertical;min-height:170px}.dsh-prompt-library label{display:block;margin:16px 0 0}.dsh-prompt-library button{font:inherit;color:inherit;background:rgba(128,128,128,.1);border:1px solid rgba(128,128,128,.3);border-radius:9px;padding:7px 12px;cursor:pointer}.dsh-prompt-library button:hover{background:rgba(128,128,128,.23)}.dsh-prompt-library button:disabled{opacity:.4;cursor:default}.dsh-prompt-library .pl-bar{display:flex;gap:8px;margin:14px 0;flex-wrap:wrap}.dsh-prompt-library .pl-list{display:flex;flex-direction:column;gap:5px;max-height:185px;overflow:auto;margin:12px 0}.dsh-prompt-library .pl-list button{text-align:left}.dsh-prompt-library button[aria-pressed=true]{border-color:#62b4a0;background:rgba(98,180,160,.14)}.dsh-prompt-library .pl-status{min-height:24px;overflow-wrap:anywhere}`),
          h('style', null, `.dsh-prompt-library .pl-preview{white-space:pre-wrap;overflow-wrap:anywhere;max-height:300px;overflow:auto;padding:16px;border-radius:12px;background:rgba(128,128,128,.08);border:1px solid rgba(128,128,128,.25);line-height:1.6}.dsh-prompt-library h3{font-size:16px;margin:20px 0 10px}.dsh-prompt-library .pl-list button small{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;opacity:.65;font-size:12px;margin-top:2px}`),
          h('h2', null, 'Prompt library'),
          h('div',{className:'pl-bar'},h('button',{type:'button','aria-pressed':section==='saved',onClick:()=>setSection('saved')},'Saved prompts'),h('button',{type:'button','aria-pressed':section==='improve',onClick:()=>setSection('improve')},'Improve prompt')),
          h('div',{hidden:section!=='improve'},h(ImprovementPage)),
          h('div',{hidden:section!=='saved'},
          h('p', null, 'Shared across Augmentor interfaces and harnesses. Click a prompt to preview it, or type / in chat to insert it into your draft.'),
          h('input', {'aria-label': 'Search saved prompts', placeholder: 'Search prompts…', value: query, onChange: e => setQuery(e.target.value)}),
          h('div', {className: 'pl-bar'},
            h('button', {type: 'button', disabled: busy, onClick: () => select(null)}, 'New prompt'),
            h('button', {type: 'button', disabled: busy, onClick: () => load(false).then(() => setStatus(editing ? 'Library refreshed. Your draft is kept.' : 'Library refreshed.'), e => setStatus(e.message))}, 'Refresh')),
          h('div', {className: 'pl-list'}, matches.map(p => h('button', {key: p.id, type: 'button', disabled: busy, 'aria-label': '/' + p.name, 'aria-pressed': p.id === form.id, onClick: () => select(p)}, '/' + p.name, h('small', {'aria-hidden': true}, p.content.replace(/\s+/g, ' ').slice(0, 100))))),
          library && !prompts.length && !editing && h('p', null, 'Your library is empty. Choose New prompt to get started.'),
          prompts.length > 0 && !matches.length && h('p', null, 'No matching prompts.'),
          !editing && !form.id && prompts.length > 0 && h('p', null, 'Select a prompt above to preview it.'),
          !editing && form.id && h(React.Fragment, null,
            h('h3', null, '/' + form.name),
            h('div', {className: 'pl-preview', role: 'region', 'aria-label': 'Prompt preview'}, form.content),
            h('div', {className: 'pl-bar'},
              h('button', {type: 'button', disabled: !library || busy, onClick: () => { setEditing(true); setStatus(''); }}, 'Edit'),
              h('button', {type: 'button', disabled: !library || busy, onClick: () => save(true)}, 'Delete prompt'))),
          editing && h(React.Fragment, null,
            h('h3', null, form.id ? 'Edit prompt' : 'New prompt'),
            h('label', null, 'Shortcut name', h('input', {'aria-label': 'Prompt shortcut name', placeholder: 'For example: summarise', maxLength: 128, disabled: busy, value: form.name, onChange: e => edit('name', e.target.value)})),
            h('label', null, 'Prompt text', h('textarea', {ref:textRef,'aria-label': 'Saved prompt text', rows: 7, maxLength: 32000, disabled: busy, value: form.content, onChange: e => edit('content', e.target.value)})),
            h('div', {className: 'pl-bar'},
              h('button',{type:'button',disabled:busy,onClick:()=>{const t=textRef.current;const start=t.selectionStart,end=t.selectionEnd;edit('content',form.content.slice(0,start)+'[clipboard]'+form.content.slice(end));requestAnimationFrame(()=>{t.focus();t.setSelectionRange(start+11,start+11);});}},'Insert clipboard'),
              h('button', {type: 'button', disabled: !library || busy || !form.name.trim() || !form.content.trim(), onClick: () => save(false)}, busy ? 'Saving…' : 'Save prompt'),
              h('button', {type: 'button', disabled: busy, onClick: cancelEdit}, 'Cancel'))),
          h('p', {role: 'status', className: 'pl-status'}, status),
          h('p', null, 'Stored in the shared Augmentor library. This library does not send prompts to a model.')));
      }
      ctx.slots.inject('settings.section', () => ctx.slots.register({name: 'settings.section', id: NS, order: 95, label: () => 'Prompt library'}, LibraryPage));
    }
    return {name: 'dsh-prompt-library', inject: ['slots', 'connection', 'remote'], apply};
  }
});
