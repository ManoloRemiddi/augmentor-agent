// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Independently authored SDK OAuth provider. No external provider or owner credentials.
import {existsSync,readFileSync,appendFileSync} from 'node:fs';
import {join} from 'node:path';import {randomUUID} from 'node:crypto';import {setTimeout as delay} from 'node:timers/promises';
export default function register(pi,{root,authorizeUrl}){
 const audit=phase=>appendFileSync(join(root,'account-login-audit.jsonl'),JSON.stringify({phase})+'\n',{mode:0o600});
 pi.registerProvider({id:'authored-login',name:'Authored OAuth fixture',getModels:()=>[],refreshModels:async()=>{if(existsSync(join(root,'account-login-fail-refresh')))throw Error('AUTHORED_PRIVATE_REFRESH_BODY_WITH_TOKEN');},auth:{oauth:{name:'Authored OAuth fixture',
  async login(interaction,options){
   audit('login-start');if(options.agentName!=='Augmentor Harness')throw Error('Incorrect authored app identity');const installation=options.getDeviceId();if(installation!==options.getDeviceId())throw Error('Unstable authored installation ID');
   const method=await interaction.prompt({type:'select',message:'Fixture account method',options:[{id:'manual',label:'Manual fixture'},{id:'callback',label:'Callback fixture'},{id:'failure',label:'Failure fixture'}]});
   if(method==='failure')throw Error('AUTHORED_PRIVATE_LOGIN_BODY_WITH_TOKEN');
   const nonce=randomUUID(),url=new URL(authorizeUrl);url.searchParams.set('state',nonce);interaction.notify({type:'auth_url',url:url.href,instructions:'Authored account authorization only.'});interaction.notify({type:'device_code',userCode:'FIXTURE-DEVICE-CODE',verificationUri:url.href});
   if(method==='manual'){
    for(const [type,message,expected] of [['secret','Fixture account secret','fixture-secret'],['text','Fixture account label','fixture label'],['manual_code','Fixture callback code','fixture-code']]){
     const value=await interaction.prompt({type,message,placeholder:'Authored fixture input'});if(value!==expected)throw Error('AUTHORED_PRIVATE_INVALID_INPUT');audit('answered-'+type);
    }
   }else{
    const local=new AbortController(),signal=AbortSignal.any([interaction.signal,local.signal]);
    const manual=interaction.prompt({type:'manual_code',message:'Fixture callback or manual code',signal:local.signal}).then(value=>({manual:value}));
    const callback=(async()=>{while(!signal.aborted){const file=join(root,'account-login-callback.json');if(existsSync(file)){const row=JSON.parse(readFileSync(file,'utf8'));if(row.nonce===nonce)return {callback:row.code};}await delay(20,undefined,{signal});}throw Error('Authored callback cancelled');})();
    try{const result=await Promise.race([manual,callback]);if(result.manual!==undefined&&result.manual!=='fixture-code'||result.callback!==undefined&&result.callback!=='fixture-code')throw Error('Authored callback mismatch');audit('callback-finished');}finally{local.abort();}
   }
   interaction.notify({type:'progress',message:'Authored account exchange finished.'});audit('login-return');
   return {type:'oauth',access:'AUTHORED_LOGIN_ACCESS',refresh:'AUTHORED_LOGIN_REFRESH',expires:4102444800000};
  },refresh:async()=>{throw Error('No authored account refresh expected');},toAuth:async credential=>({apiKey:credential.access})}}});
}
