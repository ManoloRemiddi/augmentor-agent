// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {desktopCapabilities} from '../../desktop/src/capabilities.js';
import {desktopPackage,control as desktopControl} from '../../desktop/src/index.js';
import {DualMemoryClient} from '../../memory/src/dual.js';
import {piMemoryContext,piTranscriptEvent} from '../../memory/src/pi.js';
import {memoryPackage} from '../../memory/src/index.js';
import {promptCall} from '../../prompt-library/src/client.js';
import {mkdirSync,existsSync,readFileSync,readdirSync,writeFileSync,unlinkSync} from 'node:fs';
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
import {DisplayHistory} from './display-history.js';
import {NativeHistory} from './native-history.js';
import {ManagedMcp} from './mcp.js';
import {DesktopSpecialist,DESKTOP_DELEGATION_GUIDANCE} from './desktop-specialist.js';
import {linuxDesktopExecutor} from '../../pi-linux/src/desktop-executor.js';
import {ObservationStore,OBSERVATION_PROTOCOL,DEFAULT_RETENTION} from '../../observation/src/store.js';
import {observeSession} from './observations.js';
import {ContextProvenance,PROVENANCE_VERSION} from './context-provenance.js';
import {piToolBudget,trimSavedToolContext,TOOL_BUDGET} from './tool-budget.js';
import {piReassessment} from './reassessment.js';
import {PiExecution,EXECUTION_POLICY,type ExecutionContract} from './execution.js';
import {PiPromptQueue,promptIdentity} from './queue.js';
import {PiSteering} from './steering.js';
import {validateSteeringInput} from './steering-input.js';
import {getSupportedThinkingLevels} from '@earendil-works/pi-ai';
import {PiReasoning,reasoningConfig,savedReasoning,thinkingLevel,requireThinking,type SavedReasoning} from './reasoning.js';
import {PiPromptImprovement} from './prompt-improvement.js';
const browserRecovery = readFileSync(new URL('../../../config/browser-recovery.md', import.meta.url), 'utf8');
interface Meta {reasoning?:SavedReasoning;memoryStartSeq?:number;surface?:"linux"|"browser";id:string;cwd:string;file?:string;selection:Data;title:string;saved:boolean;policy:string;updatedAt:number;requests:string[];running:boolean;fork?:{sessionId:string;messageSeq:number;mode:'reply'|'edit'}}
interface Loaded {memory:DualMemoryClient;meta:Meta;session:AgentSession;manager:SessionManager;events:DisplayEvent[];mcp?:ManagedMcp;reasoning?:PiReasoning;execution?:PiExecution;steering?:PiSteering;phase?:'preparing'|'running'|'settling';initialDelivered?:boolean;preparingInput?:boolean;interruptedInput?:boolean;observation?:ReturnType<typeof observeSession>;turnId?:string;activeRequestId?:string;cancelled:boolean;failed?:boolean;task?:Promise<void>}
/** Admission is serialized; extension preparation must not hold the host's
 * state lock while waiting for a UI answer, another RPC or an input handler.
 */
