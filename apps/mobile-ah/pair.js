// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
const form=document.querySelector('form'),status=document.querySelector('[role=status]');
form.addEventListener('submit',async event=>{event.preventDefault();const button=form.querySelector('button');button.disabled=true;try{const response=await fetch('/mobile/pair',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:form.elements.key.value})}),body=await response.json();if(!response.ok)throw Error(body.error?.message||'Pairing failed.');form.reset();location.replace('/agent'+location.hash);}catch(error){status.textContent=error.message;}finally{button.disabled=false;}});
// Android external-link navigation may omit a Strict cookie on its first GET.
// Recheck it from this same-origin page before asking an already paired user.
void fetch('/api/access').then(r=>{if(r.ok)location.replace('/agent'+location.hash);}).catch(()=>{});
