// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
export function homeSettings(document,send,parent){
 const make=(tag,text='')=>{const e=document.createElement(tag);e.textContent=text;return e;};
 const form=make('form'),status=make('p');status.setAttribute('role','status');const fields={};
 form.append(make('p','Pair this Augmentor with your NAS once, then request Home work in your existing conversations.'));
 for(const [name,label,value] of [['url','Home HTTPS URL',''],['name','Device name','Augmentor browser'],['code','One-time pairing code','']]){const l=make('label',label),input=make('input');input.name=name;input.value=value;input.required=true;input.type=name==='code'?'password':'text';l.append(input);form.append(l);fields[name]=input;}
 const connect=make('button','Connect');connect.type='submit';const disconnect=make('button','Disconnect');disconnect.type='button';form.append(connect,disconnect,status);parent.append(form);
 async function run(action,params={}){connect.disabled=true;disconnect.disabled=true;try{const r=await send('homeConnection',{request:{action,...params}});if(!r?.ok)throw Error(r?.error??'Home connection unavailable');status.textContent=r.connected?'Connected. Ask Augmentor about your home.':'Not connected.';connect.disabled=!!r.connected;disconnect.disabled=!r.connected;if(r.url)fields.url.value=r.url;}catch(e){status.textContent=e.message;connect.disabled=false;disconnect.disabled=false;}}
 form.onsubmit=e=>{e.preventDefault();const values=Object.fromEntries(Object.entries(fields).map(([k,v])=>[k,v.value.trim()]));fields.code.value='';void run('pair',values);};disconnect.onclick=()=>run('disconnect');void run('state');
}
