// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash,randomInt,randomUUID} from 'node:crypto';
import {existsSync,readFileSync,mkdtempSync,rmSync} from 'node:fs';
import {join,dirname} from 'node:path';
import {ModelRuntime} from '@earendil-works/pi-coding-agent';
import {InMemoryCredentialStore} from '@earendil-works/pi-ai';
import {atomicJson} from './storage.js';
import {type Data} from '../../protocol/src/index.js';
import {discoverModels as discoverEndpoint} from '../vendor/dsh-model-discovery/discovery.js';

export const MODEL_APIS=['openai-completions','openai-responses','anthropic-messages','mistral-conversations','azure-openai-responses','openai-codex-responses','bedrock-converse-stream','google-generative-ai','google-vertex','pi-messages'];
const NS='llm-pi-ai',FIELDS=['displayName','baseURL','api','models','apiKeyEnv'],MODEL_FIELDS=['id','name','contextWindow','maxTokens','input','reasoning'];
const own=(value:Data,key:string)=>Object.hasOwn(value,key);
const object=(value:unknown):value is Data=>!!value&&typeof value==='object'&&!Array.isArray(value);
const digest=(raw:string)=>createHash('sha256').update(raw).digest('hex');
const ref=(provider:string)=>provider.toUpperCase().replace(/[^A-Z0-9]+/g,'_')+'_API_KEY';
const literal=(value:string)=>value.replaceAll('$',()=>'$$').replace(/^!/,()=>'$!');
const expression=(value:unknown)=>typeof value==='string'&&(value.startsWith('!')||/\$(?:\{|[A-Za-z_])/.test(value.replaceAll('$$','').replaceAll('$!','')));
const command=(value:unknown)=>typeof value==='string'&&value.startsWith('!');
function endpoint(value:unknown){
  if(typeof value!=='string'||value.length>2048)throw Error('Enter a model endpoint URL.');
  let url;try{url=new URL(value);}catch{throw Error('Enter a valid model endpoint URL.');}
  if(!['https:','http:'].includes(url.protocol)||url.username||url.password||url.search||url.hash||url.protocol==='http:'&&!['localhost','127.0.0.1','[::1]'].includes(url.hostname))throw Error('Use HTTPS, or a loopback HTTP endpoint, without credentials, queries or fragments.');
  return value;
}

/** Private minimal storage adapter for the original DSH Models forms.
 * Descriptors contain curated fields and opaque model identities, never keys,
 * headers, compatibility options or command/environment expressions. */
export class ModelSettings {
  private hash='';private revision=randomInt(2**32,2**48);private tokens=new Map<string,{provider:string;index:number;hash:string}>();private tokenAt=new Map<string,string>();
  private defaults=ModelRuntime.create({modelsPath:null,credentials:new InMemoryCredentialStore(),refreshOnCreate:false,allowModelNetwork:false});
  private probes=new Set<AbortController>();private appliedHash='';
  private async oauthAccounts(signal?:AbortSignal){try{return new Set((await this.runtime().listCredentials({signal})).filter(credential=>credential.type==='oauth').map(credential=>credential.providerId));}catch{throw Error('Pi credential metadata is unavailable.');}}
  // The execution owner calls markApplied after runtime/session reconciliation;
  // persistence alone must never attest the current credential snapshot.
  constructor(private file:string,private runtime:()=>ModelRuntime,private guard:()=>void,private apply:(config:Data,validated:ModelRuntime,deferred:ReadonlySet<string>)=>Promise<void>){this.markApplied();}
  private fileHash(){return digest(existsSync(this.file)?readFileSync(this.file,'utf8'):JSON.stringify({providers:{}}));}
  get fingerprint(){return this.fileHash();}
  get applied(){return this.appliedHash===this.fileHash();}
  markApplied(expected=this.fileHash()){if(this.fileHash()!==expected)throw Error('The model profile changed during application.');this.appliedHash=expected;}
  get activeDiscoveries(){return this.probes.size;}
  cancelDiscoveries(){for(const probe of this.probes)probe.abort();}
  private read(){
    const raw=existsSync(this.file)?readFileSync(this.file,'utf8'):JSON.stringify({providers:{}});
    if(Buffer.byteLength(raw)>4*1024*1024)throw Error('The model configuration exceeds the editor limit.');
    const hash=digest(raw);if(hash!==this.hash){this.hash=hash;this.revision++;this.tokens.clear();this.tokenAt.clear();}
    let config;try{config=JSON.parse(raw);}catch{throw Error('Repair the model configuration JSON before opening Models.');}
    if(!object(config)||!object(config.providers))throw Error('Repair the providers object before opening Models.');
    const profiles=Object.values(config.providers);if(profiles.length>128||profiles.reduce<number>((sum,profile:any)=>sum+(Array.isArray(profile?.models)?profile.models.length:0),0)>4096||profiles.some((profile:any)=>Array.isArray(profile?.models)&&profile.models.length>512))throw Error('The model profile exceeds the bounded editor catalog limit.');
    return {config,hash};
  }
  private provider(value:unknown){if(typeof value!=='string'||!value||value.length>256||/[\x00-\x1f]/.test(value)||['__proto__','constructor','prototype'].includes(value))throw Error('Choose a valid provider.');return value;}
  private profile(provider:string,value:Data,hash:string){
    const projected:Data={};for(const [field,key] of [['name','displayName'],['baseUrl','baseURL'],['api','api']])if(own(value,field)){if(field==='baseUrl'){try{endpoint(value[field]);}catch{continue;}}projected[key]=value[field];}
    if(Array.isArray(value.models))projected.models=value.models.map((model:Data,index:number)=>{
      if(!object(model))throw Error('Repair the model rows before opening Models.');
      const identity=provider+'\0'+index;let token=this.tokenAt.get(identity);
      if(!token){token=randomUUID();this.tokens.set(token,{provider,index,hash});this.tokenAt.set(identity,token);}
      return {...Object.fromEntries(MODEL_FIELDS.filter(field=>own(model,field)).map(field=>[field,model[field]])),_augmentorModel:token};
    });
    return projected;
  }
  async describe(){
    const defaults=await this.defaults;
    const oauth=await this.oauthAccounts();
    const {config,hash}=this.read(),runtime=this.runtime(),user:Data={providers:Object.create(null)},base:Data={providers:Object.create(null)};
    const ids=new Set([...runtime.getProviders().map(p=>p.id),...Object.keys(config.providers)]);
    const rows=[];
    for(const id of ids){
      this.provider(id);const stored=config.providers[id],models=runtime.getModels(id),registered=runtime.getProvider(id);
      if(stored!==undefined&&!object(stored))throw Error('Repair a provider profile before opening Models.');
      if(stored)user.providers[id]=this.profile(id,stored,hash);
      if(defaults.getProvider(id))base.providers[id]={models:defaults.getModels(id).map(model=>Object.fromEntries(MODEL_FIELDS.filter(field=>field in model).map(field=>[field,(model as any)[field]])))};
      const status=runtime.getProviderAuthStatus(id),credential={configured:status.configured,writable:!expression(stored?.apiKey)&&!oauth.has(id)&&!runtime.isUsingOAuth(id),source:status.source??'none'};
      rows.push({entry:{provider:id,displayName:stored?.name??id,settingsNs:NS,settingsPath:['providers',id],active:models.length>0,declared:!defaults.getProvider(id)},configured:!!stored||status.configured,removable:!!stored,apiKeyEnv:undefined,credential,derivedCredential:credential});
    }
    const value={providers:Object.fromEntries([...ids].map(id=>[id,{...base.providers[id],...user.providers[id]}]))};
    const accounts=[...oauth].sort().map(provider=>({provider,registered:!!runtime.getProvider(provider)}));
    if(accounts.length>256)throw Error('The stored account list exceeds the editor limit.');
    return {writable:true,revision:this.revision,rows,accounts,namespaces:[{ns:NS,revision:this.revision,user,base,value,schema:{apis:MODEL_APIS}}]};
  }
  async requireOAuthAccount(value:unknown,revision:unknown){
    const provider=this.provider(value),oauth=await this.oauthAccounts();this.read();
    if(revision!==this.revision)throw Error('Model settings changed. Refresh before signing out.');
    if(!oauth.has(provider))throw Error('The stored OAuth account changed. Refresh before signing out.');
    if(!this.runtime().getProvider(provider))throw Error('Register this provider in Pi before managing its stored account.');
    return provider;
  }
  async credential(reference:unknown){
    const oauth=await this.oauthAccounts();
    this.read();const providers=new Set([...this.runtime().getProviders().map(p=>p.id),...Object.keys(this.read().config.providers)]);
    const matches=[...providers].filter(id=>ref(id)===reference);
    if(matches.length!==1)throw Error('This credential reference is missing or ambiguous.');
    const provider=matches[0],profile=this.read().config.providers[provider],status=this.runtime().getProviderAuthStatus(provider);
    return {provider,configured:status.configured,writable:!expression(profile?.apiKey)&&!oauth.has(provider)&&!this.runtime().isUsingOAuth(provider),source:status.source??'none'};
  }
  private models(provider:string,rows:unknown,current:Data,hash:string){
    if(!Array.isArray(rows)||rows.length>512)throw Error('Use a bounded model list.');
    const seen=new Set<string>(),used=new Set<string>();
    return rows.map(row=>{
      if(!object(row)||Object.keys(row).some(key=>!MODEL_FIELDS.includes(key)&&key!=='_augmentorModel'))throw Error('The editor cannot change hidden model fields.');
      if(typeof row.id!=='string'||!row.id.trim()||row.id!==row.id.trim()||row.id.length>512||seen.has(row.id))throw Error('Model IDs must be nonempty and unique.');seen.add(row.id);
      let prior:Data={};if(row._augmentorModel!==undefined){const token=this.tokens.get(row._augmentorModel);if(!token||token.provider!==provider||token.hash!==hash||used.has(row._augmentorModel))throw Error('Model identity changed. Close and reopen this card.');used.add(row._augmentorModel);prior=current.models?.[token.index];if(!object(prior))throw Error('Model identity is unavailable.');}
      const result={...prior};for(const field of MODEL_FIELDS){if(own(row,field))result[field]=row[field];else delete result[field];}
      if(result.name!==undefined&&(typeof result.name!=='string'||!result.name.trim()||result.name.length>512))throw Error('Enter a valid model name.');
      for(const field of ['contextWindow','maxTokens'])if(result[field]!==undefined&&(!Number.isSafeInteger(result[field])||result[field]<1||result[field]>10_000_000))throw Error('Enter valid model token limits.');
      if(result.maxTokens!==undefined&&result.contextWindow!==undefined&&result.maxTokens>result.contextWindow)throw Error('The response limit must fit inside the context window.');
      if(result.input!==undefined&&(!Array.isArray(result.input)||!result.input.length||result.input.some((x:unknown)=>!['text','image'].includes(x as string))||new Set(result.input).size!==result.input.length))throw Error('Choose supported model input types.');
      if(result.reasoning!==undefined&&typeof result.reasoning!=='boolean')throw Error('Choose a valid reasoning capability.');
      return result;
    });
  }
  async mutate(ops:unknown,expected:unknown){
    this.guard();const {config,hash}=this.read();
    if(expected!==this.revision)return {kind:'conflict',message:'Someone else changed these settings. Close and reopen the card.'};
    if(!Array.isArray(ops)||!ops.length||ops.length>64||Buffer.byteLength(JSON.stringify(ops))>512*1024)throw Error('Use bounded provider path edits.');
    const next=structuredClone(config);
    for(const op of ops){
      if(!object(op)||!['set','unset'].includes(op.op)||!Array.isArray(op.path)||op.path[0]!=='providers'||![2,3].includes(op.path.length))throw Error('Use a provider field operation.');
      const provider=this.provider(op.path[1]),current=next.providers[provider]??{};
      if(!object(current))throw Error('Repair the provider profile first.');
      const field=op.path[2];if(field!==undefined&&!FIELDS.includes(field))throw Error('This field is not editable in Models.');
      if(field===undefined){
        if(op.op==='unset'){delete next.providers[provider];continue;}
        if(own(next.providers,provider))throw Error('That provider already exists. Edit its card.');
        if(!/^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/.test(provider)||!object(op.value)||Object.keys(op.value).some(key=>!FIELDS.includes(key)))throw Error('Enter a valid custom provider.');
        next.providers[provider]={};for(const [key,value] of Object.entries(op.value))this.field(next.providers[provider],provider,key,value,hash,config.providers[provider]??{});continue;
      }
      if(!own(next.providers,provider))next.providers[provider]={};
      const mapped=field==='displayName'?'name':field==='baseURL'?'baseUrl':field;
      if(op.op==='unset'){if(field!=='apiKeyEnv')delete current[mapped];}
      else this.field(current,provider,field,op.value,hash,config.providers[provider]??{});
      next.providers[provider]=current;
    }
    await this.commit(next,hash);return {kind:'written',view:(await this.describe()).namespaces[0]};
  }
  private field(profile:Data,provider:string,field:string,value:unknown,hash:string,current:Data){
    if(field==='apiKeyEnv'){if(value!==ref(provider))throw Error('Use the provider credential reference.');return;}
    if(field==='models'){profile.models=this.models(provider,value,current,hash);return;}
    if(typeof value!=='string'||!value.trim()||value.length>2048||/[\r\n\0]/.test(value))throw Error('Enter a valid provider field.');
    if(field==='api'&&!MODEL_APIS.includes(value))throw Error('Choose a supported Pi API.');
    profile[field==='displayName'?'name':field==='baseURL'?'baseUrl':field]=field==='baseURL'?endpoint(value):value;
  }
  async setCredential(reference:unknown,value:unknown,expected:unknown){
    this.guard();const credential=await this.credential(reference),{config,hash}=this.read();
    if(expected!==this.revision)throw Error('Model settings changed. Close and reopen this card.');
    if(!credential.writable)throw Error('This provider uses a command, environment expression or OAuth account. Manage that authentication through Pi before replacing it here.');
    if(typeof value!=='string'||!value.trim()||value.length>8192||/[\r\n\0]/.test(value))throw Error('Enter a valid API key.');
    const next=structuredClone(config);next.providers[credential.provider]={...next.providers[credential.provider],apiKey:literal(value.trim())};
    await this.commit(next,hash);return {revision:(await this.describe()).revision};
  }
  async discover(request:Data,callerSignal?:AbortSignal){
    if(!object(request)||Object.keys(request).some(key=>!['provider','baseURL','api','apiKey'].includes(key)))return {kind:'refused',message:'Use the model form discovery fields.'};
    const provider=request.provider===undefined?undefined:this.provider(request.provider),defaults=await this.defaults;
    // The supplier editor automatically asks for defaults with provider only.
    // This cold read must never execute configured keys or contact a catalog.
    if(provider!==undefined&&(Object.keys(request).every(key=>key==='provider')||defaults.getModels(provider).length))return {kind:'found',models:this.runtime().getModels(provider).map(model=>({id:model.id,name:model.name,contextWindow:model.contextWindow,maxTokens:model.maxTokens,inputModalities:model.input})),coverage:{source:'installed',providerHasMore:false,droppedRows:0}};
    let baseURL:string;try{baseURL=endpoint(request.baseURL);}catch{return {kind:'refused',message:'Enter a valid HTTPS or loopback HTTP model endpoint without credentials, queries or fragments.'};}
    const {config,hash}=this.read(),profile=provider===undefined?undefined:config.providers[provider];
    const api=request.api??profile?.api??'openai-completions';if(!['openai-completions','openai-responses','anthropic-messages'].includes(api))return {kind:'refused',message:'This API has no endpoint listing this build can read. Use the installed catalog or enter models manually.'};
    if(request.apiKey!==undefined&&(typeof request.apiKey!=='string'||request.apiKey.length>8192))return {kind:'refused',message:'Enter a valid one-shot API key.'};
    if(this.probes.size>=2)return {kind:'refused',message:'Two model listings are already running. Wait for one to finish.'};
    const probe=new AbortController(),signal=AbortSignal.any([probe.signal,AbortSignal.timeout(12000),...(callerSignal?[callerSignal]:[])]);this.probes.add(probe);
    try{
      signal.throwIfAborted();let providerHasMore=false;
      const stored=async()=>{
        const oneShot=request.apiKey!==undefined;
        if(hash!==this.appliedHash||this.fileHash()!==hash){if(oneShot)return undefined;throw Error('PROFILE_CHANGED');}
        if(!provider||!profile)return undefined;
        let sameOrigin=false;try{sameOrigin=new URL(baseURL).origin===new URL(endpoint(profile.baseUrl)).origin;}catch{}
        if(!sameOrigin){if(oneShot)return undefined;throw Error('ENDPOINT_CHANGED');}
        if(Object.values(profile.headers??{}).some(command)||!oneShot&&(command(profile.apiKey)||this.runtime().isUsingOAuth(provider)||(await this.oauthAccounts(signal)).has(provider)))throw Error('AUTH_UNSUPPORTED');
        const headers=Object.fromEntries(Object.entries(profile.headers??{}).map(([name,value])=>{if(typeof value!=='string')throw Error('AUTH_UNSUPPORTED');return [name,value.replace(/\$(\$|!)/g,(_match,character)=>character)];}));
        // A header-only relay still has discovery auth even when Pi has no
        // API-key handler. Do not refresh an OAuth-only route for a typed key.
        if(oneShot&&!this.runtime().getProvider(provider)?.auth.apiKey){if(Object.values(profile.headers??{}).some(expression))throw Error('AUTH_UNSUPPORTED');return {auth:{headers}};}
        const resolved=await this.runtime().getAuth(provider,{signal,...(oneShot?{apiKey:request.apiKey}:{})});
        if(!resolved&&Object.values(profile.headers??{}).some(expression))throw Error('AUTH_UNSUPPORTED');
        return resolved??{auth:{headers}};
      };
      let auth:any;
      // A one-shot key does not read, resolve, overwrite or fall back to stored
      // credentials. An applied same-origin profile can still supply deployment
      // headers through Pi's public auth API with the literal key override.
      auth=await stored();
      const rows=await discoverEndpoint({baseURL,api,...(request.apiKey===undefined?{}:{apiKey:request.apiKey}),signal},()=>({headers:auth?.auth?.headers,resolveApiKey:async()=>auth?.auth?.apiKey}),fetch,partial=>{providerHasMore=partial;});
      signal.throwIfAborted();if(this.fileHash()!==hash)return {kind:'refused',message:'The model profile changed while listing. Read the current settings before fetching again.'};
      const ids=new Set<string>();let droppedRows=0;
      const models=rows.filter(row=>{const valid=typeof row.id==='string'&&row.id===row.id.trim()&&!!row.id&&row.id.length<=512&&typeof row.name==='string'&&row.name.length<=512&&!ids.has(row.id);if(!valid){droppedRows++;return false;}ids.add(row.id);return true;});
      if(models.length>4096)return {kind:'refused',message:'The endpoint returned too many model candidates. Enter the needed models manually.'};
      return {kind:'found',models,coverage:{source:'endpoint',pages:1,providerHasMore,droppedRows}};
    }catch(error){
      const code=(error as any)?.code,message=(error as any)?.message;
      return {kind:'refused',message:signal.aborted?'Model listing was cancelled or exceeded its time limit. Nothing was saved or retried.':message==='PROFILE_CHANGED'?'Refresh model settings before using stored authentication.':message==='ENDPOINT_CHANGED'?'Enter a one-shot key to list models from a changed endpoint origin.':message==='AUTH_UNSUPPORTED'?'This authentication method cannot be used for endpoint listing. Enter models manually.':code==='INVALID_CREDENTIAL'?'The supplied key cannot be used in an HTTP header.':code==='DISCOVERY_UNSUPPORTED'?'This API cannot list endpoint models. Enter them manually.':'The endpoint did not return a usable model listing. Check the endpoint, protocol and authentication, or enter models manually. Nothing was saved or retried.'};
    }finally{this.probes.delete(probe);}
  }
  async configure(value:unknown){
    this.guard();if(!object(value)||!object(value.providers))throw Error('Invalid providers configuration');
    // Complete SDK configuration is not restricted to the GUI's curated fields
    // or catalog size. Validate without resolving credentials before storing it.
    await this.commit(structuredClone(value),this.fileHash(),false);
  }
  private async commit(config:Data,hash:string,bounded=true){
    const profiles=Object.values(config.providers);if(bounded&&(Buffer.byteLength(JSON.stringify(config))>4*1024*1024||profiles.length>128||profiles.reduce<number>((sum,profile:any)=>sum+(Array.isArray(profile?.models)?profile.models.length:0),0)>4096||profiles.some((profile:any)=>Array.isArray(profile?.models)&&profile.models.length>512)))throw Error('The model profile exceeds the bounded editor catalog limit.');
    const temporary=mkdtempSync(join(dirname(this.file),'.model-settings-'));
    try{
      // Registered providers can supply defaults, custom APIs and auth handlers
      // absent from a clean runtime. Validate these only in their actual SDK
      // registration context; do not clone handlers or trigger shadow refreshes.
      const deferred=new Set(this.runtime().getRegisteredProviderIds());
      const file=join(temporary,'models.json');atomicJson(file,{...config,providers:Object.fromEntries(Object.entries(config.providers).filter(([id])=>!deferred.has(id)))});
      const validated=await ModelRuntime.create({modelsPath:file,credentials:new InMemoryCredentialStore(),refreshOnCreate:false,allowModelNetwork:false});
      if(validated.getError())throw Error('Pi rejected this model configuration. Check the provider API and model fields.');
      this.guard();if(this.fileHash()!==hash)throw Error('Model settings changed. Read the current configuration before saving.');
      this.cancelDiscoveries();await this.apply(config,validated,deferred);if(bounded)this.read();
    }finally{rmSync(temporary,{recursive:true,force:true});}
  }
}