class SteeringReply {constructor(readonly settled:Promise<Record<string,unknown>>){} }
export class Host {
  readonly dirs=paths();
  readonly browser=new BrowserBroker();
  readonly metadata=new Map<string,Meta>();readonly loaded=new Map<string,Loaded>();
  readonly interactions:Interactions;
  modelRuntime!:ModelRuntime;
  readonly setup=new SetupConnections(join(this.dirs.agent,'models.json'));
  settings:Data;
  readonly observations:ObservationStore;
  readonly improvements=new PiPromptImprovement(join(this.dirs.state,'prompt-improvements.json'));
  private serial:Promise<unknown>=Promise.resolve();
  private quiescing=false;
  private histories=new Map<string,DisplayHistory>();
  private nativeHistories=new Map<string,NativeHistory>();
  private displayOriginals=new Map<string,NativeHistory>();
  private queues=new Map<string,PiPromptQueue>();
  private pumping=new Map<string,Promise<unknown>>();
  readonly backend=process.env.AUGMENTOR_PI_DESKTOP_HELPER || fileURLToPath(new URL('../../../apps/native/augmentor_linux/desktop.py',import.meta.url));
  readonly desktopSpecialist=new DesktopSpecialist(join(this.dirs.state,'desktop-runs'),linuxDesktopExecutor(this.backend));
  constructor(readonly publish:(sid:string,frame:Data)=>void,readonly connected:(sid:string)=>boolean){
    this.settings=readJson(join(this.dirs.config,'settings.json'),{revision:0,defaultPreset:'workspace-write',pinned:[],hidden:[],defaultModel:null});
    this.observations=new ObservationStore(join(this.dirs.state,'observations'),()=>({
      capturePayloads:this.settings.observation?.capturePayloads===true || (this.settings.observation?.capturePayloads===undefined && process.env.AUGMENTOR_PI_CAPTURE_PAYLOADS==='1'),
      ...DEFAULT_RETENTION,
    }));
    this.interactions=new Interactions(publish,connected,Number(process.env.AUGMENTOR_PI_INTERACTION_TIMEOUT||120000));
    for(const file of readdirSync(this.dirs.sessions).filter(f=>f.endsWith('.meta.json'))){const m=readJson<Meta>(join(this.dirs.sessions,file),null as any);identifier(m.id);this.metadata.set(m.id,m);}
  }
  async init(){this.modelRuntime=await ModelRuntime.create({authPath:join(this.dirs.agent,'auth.json'),modelsPath:join(this.dirs.agent,'models.json'),modelsStorePath:join(this.dirs.agent,'models-store.json'),allowModelNetwork:false});
    if(this.modelRuntime.getError())throw new Error(this.modelRuntime.getError());
    for(const m of this.metadata.values()){
      this.queue(m).recover();
      if(m.running){if(this.history(m).last()?.type==='turn/end'){m.running=false;this.save(m);continue;}this.append(m,'turn/end',{reason:{kind:'interrupted'},message:'Runtime stopped. The previous action outcome may be unknown; the prompt was not replayed.'});m.running=false;this.save(m);}
    }
  }
  private queue(m:Meta){let queue=this.queues.get(m.id);if(!queue){queue=new PiPromptQueue(join(this.dirs.sessions,m.id+'.queue.json'),m.id,()=>this.publish(m.id,{method:'session/queue',payload:{sessionId:m.id,...this.queueSnapshot(m.id)}}));this.queues.set(m.id,queue);}return queue;}
  queueSnapshot(id:unknown){const m=this.getMeta(id),r=this.loaded.get(m.id);return this.queue(m).snapshot(!!r&&m.running&&!r.cancelled&&r.phase!=='settling');}
  save(m:Meta){atomicJson(join(this.dirs.sessions,m.id+'.meta.json'),m);}
  persistSettings(){this.settings.revision++;atomicJson(join(this.dirs.config,'settings.json'),this.settings);}
  private history(m:Meta){let history=this.histories.get(m.id);if(!history){history=new DisplayHistory(join(this.dirs.sessions,m.id+'.events.jsonl'));if(this.histories.size>=32)this.histories.delete(this.histories.keys().next().value!);this.histories.set(m.id,history);}return history;}
  events(m:Meta):DisplayEvent[]{return [...this.history(m).all()];}
  append(m:Meta,type:string,data:Data){const record=this.loaded.get(m.id),history=this.history(m);const event:DisplayEvent={seq:history.lastSeq+1,type,data,...(record?.turnId?{turnId:record.turnId}:{})};
    history.append(event);if(record)record.events.push(event);
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
      groups.get(m.provider)!.models.push({provider:m.provider,model:m.id,name:m.name,location:local?'Local':'Network',available:available.has(m.provider+'/'+m.id),thinkingLevels:getSupportedThinkingLevels(m)});}
    return {groups:[...groups.values()],pinned:this.settings.pinned.map((p:any)=>typeof p==='string'?p:p.provider+'/'+p.model),hidden:this.settings.hidden,default:this.settings.defaultModel,failures:[]};
  }
  getMeta(id:unknown){const m=this.metadata.get(identifier(id));if(!m)throw new Error('Conversation not found');return m;}
  reasoningSettings(m:Meta){return savedReasoning(m.reasoning,m.file&&existsSync(m.file)?SessionManager.open(m.file).buildSessionContext().thinkingLevel:'off');}
  async reasoningState(m:Meta){const loaded=await this.load(m),config=reasoningConfig(this.settings.reasoning),saved=this.reasoningSettings(m),model=loaded.session.model!;
    const preset=m.surface==='browser'?'augmentor-browser-pi':'augmentor-linux-pi';
    const route=config.routes.find(r=>r.provider===model.provider&&r.model===model.id);
    return {...saved,availableLevels:getSupportedThinkingLevels(model),policy:{...config,revision:this.settings.revision},route:route??null,lastDecision:loaded.reasoning?.snapshot()??null,adaptiveStatus:saved.mode==='manual'?'manual-override':!config.enabled?'policy-disabled':!config.presets.includes(preset)?'preset-excluded':!route?'unmapped-model':'configured'};
  }
  policy(m:Meta){return (pi:ExtensionAPI)=>{pi.on('tool_call',async e=>{
    if(e.toolName==='linux_desktop_stop')this.desktopSpecialist.cancel('pi:'+m.id);
    if(m.surface==='browser'&&!['browser_tabs_list','browser_screenshot','browser_snapshot','browser_navigate','browser_click','browser_type','memory_recall','memory_source','tool_result_excerpt','home_devices','home_set','home_read','home_status','home_request','home_result','home_cancel'].includes(e.toolName))
      return {block:true,reason:'This browser chat can only use its browser tools.'};
    if(this.desktopSpecialist.busy()&&['linux_desktop_connect','linux_desktop_snapshot','linux_desktop_action'].includes(e.toolName))return {block:true,reason:'A desktop specialist owns the desktop. Wait for it or Stop it before using direct desktop tools.'};
    if(m.surface!=='browser'&&this.loaded.get(m.id)?.mcp?.isRead(e.toolName))return;
    if(['home_devices','home_read','home_status','home_result','home_cancel','desktop_delegate','desktop_evidence','memory_recall','memory_source','tool_result_excerpt','read','ls','find','grep','linux_system_profile','linux_desktop_observe','linux_desktop_connect','linux_desktop_snapshot','linux_desktop_stop','ask_user','browser_tabs_list','browser_screenshot','browser_snapshot'].includes(e.toolName))return;
    if(e.toolName==='bash'&&isRoutineQuery(e.input.command))return;
    if(m.policy==='read-only')return {block:true,reason:'Read-only chat: actions that can change state are disabled.'};
    if(['home_request','home_set'].includes(e.toolName))return; // Persistent NAS pairing grants the scoped Home capability.
    if(m.policy!=='danger-full-access'&&!await this.interactions.approve(m.id,e.toolName,e.input))return {block:true,reason:'Action not approved, cancelled or no user interface connected.'};
  });};}
  async load(m:Meta,branchManager?:SessionManager){let record=this.loaded.get(m.id);if(record)return record;
    const model=await this.selected(m.selection);
    const memory=new DualMemoryClient('pi:'+m.id,m.cwd,undefined,message=>console.warn('[augmentor-memory]',message));
    const mcp=m.surface==='browser'?undefined:new ManagedMcp(this.dirs.agent,this.dirs.state,m.id);
    mkdirSync(m.cwd,{recursive:true,mode:0o700});
    const execution:PiExecution=new PiExecution((kind,data,payload)=>record?.observation?.record(kind,data,payload),(message,incomplete)=>{record?.observation?.record('execution/notice',{message,incomplete});this.append(m,'runtime/notice',{message,incomplete});},{},undefined,(name):ExecutionContract|undefined=>{
      const definition=resourceLoader.getExtensions().extensions.flatMap(extension=>[...extension.tools.values()]).find(tool=>tool.definition.name===name)?.definition;
      return (definition as (typeof definition & {augmentorExecution?:ExecutionContract}))?.augmentorExecution??(mcp?.isRead(name)?{effect:()=> 'read'}:undefined);
    });
    const settingsManager=SettingsManager.inMemory({enableInstallTelemetry:false,enableAnalytics:false,cacheWarming:'off',retry:{enabled:false,provider:{maxRetries:0}},compaction:{enabled:true},packages:[],defaultProjectTrust:'never'});
    const resources=readJson<Data>(join(this.dirs.config,'resources.json'),{sources:[],skills:[]});
    const provenance=new ContextProvenance(()=>this.observations.policy().capturePayloads);
    if(!Array.isArray(resources.sources)||!Array.isArray(resources.skills))throw new Error('Invalid Pi resource configuration');
    const resourceLoader:DefaultResourceLoader=new DefaultResourceLoader({cwd:m.cwd,agentDir:this.dirs.agent,settingsManager,noExtensions:true,noSkills:true,noContextFiles:true,noThemes:true,
      additionalExtensionPaths:m.surface==='browser'?[]:resources.sources,additionalSkillPaths:m.surface==='browser'?[]:resources.skills,additionalPromptTemplatePaths:[privateDir(join(this.dirs.agent,'prompts'))],
      extensionFactories:[this.policy(m),piToolBudget(changes=>record?.observation?.record('context/budget',{changes,units:'unicode-code-points'})),piReassessment(data=>record?.observation?.record('execution/checkpoint',data)),execution.extension,homePackage('pi:'+m.id),pi=>memoryPackage(pi,m.fork?undefined:'pi:'+m.id),piMemoryContext(memory,!m.fork,contribution=>provenance.memory(contribution)),...(mcp?mcp.factories():[]),...(m.surface==='browser'?[this.browser.package(m.id)]:process.env.AUGMENTOR_PI_LINUX_TOOLS==='0'?[]:[linuxPackage(this.backend),desktopPackage('pi:'+m.id),this.desktopSpecialist.package({owner:'pi:'+m.id,cwd:m.cwd,agentDir:this.dirs.agent,modelRuntime:this.modelRuntime,policy:m.policy,approve:(name,args)=>this.interactions.approve(m.id,name,args),cancelInteractions:()=>this.interactions.cancel(m.id),progress:info=>this.append(m,'desktop/progress',info)})]),{name:'augmentor-context-observer',factory:provenance.extension}],
      appendSystemPrompt:[browserRecovery,m.surface==='browser'?'You are Augmentor Agent for Browser, powered by Pi. Use the browser tools to inspect and act in the connected visible browser. Read a fresh snapshot before actions. Stop on stale targets or denied actions. Report unknown outcomes honestly; do not replay actions.': `You are Augmentor Agent Desktop, powered by Pi. The operating system is ${process.platform}. Use tools to check actual facts. Keep the user informed. Use linux_browser_open for visible Chromium; never claim dispatch proves a page loaded. Use the platform accessibility observations for desktop structure. Stop on stale targets or denied actions. Use linux_desktop_connect and the user’s OS consent for desktop control. Use fresh screenshots before each action, then verify the result. A model must support image input. Stop on focus changes; never replay an unknown input outcome. Ask the user only when required information is missing.`,...(m.surface!=='browser'&&process.env.AUGMENTOR_PI_LINUX_TOOLS!=='0'?[DESKTOP_DELEGATION_GUIDANCE]:[])],
    });await resourceLoader.reload();
    const errors=resourceLoader.getExtensions().errors;if(errors.length)throw new Error('Pi extension loading failed: '+errors.map(e=>e.error).join('; '));
    const manager=branchManager??(m.file&&existsSync(m.file)?SessionManager.open(m.file):SessionManager.create(m.cwd,join(this.dirs.sessions,m.id)));
    const repaired=trimSavedToolContext(manager);
    const reasoning=savedReasoning(m.reasoning,manager.buildSessionContext().thinkingLevel);requireThinking(model,reasoning.thinkingLevel);
    const created=await createAgentSession({cwd:m.cwd,agentDir:this.dirs.agent,modelRuntime:this.modelRuntime,model,thinkingLevel:reasoning.thinkingLevel,settingsManager,resourceLoader,sessionManager:manager,...(m.surface==='browser'?{tools:resourceLoader.getExtensions().extensions.flatMap(e=>[...e.tools.values()].filter(tool=>tool.definition.defaultActive!==false).map(tool=>tool.definition.name))}:{noTools:'builtin' as const,tools:['read','write','edit','bash','ls','find','grep'].map(name=>'+'+name)})});
    if(created.modelFallbackMessage){created.session.dispose();throw new Error('Pi attempted a model substitution: '+created.modelFallbackMessage);}
    if(created.session.model?.id!==m.selection.model||created.session.model?.provider!==m.selection.provider){created.session.dispose();throw new Error('Pi selected a different model.');}
    if(m.surface!=='browser')created.session.agent.toolExecution='sequential';
    if(m.title)created.session.setSessionName(m.title);m.reasoning=reasoning;m.file=created.session.sessionFile;this.save(m);
    record={memory,meta:m,session:created.session,manager,events:this.events(m),mcp,cancelled:false};this.loaded.set(m.id,record);
    let history=record.events;
    if(m.fork){m.memoryStartSeq??=history.at(-1)?.seq??0;this.save(m);history=history.filter(e=>e.seq>m.memoryStartSeq!);}
    await memory.append(history.flatMap(event=>piTranscriptEvent(event)));
    await created.session.bindExtensions({mode:'rpc',uiContext:this.interactions.ui(m.id),onError:error=>this.append(m,'runtime/error',{message:error.error})});
    record.execution=execution;execution.install(created.session);
    record.steering=new PiSteering(created.session);record.steering.install();
    record.reasoning=new PiReasoning(created.session,m.surface==='browser'?'augmentor-browser-pi':'augmentor-linux-pi',data=>record!.observation?.record('execution/reasoning',data));record.reasoning.install();
    provenance.attach(created.session);
    record.observation=observeSession(created.session,this.observations,m.id,
      ()=>({turnId:record!.turnId,selected:{...m.selection},permissionPreset:m.policy,toolBudget:{...TOOL_BUDGET,units:'unicode-code-points'},execution:record!.execution?.describe(),reasoning:record!.reasoning?.snapshot()}),
      observation=>this.publish(m.id,{method:'observation/event',payload:{sessionId:m.id,observation}}),
      message=>this.append(m,'runtime/warning',{message}),provenance);
    record.observation.record('session/load',{piVersion:'1.1.0',productVersion:RELEASE.version,
      surface:m.surface??'linux',policy:m.policy,...(m.fork?{fork:m.fork}:{})});
    if(mcp){const info=mcp.describe();if(info.servers.length||info.configurationErrors)record.observation.record('integration/mcp',info);if(info.configurationErrors)this.append(m,'runtime/warning',{message:'Managed MCP configuration contains errors. Some servers are unavailable; ordinary chat remains available.'});}
    if(repaired.length)record.observation.record('context/budget',{changes:repaired,units:'unicode-code-points',boundary:'before-session-owner-load'});
    created.session.subscribe(e=>{
      if(e.type==='message_start'&&e.message.role==='user'){
        const correction=record!.steering?.delivery(e.message);
        const requestId=correction??(!record!.initialDelivered?record!.activeRequestId:undefined);
        if(correction){record!.execution?.steerDelivered();record!.observation?.record('execution/steer-delivered',{clientRequestId:correction});}
        else if(requestId)record!.initialDelivered=true;
        if(requestId){this.queue(m).delivered(requestId);record!.reasoning?.admit(e.message);}
        const content=typeof e.message.content==='string'?[{type:'text',text:e.message.content}]:e.message.content;
        const submitted=requestId?this.queue(m).read(requestId).input:undefined,submittedContent=submitted?[{type:'text',text:submitted}]:undefined;
        this.append(m,'user/message',{source:{kind:'user',sessionId:m.id,...(requestId?{rpcId:requestId}:{})},content,...(submittedContent&&JSON.stringify(submittedContent)!==JSON.stringify(content)?{submittedContent}:{})});
      }
      if(e.type==='message_update'){
        const a=e.assistantMessageEvent;if(a.type==='text_delta')this.append(m,'assistant/chunk',{chunk:{type:'text-delta',text:a.delta}});
        if(a.type==='thinking_delta')this.append(m,'assistant/chunk',{chunk:{type:'reasoning-delta',text:a.delta}});
      }
      if(e.type==='message_end'&&e.message.role==='assistant'){
        this.append(m,'assistant/message',{message:{content:e.message.content,stopReason:e.message.stopReason}});
        record!.failed=e.message.stopReason==='error';if(record!.failed&&!record!.steering?.waiting)this.append(m,'runtime/error',{message:e.message.errorMessage||'Model request failed'});
      }
      if(e.type==='tool_execution_start')this.append(m,'tool/call',{name:e.toolName,toolCallId:e.toolCallId,...(e.parentToolCallId?{parentToolCallId:e.parentToolCallId}:{})});
      if(e.type==='tool_execution_end')this.append(m,'tool/result',{name:e.toolName,toolCallId:e.toolCallId,...(e.parentToolCallId?{parentToolCallId:e.parentToolCallId}:{}),isError:e.isError,result:{...e.result,content:e.result.content.map((part:Data)=>part.type==='image'?{type:'text',text:'[Tool image omitted from this display projection; inspect native evidence]'}:part)}});
    });return record;
  }
  async cancel(id:unknown,source='user'){
    const m=this.getMeta(id),queue=this.queue(m);queue.pause();const r=this.loaded.get(m.id);let aborting:Promise<void>|undefined;
    if(m.running&&r){if(r.preparingInput)r.interruptedInput=true;r.cancelled=true;r.execution?.cancel();for(const requestId of r.steering?.withdraw()??[])queue.withdrawSteer(requestId);r.session.abortCompaction();aborting=r.session.abort();}
    if(source==='user'||m.running)r?.observation?.record('control/stop',{wasRunning:m.running,source});this.desktopSpecialist.cancel('pi:'+m.id);this.interactions.cancel(m.id);
    if(r)await r.memory.activity('stop');if(m.surface!=='browser')await desktopControl('stop','pi:'+m.id).catch(()=>{});if(aborting)await aborting;return {accepted:!!aborting,paused:true};
  }
  private async steer(m:Meta,id:string,expectedTurnId:unknown){
    const r=this.loaded.get(m.id),turnId=promptIdentity(expectedTurnId),queue=this.queue(m);
    if(!m.running||!r||r.cancelled||r.phase==='settling'||r.turnId!==turnId)throw Error('The observed steering turn is no longer active.');
    const prior=queue.read(id);if(prior.steerTurnId===turnId&&prior.status!=='waiting')return {accepted:true,duplicate:true,turnId};
    if(r.steering?.waiting)throw Error('A correction is already waiting for its safe boundary.');
    r.steering!.validate(prior.input!);
    if(!queue.promote(id,turnId))return {accepted:true,duplicate:true,turnId};
    r.execution!.steerRequested();this.interactions.cancel(m.id);
    const pending=r.steering!.enqueue(id,prior.input!,result=>{
      if(result.action==='handled'){queue.handledSteer(id);r.execution!.steerHandled();this.append(m,'runtime/notice',{message:'The correction was handled by an input extension. No copy of that input was sent to the model.',submittedContent:[{type:'text',text:prior.input}],source:{kind:'user',rpcId:id},incomplete:false});}
      r.observation?.record('execution/steer-input',{clientRequestId:id,action:result.action,handler:result.handler,skill:result.skill,template:result.template});
    },error=>{r.failed=true;r.execution!.steerFailed();this.append(m,'runtime/error',{message:'Correction input preparation failed: '+String(error)});});
    r.observation?.record('execution/steer-requested',{clientRequestId:id,boundary:'provider-supersession; dispatched-tools-settle',input:'sdk-public-input-and-approved-resources'});
    this.append(m,'runtime/notice',{message:'Steering accepted. Obsolete generation is stopping; any dispatched tools will settle before the correction.',incomplete:false});
    const result=await pending;return {accepted:true,turnId,...(result.action==='handled'?{handled:true}:result.action==='cancelled'?{interruptedPreparation:true}:{})};
  }
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
    const m:Meta={reasoning:{...this.reasoningSettings(source)},memoryStartSeq:context.events.at(-1)?.seq??0,surface:source.surface,id:sid,cwd:source.cwd,file:context.file,selection:{...source.selection},title:((p.mode==='edit'?'Edit · ':'Branch · ')+source.title).slice(0,200),saved:false,policy:source.policy,updatedAt:Date.now(),requests:[],running:false,fork};
    const inherited=context.events.map(event=>event.type==='user/message'?{...event,data:{...event.data,source:{...event.data.source,sessionId:event.data.source?.sessionId??source.id}}}:event);
    writeFileSync(join(this.dirs.sessions,sid+'.events.jsonl'),inherited.map(e=>JSON.stringify(e)+'\n').join(''),{mode:0o600});
    // Pi defers writing branches with no assistant messages until a reply.
    if(context.manager&&context.file&&!existsSync(context.file))await this.load(m,context.manager);
    this.metadata.set(sid,m);this.save(m);
    if(p.mode==='reply')this.append(m,'turn/end',{reason:{kind:'completed'}});
    this.append(m,'session/title',{title:m.title});
    return this.branchRow(m);
  }
  branchRow(m:Meta){return {sessionId:m.id,cwd:m.cwd,agentPreset:m.surface==='browser'?'augmentor-browser-pi':'augmentor-linux-pi',title:m.title,saved:m.saved,running:m.running,selection:m.selection,fork:m.fork};}
  submit(r:Loaded,input:string,id:string){const m=r.meta;if(m.running)throw new Error('This conversation is already working');
    const reasoningPolicy=reasoningConfig(this.settings.reasoning),savedThinking=this.reasoningSettings(m);
    r.turnId=randomUUID();const queue=this.queue(m);queue.dispatch(id,r.turnId);
    m.running=true;r.cancelled=false;r.failed=false;r.initialDelivered=false;r.preparingInput=false;r.interruptedInput=false;r.phase='preparing';r.activeRequestId=id;m.requests=[...m.requests.slice(-99),id];m.updatedAt=Date.now();this.save(m);this.append(m,'turn/start',{requestId:id});queue.accepted(id);
    r.observation?.beginTurn({clientRequestId:id});
    r.execution?.begin(r.manager);
    r.reasoning?.begin(reasoningPolicy,savedThinking,this.settings.revision);
    if(!m.title){m.title=input.replace(/\s+/g,' ').slice(0,80);r.session.setSessionName(m.title);this.append(m,'session/title',{title:m.title});this.save(m);}
    r.task=(async()=>{let failed=false,attempted=false,handled=false;try{
      await r.memory.activity('foreground');if(r.cancelled)return;
      validateSteeringInput(r.session,input);r.phase='running';attempted=true;r.preparingInput=true;
      await r.session.prompt(input,{expandPromptTemplates:true,source:'rpc',preflightResult:disposition=>{
        r.preparingInput=false;
        if(r.cancelled)return;
        r.observation?.record('execution/input',{clientRequestId:id,disposition,expansion:'sdk-approved-skills-and-templates'});
        if(disposition==='handled'){
          handled=true;r.execution?.inputHandled();
          this.append(m,'runtime/notice',{message:'The input was handled by an input extension. No copy of that input was sent to the model.',disposition:'input-handled',submittedContent:[{type:'text',text:input}],source:{kind:'user',sessionId:m.id,rpcId:id},incomplete:false});
        }
      }});
    }catch(error){failed=true;this.append(m,'runtime/error',{message:String(error)});}finally{
      r.phase='settling';
      await r.memory.activity('stop');
      r.execution?.end(r.cancelled?'aborted':failed||r.failed||r.execution?.incomplete?'error':'completed');this.interactions.cancel(m.id);if(m.surface!=='browser')await desktopControl('stop','pi:'+m.id).catch(()=>{});const reason=r.cancelled?'aborted':failed||r.failed||r.execution?.incomplete?'error':'completed';
      // A terminal receipt is persisted before admitting another input. A crash
      // before this boundary produces an unknown receipt, never an automatic retry.
      const unknownInput=r.interruptedInput||attempted&&!r.initialDelivered&&!handled&&(r.cancelled||failed);r.preparingInput=false;
      queue.finish(id,unknownInput?'unconfirmed':reason==='aborted'?'cancelled':reason==='error'?'failed':'completed');if(reason!=='completed'||queue.uncertain)queue.pause();
      if(unknownInput)this.append(m,'runtime/notice',{message:'Input preparation stopped before model delivery. Its extension effects may be unknown; this prompt will not be replayed.',incomplete:true});
      m.running=false;m.updatedAt=Date.now();this.save(m);this.append(m,'turn/end',{reason:{kind:reason},requestId:id});r.observation?.record('turn/end',{reason,execution:r.execution?.describe()});r.turnId=undefined;r.activeRequestId=undefined;r.phase=undefined;
      if(!queue.paused)this.pump(m);
    }})();return {accepted:true,turnId:r.turnId};
  }
  private pump(m:Meta){
    if(this.pumping.has(m.id))return this.pumping.get(m.id)!;
    const run=this.serial.then(async()=>{
      const queue=this.queue(m);
      if(this.quiescing||this.improvements.busy||m.running||queue.paused||queue.uncertain||!queue.next)return;
      const item=queue.next;
      let r:Loaded;
      try{r=await this.load(m);}catch(error){queue.notSent(item.id);this.append(m,'runtime/error',{message:'Queued prompt was not sent: '+String(error)});return;}
      if(this.quiescing||this.improvements.busy||m.running||queue.paused||queue.uncertain||queue.next?.id!==item.id)return;
      this.submit(r,item.input!,item.id);
    });
    this.serial=run.catch(()=>{});this.pumping.set(m.id,run);
    void run.catch(error=>{this.queue(m).pause();console.warn('[augmentor-queue] Dispatch stopped:',String(error));}).finally(()=>this.pumping.delete(m.id));return run;
  }
  async dispatch(method:string,p:Data,id:string){
    if(this.quiescing&&method!=='host.describe')throw new Error('Runtime is closing for maintenance. No action was submitted.');
    if(method==='setup.test')return this.setup.test(p);
    if(method==='setup.cancel')return this.setup.cancel();
    if(method==='session.cancel')return this.cancel(p.sessionId);
    if(method==='prompt.cancelImprovement')return this.improvements.cancel(p.requestId,p.scopeId);
    if(method==='prompt.improvementStatus')return this.improvements.status(p.requestId);
    if(method==='interaction.respond')return this.interactions.answer(identifier(p.rpcId),p.value,identifier(p.sessionId));
    // Serialize state-changing preparations so two clients cannot create/replace an execution owner.
    const run=this.serial.then(()=>{if(this.quiescing&&method!=='host.describe')throw new Error('Runtime is closing for maintenance. No action was submitted.');return this.handle(method,p,id);});this.serial=run.catch(()=>{});
    const result=await run;return result instanceof SteeringReply?result.settled:result;
  }
  async handle(method:string,p:Data,id:string):Promise<any>{switch(method){
    case 'prompt.improve':{
      const model=await this.selected(p.selection);
      const instructions=(await promptCall('prompts.list')).improvement;
      const accepting=()=>{
        if(this.quiescing||[...this.metadata.values()].some(m=>m.running))throw Error('Open an idle Pi conversation before improving a draft.');
        if(p.sessionId){const m=this.getMeta(p.sessionId);if(m.selection.provider!==model.provider||m.selection.model!==model.id)throw Error('The selected conversation model changed.');}
      };
      accepting();
      return new SteeringReply(this.improvements.begin(p,{cwd:this.dirs.state,agentDir:this.dirs.agent,modelRuntime:this.modelRuntime,model,instructions,accepting}));
    }
    case 'observation.describe':return {protocol:OBSERVATION_PROTOCOL,revision:this.settings.revision,capturePayloads:this.observations.policy().capturePayloads,retention:DEFAULT_RETENTION,boundary:'provider-payload-after-hooks',capabilities:{metadata:true,payloads:true,reasoningDecisions:true,indexedMetadata:true,metadataSearch:'retained metadata only; payload bodies excluded; bounded scan cursors',payloadSearch:'retained redacted JSON snapshots; authenticated resumable cursors; explicit missing coverage',payloadVerification:'optional expected sha256; verified captured source blocks',attachments:'inline-payloads-only',parsedProviderEvents:true,providerEventCoverage:'parsed events supplied by the provider; 8 MiB per request; partial coverage reported',contextBoundaries:PROVENANCE_VERSION,contextBoundaryCoverage:'public SDK transforms, converted context, provider hooks and managed memory; 8 MiB aggregate snapshot bodies; partial states reported',sourceProvenance:false,nativeEntryLineage:'public SDK projection matched to before-transform redacted JSON; ambiguous matches reported',historicalCoverage:'recorded-during-managed-operation'},telemetry:{installReporting:'disabled-by-host',analytics:'disabled-by-host',cacheWarming:'off-by-host',providerRetries:0,sessionRetries:'disabled-by-host',networkAudit:'synthetic-core-test; configured extensions and live services require separate review'}};
    case 'observation.configure':{if(p.expectedRevision!==this.settings.revision)throw new Error('Settings changed. Refresh inspection settings.');if(typeof p.capturePayloads!=='boolean')throw new Error('Choose whether to retain private request payloads.');this.settings.observation={capturePayloads:p.capturePayloads};this.persistSettings();return this.handle('observation.describe',{},id);}
    case 'observation.search':{const m=this.getMeta(p.sessionId);return this.observations.search(m.id,{query:p.query,scope:p.scope,cursor:p.cursor,limit:p.limit});}
    case 'observation.list':{const m=this.getMeta(p.sessionId);return this.observations.page(m.id,{beforeSeq:p.beforeSeq,afterSeq:p.afterSeq,limit:p.limit,query:p.query});}
    case 'observation.payload':{const m=this.getMeta(p.sessionId);return this.observations.payload(m.id,identifier(p.eventId),p.offset,p.limit,p.sha256);}
    case 'observation.clear':{const m=this.getMeta(p.sessionId);this.observations.clear(m.id);return {cleared:true,scope:'diagnostic records only'};}
    case 'host.describe':return {protocol:PROTOCOL,pid:process.pid,activeTurns:[...this.metadata.values()].filter(m=>m.running).length,version:RELEASE.version,piVersion:'1.1.0',workspace:process.cwd(),capabilities:{queue:true,steering:true,reasoning:true,promptImprovement:true,inspection:true,indexedDisplayHistory:true,indexedNativeHistory:true,managedMcp:'native-managed-profile; browser-unavailable; catalog-only',toolOriginals:'native-current-branch; MCP-and-nested; before-result-hooks; 63-MiB-JSON-limit',originalHistorySearch:'Pi selected ancestry/all saved entries and raw display originals',linuxTools:process.env.AUGMENTOR_PI_LINUX_TOOLS!=='0',desktopInput:desktopCapabilities().available,osCustomisation:false,localRouteEnforcement:false},promptInput:{source:'rpc',expandPromptTemplates:true,skills:'approved-session-resources',extensionCommands:'rejected-in-durable-queue',disposition:'PromptOptions.preflightResult',stopDuringInput:'provider-blocked; await-handler-settlement; uncertain-receipt'},steering:{input:'sdk-public-input-and-approved-resources',sdkInputTransforms:true,inFlightTools:'settle',continuation:'same-AgentSession',identity:'owned-message-reference'},execution:{...EXECUTION_POLICY,providerRetries:0,sessionRetries:false,actionGuard:'automatic-recovery-and-steered-continuation',completion:'response-or-tool-handoff; task success requires verification'},toolBudget:{...TOOL_BUDGET,units:'unicode-code-points',originals:'native-current-branch',idleRepair:true},desktopSpecialist:{version:'augmentor-computer-use/1',available:desktopCapabilities().available,selectedModelOnly:true,requiresImageModel:true,maxConcurrent:1,evidence:'local-files',coreIntegration:false},desktopControl:desktopCapabilities(),configDir:this.dirs.config,stateDir:this.dirs.state};
    case 'host.prepareShutdown':
      if(this.improvements.busy)throw Error('Finish or cancel prompt improvement before shutting down the runtime');
      if([...this.metadata.values()].some(m=>m.running))throw new Error('Stop active Pi tasks before shutting down the runtime');
      this.quiescing=true;this.setup.cancel();return {accepted:true};
    case 'session.branch':return this.branch(p);
    case 'session.trimTools':{
      const m=this.getMeta(p.sessionId);if(m.running)throw Error('Stop the current turn before repairing tool context.');
      const loaded=this.loaded.get(m.id);
      if(!loaded&&(!m.file||!existsSync(m.file)))return {changes:[],units:'unicode-code-points',policy:TOOL_BUDGET};
      const manager=loaded?.manager??SessionManager.open(m.file!);
      const changes=trimSavedToolContext(manager);
      if(loaded){loaded.session.refreshContext();loaded.observation?.record('context/budget',{changes,units:'unicode-code-points',boundary:'manual-idle-repair'});}
      else try{this.observations.append(m.id,'context/budget',{changes,units:'unicode-code-points',boundary:'manual-cold-repair'});}catch{console.warn('[augmentor-inspection] Idle repair completed; its diagnostic observation could not be recorded.');}
      return {changes,units:'unicode-code-points',policy:TOOL_BUDGET};
    }
    case 'models.list':return this.catalog();
    case 'reasoning.describe':return {revision:this.settings.revision,config:reasoningConfig(this.settings.reasoning),source:{policy:'adaptive-reasoning/0.2.3',license:'MIT',adapter:'public-pi-prepareRequest-and-transformContext'},defaults:'unmapped models preserve their existing request level; no automatic model selection'};
    case 'reasoning.configure':{
      if(p.expectedRevision!==this.settings.revision)throw Error('Settings changed. Reload reasoning settings before saving.');
      if([...this.metadata.values()].some(m=>m.running))throw Error('Stop active chats before changing reasoning routes.');
      if(p.config===undefined)throw Error('Provide the complete Adaptive Reasoning configuration.');
      const config=reasoningConfig(p.config);
      for(const route of config.routes){const model=await this.selected(route);for(const level of Object.values(route.efforts))requireThinking(model,level);}
      this.settings.reasoning=config;this.persistSettings();return this.handle('reasoning.describe',{},id);
    }
    case 'setup.save':{
      if(!['read-only','workspace-write','danger-full-access'].includes(p.approvalMode))throw new Error('Choose an approval mode.');
      const checked=this.setup.checked(p.token);
      await this.handle('models.configure',{config:checked.config},id);
      this.settings.defaultModel=checked.selection;this.settings.defaultPreset=p.approvalMode;this.persistSettings();
      this.setup.saved();return {selection:checked.selection,catalog:await this.catalog()};
    }
    case 'models.validate':await this.selected(p);return {valid:true};
    case 'models.pin':{await this.selected(p);const key=p.provider+'/'+p.model;this.settings.pinned=this.settings.pinned.map((m:any)=>typeof m==='string'?m:m.provider+'/'+m.model).filter((m:string)=>m!==key);if(p.pinned)this.settings.pinned.push(key);this.persistSettings();return this.catalog();}
    case 'models.configure':{if(this.improvements.busy)throw Error('Finish or cancel prompt improvement before changing providers');if(!p.config||typeof p.config.providers!=='object'||Array.isArray(p.config.providers))throw new Error('Invalid providers configuration');if([...this.metadata.values()].some(m=>m.running))throw new Error('Stop active chats before changing providers');const file=join(this.dirs.agent,'models.json');const old=existsSync(file)?readFileSync(file,'utf8'):null;atomicJson(file,p.config);try{await this.modelRuntime.refresh({allowNetwork:false,signal:AbortSignal.timeout(10000)});if(this.modelRuntime.getError())throw new Error(this.modelRuntime.getError());}catch(error){if(old===null)unlinkSync(file);else writeFileSync(file,old,{mode:0o600});await this.modelRuntime.refresh({allowNetwork:false});throw error;}return this.catalog();}
    case 'models.reload':if(this.improvements.busy)throw Error('Finish or cancel prompt improvement before reloading models');await this.modelRuntime.refresh({allowNetwork:false,signal:AbortSignal.timeout(10000)});return this.catalog();
    case 'session.create':{const sid=identifier(p.sessionId);let m=this.metadata.get(sid);if(!m){await this.selected(p.selection);const cwd=resolve(text(p.cwd,4096));m={surface:p.surface==='browser'?'browser':'linux',id:sid,cwd,selection:p.selection,title:'',saved:false,policy:this.settings.defaultPreset,updatedAt:Date.now(),requests:[],running:false};this.metadata.set(sid,m);this.save(m);await this.load(m);}return {sessionId:sid};}
    case 'session.list':return {items:[...this.metadata.values()].sort((a,b)=>b.updatedAt-a.updatedAt).map(m=>({sessionId:m.id,cwd:m.cwd,agentPreset:m.surface==='browser'?'augmentor-browser-pi':'augmentor-linux-pi',title:m.title,updatedAt:m.updatedAt,saved:m.saved,running:m.running,blank:!m.title}))};
    case 'session.history':{const m=this.getMeta(p.sessionId);return this.history(m).page(p.maxMessages,p.beforeSeq);}
    case 'session.mcpInfo':{const m=this.getMeta(p.sessionId);if(m.surface==='browser')return {available:false,reason:'MCP is unavailable in browser-only conversations.'};return this.loaded.get(m.id)?.mcp?.describe()??{available:false,reason:'MCP bindings are not loaded for this saved conversation.'};}
    case 'session.originalSearch':case 'session.originalRead':{
      const m=this.getMeta(p.sessionId),source=p.source??'pi';if(!['pi','display'].includes(source))throw Error('Choose Pi entries or display originals.');
      const file=source==='pi'?m.file:join(this.dirs.sessions,m.id+'.events.jsonl');if(!file)return {available:false,reason:'This conversation has no saved native session.'};
      const cache=source==='pi'?this.nativeHistories:this.displayOriginals;let original=cache.get(m.id);if(!original||original.source!==file){original=new NativeHistory(file,join(this.dirs.state,source==='pi'?'native-index':'display-original-index',m.id),source==='display'?m.id:undefined);if(cache.size>=32)cache.delete(cache.keys().next().value!);cache.set(m.id,original);}
      if(method==='session.originalSearch')return original.search({query:p.query,scope:p.scope??(source==='display'?'all-entries':'selected-ancestry'),limit:p.limit,cursor:p.cursor,leafId:p.leafId===undefined?this.loaded.get(m.id)?.manager.getLeafId():p.leafId,nativeSessionId:p.sessionIdentity??(source==='pi'?p.nativeSessionId:undefined)});
      const result=original.read(identifier(p.entryId),{offset:p.offset,limit:p.limit,pathHash:p.pathHash,entryHash:p.entryHash,nativeSessionId:p.sessionIdentity??(source==='pi'?p.nativeSessionId:undefined)});if(!result.available)return result;const {nativeSessionId,...body}=result;return {...body,source,sessionIdentity:nativeSessionId,boundary:source==='pi'?result.boundary:'verified original display event; raw streamed fragments can be compacted in Chat; not Pi model context'};
    }
    case 'session.nativeHistory':case 'session.nativeRead':{
      const m=this.getMeta(p.sessionId);if(!m.file)return {available:false,reason:'This conversation has no saved native session.'};
      let native=this.nativeHistories.get(m.id);if(!native||native.source!==m.file){native=new NativeHistory(m.file,join(this.dirs.state,'native-index',m.id));if(this.nativeHistories.size>=32)this.nativeHistories.delete(this.nativeHistories.keys().next().value!);this.nativeHistories.set(m.id,native);}
      return method==='session.nativeRead'?native.read(identifier(p.entryId),{offset:p.offset,limit:p.limit,pathHash:p.pathHash,entryHash:p.entryHash,nativeSessionId:p.nativeSessionId}):native.page({limit:p.limit,cursor:p.cursor,leafId:p.leafId===undefined?this.loaded.get(m.id)?.manager.getLeafId():p.leafId,nativeSessionId:p.nativeSessionId});
    }
    case 'session.models':return {current:this.getMeta(p.sessionId).selection};
    case 'session.reasoning':return this.reasoningState(this.getMeta(p.sessionId));
    case 'session.selectReasoning':{
      const m=this.getMeta(p.sessionId);if(m.running)throw Error('Stop before changing thinking settings.');
      const saved=this.reasoningSettings(m);if(p.expectedRevision!==saved.revision)throw Error('Conversation reasoning settings changed. Reload before saving.');
      if(!['adaptive','manual'].includes(p.mode))throw Error('Choose Adaptive or Manual reasoning.');
      const level=thinkingLevel(p.thinkingLevel),model=await this.selected(m.selection);requireThinking(model,level);
      const loaded=await this.load(m);loaded.session.setThinkingLevel(level,{persist:false});
      m.reasoning={revision:saved.revision+1,mode:p.mode,thinkingLevel:level};this.save(m);return this.reasoningState(m);
    }
    case 'session.selectModel':{const m=this.getMeta(p.sessionId);if(m.running)throw new Error('Stop before changing models');const model=await this.selected(p);requireThinking(model,this.reasoningSettings(m).thinkingLevel);const previous=m.selection;const loaded=this.loaded.get(m.id);if(loaded)await loaded.session.setModel(model);else{m.selection={provider:p.provider,model:p.model};try{await this.load(m);}catch(error){m.selection=previous;this.save(m);throw error;}}m.selection={provider:p.provider,model:p.model};this.save(m);return {current:m.selection};}
    case 'session.prompt':{
      if(this.improvements.busy)throw Error('Finish or cancel prompt improvement before sending a chat prompt.');
      const m=this.getMeta(p.sessionId),requestId=promptIdentity(p.requestId??id);
      if(p.mode!==undefined&&!['queue','steer'].includes(p.mode))throw Error('Choose queue or steer mode.');
      const input=text(p.content?.filter((part:Data)=>part.type==='text').map((part:Data)=>part.text).join('\n')),queue=this.queue(m);
      const existing=queue.lookup(requestId,input);if(existing||m.requests.includes(requestId))return {accepted:true,duplicate:true,requestId};
      if(p.mode==='steer'){
        const r=this.loaded.get(m.id);if(!m.running||!r||r.cancelled||r.phase==='settling'||r.turnId!==p.expectedTurnId||queue.paused||queue.uncertain||r.steering?.waiting)throw Error('The observed steering turn is no longer available.');
        r.steering!.validate(input);queue.enqueue(requestId,input,true);return new SteeringReply(this.steer(m,requestId,p.expectedTurnId).then(result=>({...result,requestId})));
      }
      if(p.mode===undefined&&m.running)throw Error('This conversation is already working; use queue mode to add a waiting prompt.');
      if(p.resumeQueue!==undefined&&typeof p.resumeQueue!=='boolean')throw Error('Choose whether to resume the queue.');
      if(queue.uncertain)throw Error('A previous prompt has an unknown outcome. Inspect its history and explicitly acknowledge the interrupted receipt before sending more.');
      // Templates/skills use Session.prompt's SDK expansion, while registered
      // commands cannot bypass the persistent queue's admission/receipt rules.
      if(input.startsWith('/'))validateSteeringInput((await this.load(m)).session,input);
      queue.enqueue(requestId,input,m.running||queue.paused||!!queue.next);
      if(p.resumeQueue===true||(p.mode===undefined&&!m.running&&p.resumeQueue!==false))queue.resume();
      if(!m.running&&!queue.paused){
        let r:Loaded;try{r=await this.load(m);}catch(error){queue.notSent(requestId);throw error;}
        if(!queue.paused&&queue.next?.id===requestId)return {...this.submit(r,input,requestId),requestId};
        if(!queue.paused)this.pump(m);
      }
      return {accepted:true,queued:true,requestId};
    }
    case 'session.queue':return this.queueSnapshot(p.sessionId);
    case 'session.updateQueue':{const m=this.getMeta(p.sessionId),itemId=promptIdentity(p.itemId);if(p.action?.kind==='steer')return new SteeringReply(this.steer(m,itemId,p.expectedTurnId));if(p.action?.kind!=='remove')throw Error('Choose steer or remove.');this.queue(m).remove(itemId);return {accepted:true,...this.queueSnapshot(m.id)};}
    case 'session.continueQueue':{const m=this.getMeta(p.sessionId);this.queue(m).resume();this.pump(m);return {accepted:true};}
    case 'session.resolveQueue':{const m=this.getMeta(p.sessionId);if(m.running||p.acknowledgeUnknownOutcome!==true)throw Error('Inspect the saved history and explicitly acknowledge that the interrupted action outcome remains unknown.');this.queue(m).resolve(promptIdentity(p.itemId));this.append(m,'runtime/notice',{message:'The interrupted prompt receipt was acknowledged. Its action outcome may still be unknown. That prompt was not retried; waiting prompts remain paused.',incomplete:true});return {accepted:true};}
    case 'session.rename':{const m=this.getMeta(p.sessionId);m.title=text(p.title,200);this.loaded.get(m.id)?.session.setSessionName(m.title);this.save(m);this.append(m,'session/title',{title:m.title});return {title:m.title};}
    case 'chats.saved':{if(p.action&&p.action!=='state'){if(!['save','unsave'].includes(p.action))throw new Error('Invalid saved-chat action');const m=this.getMeta(p.sessionId);m.saved=p.action==='save';this.save(m);}return {saved:[...this.metadata.values()].filter(m=>m.saved).map(m=>m.id)};}
    case 'settings.describe':return {namespaces:[{ns:'permission',revision:this.settings.revision,value:{defaultPreset:this.settings.defaultPreset}},{ns:'prompt-library',revision:this.settings.revision,value:await promptCall('prompts.list')}]};
    case 'settings.mutate':{if(p.ns!=='permission'||p.expectedRevision!==this.settings.revision)throw new Error('Settings changed. Reopen the dialog.');const op=p.ops?.[0];if(p.ops.length!==1||op.op!=='set'||op.path?.join('.')!=='defaultPreset'||!['read-only','workspace-write','danger-full-access'].includes(op.value))throw new Error('Unsupported settings change');this.settings.defaultPreset=op.value;this.persistSettings();return {ok:true};}
    case 'prompts.list':case 'prompts.save':case 'prompts.delete':return promptCall(method,p,id);
    case 'prompts.improvementSave':return promptCall('prompts.improvement.save',p,id);
    default:throw new Error('Unsupported method: '+method);
  }}
  async close(){this.quiescing=true;this.setup.cancel();await this.improvements.close();for(const r of this.loaded.values()){await this.cancel(r.meta.id,'runtime-shutdown');await r.task;await r.session.extensionRunner.emit({type:'session_shutdown',reason:'quit'});r.memory.close();await r.memory.flush();r.observation?.record('session/close',{source:'runtime-shutdown'});r.observation?.dispose();r.reasoning?.dispose();r.steering?.dispose();r.execution?.dispose();r.session.dispose();}}
}
