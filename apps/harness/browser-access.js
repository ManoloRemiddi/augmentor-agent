// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Remember only a server-confirmed operator credential. Inspector authority
// remains tab-scoped and never falls back to a more privileged credential.
const tabKey='augmentor-harness-token',browserKey='augmentor-harness-operator-token';
const read=(store,key)=>{try{return store?.getItem(key)||null;}catch{return null;}};
const write=(store,key,value)=>{try{store?.setItem(key,value);}catch{/* Private/storage-disabled browsing still accepts a direct link. */}};
export function browserAccess(hash,tab,browser){
 const token=hash.has('token')?hash.get('token'):read(tab,tabKey)||read(browser,browserKey);
 if(token)write(tab,tabKey,token);
 return {token,confirm(access){if(token&&access?.mode==='operator')write(browser,browserKey,token);}};
}
