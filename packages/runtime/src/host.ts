// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {desktopCapabilities} from '../../desktop/src/capabilities.js';
import {desktopPackage,control as desktopControl} from '../../desktop/src/index.js';
import {DualMemoryClient} from '../../memory/src/dual.js';
import {piMemoryContext,piTranscriptEvent} from '../../memory/src/pi.js';
import {memoryPackage} from '../../memory/src/index.js';
import {promptCall} from '../../prompt-library/src/client.js';
import {appendFileSync,truncateSync,mkdirSync,existsSync,readFileSync,readdirSync,writeFileSync,unlinkSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {randomUUID,createHash} from 'node:crypto';
import {createAgentSession,ModelRuntime,SessionManager,SettingsManager,DefaultResourceLoader,type AgentSession,type ExtensionAPI} from '@earendil-works/pi-coding-agent';
import {BrowserBroker} from '../../pi-browser/src/index.js';
import {homePackage} from '../../home-client/src/pi.js';
import {linuxPackage} from '../../pi-linux/src/index.js';
import {type Data,type DisplayEvent,PROTOCOL,identifier,text} from '../../protocol/src/index.js';
import {atomicJson,readJson,privateDir,paths} from './storage.js';
import {Interactions} from './interactions.js';
import {isRoutineQuery} from './permissions.js';
import {branchContext} from './branches.js';
import {SetupConnections} from './setup.js';
import {RELEASE} from '../../contracts/src/release.js';
import {historyPage} from '../../protocol/src/history.js';
import {DesktopSpecialist,DESKTOP_DELEGATION_GUIDANCE} from './desktop-specialist.js';
import {linuxDesktopExecutor} from '../../pi-linux/src/desktop-executor.js';
const browserRecovery = readFileSync(new URL('../../../config/browser-recovery.md', import.meta.url), 'utf8');
interface Meta {memoryStartSeq?:number;surface?:"linux"|"browser";id:string;cwd:string;file?:string;selection:Data;title:string;saved:boolean;policy:string;updatedAt:number;requests:string[];running:boolean;fork?:{sessionId:string;messageSeq:number;mode:'reply'|'edit'}}
interface Loaded {memory:DualMemoryClient;meta:Meta;session:AgentSession;manager:SessionManager;events:DisplayEvent[];turnId?:string;cancelled:boolean;task?:Promise<void>}
export class Host {
  readonly dirs=paths();
  readonly browser=new BrowserBroker();
  readonly metadata=new Map<string,Meta>();readonly loaded=new Map<string,Loaded>();
  readonly interactions:Interactions;
  modelRuntime!:ModelRuntime;
  readonly setup=new SetupConnections(join(this.dirs.agent,'models.json'));
  settings:Data;
  private serial:Promise<unknown>=Promise.resolve();
  private quiescing=false;
  readonly backend=process.env.AUGMENTOR_PI_DESKTOP_HELPER || fileURLToPath(new URL('../../../apps/native/augmentor_linux/desktop.py',import.meta.url));
  readonly desktopSpecialist=new DesktopSpecialist(join(this.dirs.state,'desktop-runs'),linuxDesktopExecutor(this.backend));
  constructor(readonly publish:(sid:string,frame:Data)=>void,readonly connected:(sid:string)=>boolean){
    this.settings=readJson(join(this.dirs.config,'settings.json'),{revision:0,defaultPreset:'workspace-write',pinned:[],hidden:[],defaultModel:null});
    this.interactions=new Interactions(publish,connected,Number(process.env.AUGMENTOR_PI_INTERACTION_TIMEOUT||120000));
    for(const file of readdirSync(this.dirs.sessions).filter(f=>f.endsWith('.meta.json'))){const m=readJson<Meta>(join(this.dirs.sessions,file),null as any);identifier(m.id);this.metadata.set(m.id,m);}
  }
  async init(){this.modelRuntime=await ModelRuntime.create({authPath:join(this.dirs.agent,'auth.json'),modelsPath:join(this.dirs.agent,'models.json'),modelsStorePath:join(this.dirs.agent,'models-store.json'),allowModelNetwork:false});
    if(this.modelRuntime.getError())throw new Error(this.modelRuntime.getError());
    for(const m of this.metadata.values())if(m.running){if(this.events(m).at(-1)?.type==='turn/end'){m.running=false;this.save(m);continue;}this.append(m,'turn/end',{reason:{kind:'interrupted'},message:'Runtime stopped. The previous action outcome may be unknown; the prompt was not replayed.'});m.running=false;this.save(m);}
  }
  save(m:Meta){atomicJson(join(this.dirs.sessions,m.id+'.meta.json'),m);}
  persistSettings(){this.settings.revision++;atomicJson(join(this.dirs.config,'settings.json'),this.settings);}
  events(m:Meta):DisplayEvent[]{const file=join(this.dirs.sessions,m.id+'.events.jsonl');if(!existsSync(file))return [];let raw=readFileSync(file);if(raw.length&&raw.at(-1)!==10){const end=raw.lastIndexOf(10)+1;truncateSync(file,end);raw=raw.subarray(0,end);}const lines=raw.toString('utf8').split('\n');const result:DisplayEvent[]=[];
    for(let i=0;i<lines.length;i++){if(!lines[i])continue;try{result.push(JSON.parse(lines[i]));}catch{throw new Error('Corrupt session display journal');}}
    return result;
  }
  append(m:Meta,type:string,data:Data){const record=this.loaded.get(m.id);const events=record?.events??this.events(m);const event:DisplayEvent={seq:(events.at(-1)?.seq??0)+1,type,data,...(record?.turnId?{turnId:record.turnId}:{})};
    appendFileSync(join(this.dirs.sessions,m.id+'.events.jsonl'),JSON.stringify(event)+'\n',{mode:0o600});if(record)events.push(event);
    if(record){const memories=piTranscriptEvent(event,true);if(memories.length)void record.memory.append(memories);}
    this.publish(m.id,{method:'session/event',payload:{sessionId:m.id,event}});return event;
  }
  async selected(selection:Data):Promise<NonNullable<ReturnType<ModelRuntime['getModel']>>>{if(!selection||typeof selection.provider!=='string'||typeof selection.model!=='string')throw new Error('Choose a model before sending.');
    const model=this.modelRuntime.getModel(selection.provider,selection.model);if(!model)throw new Error('The selected model is unavailable. Refresh models or update model configuration.');
    const available=await this.modelRuntime.getAvailable(selection.provider,{signal:AbortSignal.timeout(10000)});if(!available.some(m=>m.id===model.id))throw new Error('The selected provider needs credentials. Configure Pi before sending.');return model;
  }
  async catalog(){const available=new Set((await this.modelRuntime.getAvailable(undefined,{signal:AbortSignal.timeout(10000)})).map(m=>m.provider+'/'+m.id));const groups=new Map<string,Data>();
    for(const m of this.modelRuntime.getModels()){if(!groups.has(m.provider))groups.set(m.provider,{provider:m.provider,name:m.provider,models:[]});
      let local=false;try{local=['127.0.0.1','[::1]','localhost'].includes(new URL(m.baseUrl??'').hostname);}catch{}
      groups.get(m.provider)!.models.push({provider:m.provider,model:m.id,name:m.name,location:local?'Local':'Network',available:available.has(m.provider+'/'+m.id)});}
    return {groups:[...groups.values()],pinned:this.settings.pinned.map((p:any)=>typeof p==='string'?p:p.provider+'/'+p.model),hidden:this.settings.hidden,default:this.settings.defaultModel,failures:[]};
  }
  getMeta(id:unknown){const m=this.metadata.get(identifier(id));if(!m)throw new Error('Conversation not found');return m;}
  policy(m:Meta){return (pi:ExtensionAPI)=>{pi.on('tool_call',async e=>{
    if(e.toolName==='linux_desktop_stop')this.desktopSpecialist.cancel('pi:'+m.id);
    if(m.surface==='browser'&&!['browser_tabs_list','browser_screenshot','browser_snapshot','browser_navigate','browser_click','browser_type','memory_recall','memory_source','home_read','home_status','home_request','home_result','home_cancel'].includes(e.toolName))
      return {block:true,reason:'This browser chat can only use its browser tools.'};
    if(this.desktopSpecialist.busy()&&['linux_desktop_connect','linux_desktop_snapshot','linux_desktop_action'].includes(e.toolName))return {block:true,reason:'A desktop specialist owns the desktop. Wait for it or Stop it before using direct desktop tools.'};
    if(['home_read','home_status','home_result','home_cancel','desktop_delegate','desktop_evidence','memory_recall','memory_source','read','ls','find','grep','linux_system_profile','linux_desktop_observe','linux_desktop_connect','linux_desktop_snapshot','linux_desktop_stop','ask_user','browser_tabs_list','browser_screenshot','browser_snapshot'].includes(e.toolName))return;
    if(e.toolName==='bash'&&isRoutineQuery(e.input.command))return;
    if(m.policy==='read-only')return {block:true,reason:'Read-only chat: actions that can change state are disabled.'};
    if(e.toolName==='home_request')return; // Persistent NAS pairing grants the scoped Home capability.
    if(m.policy!=='danger-full-access'&&!await this.interactions.approve(m.id,e.toolName,e.input))return {block:true,reason:'Action not approved, cancelled or no user interface connected.'};
  });};}
  async load(m:Meta,branchManager?:SessionManager){let record=this.loaded.get(m.id);if(record)return record;
    const model=await this.selected(m.selection);
    const memory=new DualMemoryClient('pi:'+m.id,m.cwd,undefined,message=>console.warn('[augmentor-memory]',message));
    mkdirSync(m.cwd,{recursive:true,mode:0o700});
    const settingsManager=SettingsManager.inMemory({enableInstallTelemetry:false,retry:{enabled:false},compaction:{enabled:true},packages:[],defaultProjectTrust:'never'});
    const resources=readJson<Data>(join(this.dirs.config,'resources.json'),{sources:[],skills:[]});
    if(!Array.isArray(resources.sources)||!Array.isArray(resources.skills))throw new Error('Invalid Pi resource configuration');
    const resourceLoader=new DefaultResourceLoader({cwd:m.cwd,agentDir:this.dirs.agent,settingsManager,noExtensions:true,noSkills:true,noContextFiles:true,noThemes:true,
      additionalExtensionPaths:m.surface==='browser'?[]:resources.sources,additionalSkillPaths:m.surface==='browser'?[]:resources.skills,additionalPromptTemplatePaths:[privateDir(join(this.dirs.agent,'prompts'))],
      extensionFactories:[this.policy(m),homePackage('pi:'+m.id),pi=>memoryPackage(pi,m.fork?undefined:'pi:'+m.id),piMemoryContext(memory,!m.fork),...(m.surface==='browser'?[this.browser.package(m.id)]:process.env.AUGMENTOR_PI_LINUX_TOOLS==='0'?[]:[linuxPackage(this.backend),desktopPackage('pi:'+m.id),this.desktopSpecialist.package({owner:'pi:'+m.id,cwd:m.cwd,agentDir:this.dirs.agent,modelRuntime:this.modelRuntime,policy:m.policy,approve:(name,args)=>this.interactions.approve(m.id,name,args),cancelInteractions:()=>this.interactions.cancel(m.id),progress:info=>this.append(m,'desktop/progress',info)})])],
      appendSystemPrompt:[browserRecovery,m.surface==='browser'?'You are Augmentor Agent for Browser, powered by Pi. Use the browser tools to inspect and act in the connected visible browser. Read a fresh snapshot before actions. Stop on stale targets or denied actions. Report unknown outcomes honestly; do not replay actions.': `You are Augmentor Agent Desktop, powered by Pi. The operating system is ${process.platform}. Use tools to check actual facts. Keep the user informed. Use linux_browser_open for visible Chromium; never claim dispatch proves a page loaded. Use the platform accessibility observations for desktop structure. Stop on stale targets or denied actions. Use linux_desktop_connect and the user’s OS consent for desktop control. Use fresh screenshots before each action, then verify the result. A model must support image input. Stop on focus changes; never replay an unknown input outcome. Ask the user only when required information is missing.`,...(m.surface!=='browser'&&process.env.AUGMENTOR_PI_LINUX_TOOLS!=='0'?[DESKTOP_DELEGATION_GUIDANCE]:[])],
    });await resourceLoader.reload();
    const errors=resourceLoader.getExtensions().errors;if(errors.length)throw new Error('Pi extension loading failed: '+errors.map(e=>e.error).join('; '));
    const manager=branchManager??(m.file&&existsSync(m.file)?SessionManager.open(m.file):SessionManager.create(m.cwd,join(this.dirs.sessions,m.id)));
    const created=await createAgentSession({cwd:m.cwd,agentDir:this.dirs.agent,modelRuntime:this.modelRuntime,model,thinkingLevel:'off',settingsManager,resourceLoader,sessionManager:manager,tools:[...(m.surface==='browser'?[]:['read','write','edit','bash','ls','find','grep']),...resourceLoader.getExtensions().extensions.flatMap(e=>[...e.tools.keys()])]});
    if(created.modelFallbackMessage){created.session.dispose();throw new Error('Pi attempted a model substitution: '+created.modelFallbackMessage);}
    if(created.session.model?.id!==m.selection.model||created.session.model?.provider!==m.selection.provider){created.session.dispose();throw new Error('Pi selected a different model.');}
    if(m.surface!=='browser')created.session.agent.toolExecution='sequential';
    if(m.title)created.session.setSessionName(m.title);m.file=created.session.sessionFile;this.save(m);
    record={memory,meta:m,session:created.session,manager,events:this.events(m),cancelled:false};this.loaded.set(m.id,record);
    let history=record.events;
    if(m.fork){m.memoryStartSeq??=history.at(-1)?.seq??0;this.save(m);history=history.filter(e=>e.seq>m.memoryStartSeq!);}
    await memory.append(history.flatMap(event=>piTranscriptEvent(event)));
    await created.session.bindExtensions({mode:'rpc',uiContext:this.interactions.ui(m.id),onError:error=>this.append(m,'runtime/error',{message:error.error})});
    created.session.subscribe(e=>{
      if(e.type==='message_start'&&e.message.role==='user')this.append(m,'user/message',{source:{kind:'user'},content:typeof e.message.content==='string'?[{type:'text',text:e.message.content}]:e.message.content});
      if(e.type==='message_update'){
        const a=e.assistantMessageEvent;if(a.type==='text_delta')this.append(m,'assistant/chunk',{chunk:{type:'text-delta',text:a.delta}});
        if(a.type==='thinking_delta')this.append(m,'assistant/chunk',{chunk:{type:'reasoning-delta',text:''}});
      }
      if(e.type==='message_end'&&e.message.role==='assistant'){
        this.append(m,'assistant/message',{message:{content:e.message.content,stopReason:e.message.stopReason}});
        if(e.message.stopReason==='error')this.append(m,'runtime/error',{message:e.message.errorMessage||'Model request failed'});
      }
      if(e.type==='tool_execution_start')this.append(m,'tool/call',{name:e.toolName,toolCallId:e.toolCallId});
      if(e.type==='tool_execution_end')this.append(m,'tool/result',{name:e.toolName,toolCallId:e.toolCallId,isError:e.isError,result:{...e.result,content:e.result.content.map((part:Data)=>part.type==='image'?{type:'text',text:'[Desktop image sent to the selected model]'}:part)}});
    });return record;
  }
  async cancel(id:unknown){const m=this.getMeta(id);const r=this.loaded.get(m.id);this.desktopSpecialist.cancel('pi:'+m.id);this.interactions.cancel(m.id);if(r)await r.memory.activity('stop');if(m.surface!=='browser')await desktopControl('stop','pi:'+m.id).catch(()=>{});if(!r||!m.running)return {accepted:false};r.cancelled=true;r.session.clearQueue();r.session.abortCompaction();await r.session.abort();return {accepted:true};}
  async branch(p:Data){
    const source=this.getMeta(p.sessionId),sid=identifier(p.newSessionId);
    if(!Number.isSafeInteger(p.messageSeq)||p.messageSeq<1||!['reply','edit'].includes(p.mode))throw new Error('Invalid branch target');
    const fork={sessionId:source.id,messageSeq:p.messageSeq,mode:p.mode as 'reply'|'edit'};
    const existing=this.metadata.get(sid);
    if(existing){if(JSON.stringify(existing.fork)!==JSON.stringify(fork))throw new Error('Conversation ID already exists');return this.branchRow(existing);}
    if(source.running)throw new Error('Stop the current response before branching or editing.');
    if(!source.file||!existsSync(source.file))throw new Error('This conversation has no persisted Pi history yet.');
    const directory=privateDir(join(this.dirs.sessions,sid));
    const context=branchContext(source.file,directory,this.loaded.get(source.id)?.events??this.events(source),p.messageSeq,p.mode);
    const m:Meta={memoryStartSeq:context.events.at(-1)?.seq??0,surface:source.surface,id:sid,cwd:source.cwd,file:context.file,selection:{...source.selection},title:((p.mode==='edit'?'Edit · ':'Branch · ')+source.title).slice(0,200),saved:false,policy:source.policy,updatedAt:Date.now(),requests:[],running:false,fork};
    writeFileSync(join(this.dirs.sessions,sid+'.events.jsonl'),context.events.map(e=>JSON.stringify(e)+'\n').join(''),{mode:0o600});
    // Pi defers writing branches with no assistant messages until a reply.
    if(context.manager&&context.file&&!existsSync(context.file))await this.load(m,context.manager);
    this.metadata.set(sid,m);this.save(m);
    if(p.mode==='reply')this.append(m,'turn/end',{reason:{kind:'completed'}});
    this.append(m,'session/title',{title:m.title});
    return this.branchRow(m);
  }
  branchRow(m:Meta){return {sessionId:m.id,cwd:m.cwd,agentPreset:m.surface==='browser'?'augmentor-browser-pi':'augmentor-linux-pi',title:m.title,saved:m.saved,running:m.running,selection:m.selection,fork:m.fork};}
  submit(r:Loaded,input:string,id:string){const m=r.meta;if(m.requests.includes(id))return {accepted:true,duplicate:true};if(m.running)throw new Error('This conversation is already working');
    m.running=true;r.cancelled=false;r.turnId=randomUUID();m.requests=[...m.requests.slice(-99),id];m.updatedAt=Date.now();this.save(m);this.append(m,'turn/start',{});
    if(!m.title){m.title=input.replace(/\s+/g,' ').slice(0,80);r.session.setSessionName(m.title);this.append(m,'session/title',{title:m.title});this.save(m);}
    r.task=(async()=>{let failed=false;try{await r.memory.activity('foreground');await r.session.prompt(input,{expandPromptTemplates:false,source:'rpc'});}catch(error){failed=true;this.append(m,'runtime/error',{message:String(error)});}finally{
      await r.memory.activity('stop');
      this.interactions.cancel(m.id);if(m.surface!=='browser')await desktopControl('stop','pi:'+m.id).catch(()=>{});m.running=false;m.updatedAt=Date.now();this.save(m);this.append(m,'turn/end',{reason:{kind:r.cancelled?'aborted':failed?'error':'completed'}});r.turnId=undefined;
    }})();return {accepted:true,turnId:r.turnId};
  }
  async dispatch(method:string,p:Data,id:string){
    if(this.quiescing&&method!=='host.describe')throw new Error('Runtime is closing for maintenance. No action was submitted.');
    if(method==='setup.test')return this.setup.test(p);
    if(method==='setup.cancel')return this.setup.cancel();
    if(method==='session.cancel')return this.cancel(p.sessionId);
    if(method==='interaction.respond')return this.interactions.answer(identifier(p.rpcId),p.value,identifier(p.sessionId));
    // Serialize state-changing preparations so two clients cannot create/replace an execution owner.
    const run=this.serial.then(()=>{if(this.quiescing&&method!=='host.describe')throw new Error('Runtime is closing for maintenance. No action was submitted.');return this.handle(method,p,id);});this.serial=run.catch(()=>{});return run;
  }
  async handle(method:string,p:Data,id:string):Promise<any>{switch(method){
    case 'host.describe':return {protocol:PROTOCOL,pid:process.pid,activeTurns:[...this.metadata.values()].filter(m=>m.running).length,version:RELEASE.version,piVersion:'0.85.1',capabilities:{linuxTools:process.env.AUGMENTOR_PI_LINUX_TOOLS!=='0',desktopInput:desktopCapabilities().available,osCustomisation:false,localRouteEnforcement:false},desktopSpecialist:{version:'augmentor-computer-use/1',available:desktopCapabilities().available,selectedModelOnly:true,requiresImageModel:true,maxConcurrent:1,evidence:'local-files',coreIntegration:false},desktopControl:desktopCapabilities(),configDir:this.dirs.config,stateDir:this.dirs.state};
    case 'host.prepareShutdown':
      if([...this.metadata.values()].some(m=>m.running))throw new Error('Stop active Pi tasks before shutting down the runtime');
      this.quiescing=true;this.setup.cancel();return {accepted:true};
    case 'session.branch':return this.branch(p);
    case 'models.list':return this.catalog();
    case 'setup.save':{
      if(!['read-only','workspace-write','danger-full-access'].includes(p.approvalMode))throw new Error('Choose an approval mode.');
      const checked=this.setup.checked(p.token);
      await this.handle('models.configure',{config:checked.config},id);
      this.settings.defaultModel=checked.selection;this.settings.defaultPreset=p.approvalMode;this.persistSettings();
      this.setup.saved();return {selection:checked.selection,catalog:await this.catalog()};
    }
    case 'models.validate':await this.selected(p);return {valid:true};
    case 'models.pin':{await this.selected(p);const key=p.provider+'/'+p.model;this.settings.pinned=this.settings.pinned.map((m:any)=>typeof m==='string'?m:m.provider+'/'+m.model).filter((m:string)=>m!==key);if(p.pinned)this.settings.pinned.push(key);this.persistSettings();return this.catalog();}
    case 'models.configure':{if(!p.config||typeof p.config.providers!=='object'||Array.isArray(p.config.providers))throw new Error('Invalid providers configuration');if([...this.metadata.values()].some(m=>m.running))throw new Error('Stop active chats before changing providers');const file=join(this.dirs.agent,'models.json');const old=existsSync(file)?readFileSync(file,'utf8'):null;atomicJson(file,p.config);try{await this.modelRuntime.refresh({allowNetwork:false,signal:AbortSignal.timeout(10000)});if(this.modelRuntime.getError())throw new Error(this.modelRuntime.getError());}catch(error){if(old===null)unlinkSync(file);else writeFileSync(file,old,{mode:0o600});await this.modelRuntime.refresh({allowNetwork:false});throw error;}return this.catalog();}
    case 'models.reload':await this.modelRuntime.refresh({allowNetwork:false,signal:AbortSignal.timeout(10000)});return this.catalog();
    case 'session.create':{const sid=identifier(p.sessionId);let m=this.metadata.get(sid);if(!m){await this.selected(p.selection);const cwd=resolve(text(p.cwd,4096));m={surface:p.surface==='browser'?'browser':'linux',id:sid,cwd,selection:p.selection,title:'',saved:false,policy:this.settings.defaultPreset,updatedAt:Date.now(),requests:[],running:false};this.metadata.set(sid,m);this.save(m);await this.load(m);}return {sessionId:sid};}
    case 'session.list':return {items:[...this.metadata.values()].sort((a,b)=>b.updatedAt-a.updatedAt).map(m=>({sessionId:m.id,cwd:m.cwd,agentPreset:m.surface==='browser'?'augmentor-browser-pi':'augmentor-linux-pi',title:m.title,updatedAt:m.updatedAt,saved:m.saved,running:m.running,blank:!m.title}))};
    case 'session.history':{const m=this.getMeta(p.sessionId);return historyPage(this.loaded.get(m.id)?.events??this.events(m),p.maxMessages,p.beforeSeq);}
    case 'session.models':return {current:this.getMeta(p.sessionId).selection};
    case 'session.selectModel':{const m=this.getMeta(p.sessionId);if(m.running)throw new Error('Stop before changing models');const model=await this.selected(p);const previous=m.selection;const loaded=this.loaded.get(m.id);if(loaded)await loaded.session.setModel(model);else{m.selection={provider:p.provider,model:p.model};try{await this.load(m);}catch(error){m.selection=previous;this.save(m);throw error;}}m.selection={provider:p.provider,model:p.model};this.save(m);return {current:m.selection};}
    case 'session.prompt':{const m=this.getMeta(p.sessionId);if(m.requests.includes(id))return {accepted:true,duplicate:true};const input=text(p.content?.filter((part:Data)=>part.type==='text').map((part:Data)=>part.text).join('\n'));const r=await this.load(m);return this.submit(r,input,id);}
    case 'session.rename':{const m=this.getMeta(p.sessionId);m.title=text(p.title,200);this.loaded.get(m.id)?.session.setSessionName(m.title);this.save(m);this.append(m,'session/title',{title:m.title});return {title:m.title};}
    case 'chats.saved':{if(p.action&&p.action!=='state'){if(!['save','unsave'].includes(p.action))throw new Error('Invalid saved-chat action');const m=this.getMeta(p.sessionId);m.saved=p.action==='save';this.save(m);}return {saved:[...this.metadata.values()].filter(m=>m.saved).map(m=>m.id)};}
    case 'settings.describe':return {namespaces:[{ns:'permission',revision:this.settings.revision,value:{defaultPreset:this.settings.defaultPreset}},{ns:'prompt-library',revision:this.settings.revision,value:await promptCall('prompts.list')}]};
    case 'settings.mutate':{if(p.ns!=='permission'||p.expectedRevision!==this.settings.revision)throw new Error('Settings changed. Reopen the dialog.');const op=p.ops?.[0];if(p.ops.length!==1||op.op!=='set'||op.path?.join('.')!=='defaultPreset'||!['read-only','workspace-write','danger-full-access'].includes(op.value))throw new Error('Unsupported settings change');this.settings.defaultPreset=op.value;this.persistSettings();return {ok:true};}
    case 'prompts.list':case 'prompts.save':case 'prompts.delete':return promptCall(method,p,id);
    default:throw new Error('Unsupported method: '+method);
  }}
  async close(){this.setup.cancel();for(const r of this.loaded.values()){await this.cancel(r.meta.id);await r.task;r.memory.close();await r.memory.flush();r.session.dispose();}}
}
