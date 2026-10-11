// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {desktopCapabilities} from '../../desktop/src/capabilities.js';
import {desktopPackage,control as desktopControl} from '../../desktop/src/index.js';
import {DualMemoryClient} from '../../memory/src/dual.js';
import {piMemoryContext,piTranscriptEvent} from '../../memory/src/pi.js';
import {memoryPackage} from '../../memory/src/index.js';
import {promptCall} from '../../prompt-library/src/client.js';
import {listWorkspaceDirectory,createWorkspaceDirectory} from './workspace-picker.js';
import {WorkspaceRegistry,workspacePath} from './workspace-registry.js';
import {PiAttachments,submittedParts,IMAGE_LIMITS,FILE_LIMIT} from './attachments.js';
import {SessionOrganization} from './session-organization.js';
import {contextPreferences,contextPreferenceChange,CONTEXT_PREFERENCE_OPTIONS} from './context-preferences.js';
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
import {piScheduling} from './scheduling.js';
import {piLlamaCppSchemas} from './provider-compat.js';
import {Interactions} from './interactions.js';
import {isRoutineQuery} from './permissions.js';
import {branchContext} from './branches.js';
import {SetupConnections} from './setup.js';
import {RELEASE} from '../../contracts/src/release.js';
import {DisplayHistory} from './display-history.js';
import {NativeHistory} from './native-history.js';
import {ManagedMcp} from './mcp.js';
import {McpManagement,type McpManagementAction} from './mcp-management.js';
import {readMcpProfile,prepareMcpProfile,saveMcpProfile,mcpDigest} from './mcp-profile.js';
import {DesktopSpecialist,desktopBrief,DESKTOP_DELEGATION_GUIDANCE} from './desktop-specialist.js';
import {COMPUTER_USE_VERSION,type DesktopBrief,type DesktopResult} from '../../computer-use/src/contracts.js';
import {linuxDesktopExecutor} from '../../pi-linux/src/desktop-executor.js';
import {ObservationStore,OBSERVATION_PROTOCOL,DEFAULT_RETENTION} from '../../observation/src/store.js';
import {observeSession} from './observations.js';
import {ContextProvenance,PROVENANCE_VERSION} from './context-provenance.js';
import {piToolBudget,trimSavedToolContext,TOOL_BUDGET} from './tool-budget.js';
import {piReassessment} from './reassessment.js';
import {PiExecution,EXECUTION_POLICY,type ExecutionContract} from './execution.js';
import {PiPromptQueue,promptIdentity} from './queue.js';
import {PiCompactions} from './compaction.js';
import {PiSteering} from './steering.js';
import {validateSteeringInput} from './steering-input.js';
import {getSupportedThinkingLevels} from '@earendil-works/pi-ai';
import {PiReasoning,reasoningConfig,savedReasoning,thinkingLevel,requireThinking,type SavedReasoning} from './reasoning.js';
import {PiPromptImprovement} from './prompt-improvement.js';
import {piPlans,currentPlan,planProjection,PLAN_TYPE,PLAN_GUIDANCE} from './plans.js';
import {PiGoals,goalProjection,GOAL_GUIDANCE,GOAL_ROUND_TYPE} from './goals.js';
import {PiJobs,jobSpec,jobsExtension,shellJob,boundChild,JOB_GUIDANCE,type JobRecord,type JobSpec,type JobControl,type JobOutcome} from './jobs.js';
import type {Usage} from '@earendil-works/pi-ai';
const browserRecovery = readFileSync(new URL('../../../config/browser-recovery.md', import.meta.url), 'utf8');
interface Meta {delegation?:{parentId:string;jobId:string;allowedTools:string[];resources:Data};reasoning?:SavedReasoning;memoryStartSeq?:number;surface?:"linux"|"browser";id:string;cwd:string;file?:string;selection:Data;title:string;saved:boolean;policy:string;updatedAt:number;requests:string[];running:boolean;fork?:{sessionId:string;messageSeq:number;mode:'reply'|'edit'}}
interface Loaded {resources:Data;memory:DualMemoryClient;meta:Meta;session:AgentSession;manager:SessionManager;events:DisplayEvent[];goals:PiGoals;mcp?:ManagedMcp;reloading?:boolean;reloadError?:boolean;reload?:(options:{removeAutoCodemode:boolean})=>Promise<void>;reasoning?:PiReasoning;execution?:PiExecution;steering?:PiSteering;phase?:'preparing'|'running'|'settling';initialDelivered?:boolean;preparingInput?:boolean;interruptedInput?:boolean;observation?:ReturnType<typeof observeSession>;turnId?:string;activeRequestId?:string;cancelled:boolean;failed?:boolean;task?:Promise<void>}
/** Admission is serialized; extension preparation must not hold the host's
 * state lock while waiting for a UI answer, another RPC or an input handler.
 */
class SteeringReply {constructor(readonly settled:Promise<Record<string,unknown>>){} }
export class Host {
  readonly dirs=paths();
  readonly browser=new BrowserBroker();
  readonly metadata=new Map<string,Meta>();readonly loaded=new Map<string,Loaded>();
  readonly workspaces=new WorkspaceRegistry(join(this.dirs.state,'workspaces.json'),()=>[resolve(process.env.AUGMENTOR_PI_WORKSPACE||process.cwd()),...[...this.metadata.values()].map(m=>resolve(m.cwd))]);
  readonly organization=new SessionOrganization(join(this.dirs.state,'session-organization.json'));
  readonly attachments=new PiAttachments(this.dirs.state,(sid,part)=>this.events(this.getMeta(sid)).some(event=>event.type==='user/message'&&event.data.source?.sessionId!==sid&&(event.data.submittedContent??event.data.content??[]).some((p:Data)=>JSON.stringify(p)===JSON.stringify(part))));
  private uploads=0;
  async uploadFile(sid:string,data:Uint8Array,name:string,mediaType?:any){const m=this.getMeta(sid);if(this.quiescing||m.delegation||this.organization.archived(sid))throw Error('This conversation cannot accept uploads.');this.uploads++;try{return await (mediaType?this.attachments.uploadImage(sid,data,name,mediaType):this.attachments.upload(sid,data,name));}finally{this.uploads--;}}
  async attachmentImage(sid:string,ref:any){this.getMeta(sid);return this.attachments.image(sid,ref);}
  readonly interactions:Interactions;
  modelRuntime!:ModelRuntime;
  readonly setup=new SetupConnections(join(this.dirs.agent,'models.json'));
  settings:Data;
  readonly observations:ObservationStore;
  readonly improvements=new PiPromptImprovement(join(this.dirs.state,'prompt-improvements.json'));
  readonly mcpManagement:McpManagement;
  readonly compactions:PiCompactions;
  readonly jobs:PiJobs;
  private jobReceipts=new Map<string,Promise<void>>();
  private serial:Promise<unknown>=Promise.resolve();
  private quiescing=false;
  private mcpReloading=false;
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
    this.compactions=new PiCompactions(join(this.dirs.state,'compactions.json'),row=>{
      this.publish(row.sessionId,{method:'session/compaction',payload:{sessionId:row.sessionId,...this.compactions.describe(row.sessionId)}});
      try{const observation=this.observations.append(row.sessionId,'compaction/receipt',{...row},{});this.publish(row.sessionId,{method:'observation/event',payload:{sessionId:row.sessionId,observation}});}catch{/* Durable status remains available independently of diagnostic retention. */}
      const m=this.metadata.get(row.sessionId);if(m&&!['running','cancel-requested'].includes(row.state))this.append(m,'runtime/notice',{message:row.state==='completed'?(row.sdkOutcome==='rejected'?'Pi saved a native summary, then reported an SDK error. Inspect that boundary before continuing; waiting prompts remain paused.':'Pi compaction saved a native summary. Original history is preserved; waiting prompts remain paused.'):row.state==='unknown'?'Compaction outcome is unknown. Inspect the saved native history before acknowledging; nothing was replayed.':row.state==='cancelled'?'Pi compaction cancelled; no new native summary was saved.':'Pi compaction did not save a new native summary. Inspect the recorded request and native history.',compaction:{...row}});
    });
    this.mcpManagement=new McpManagement(join(this.dirs.state,'mcp-management.json'),row=>{
      this.publish(row.sessionId,{method:'mcp/management',payload:{sessionId:row.sessionId,receipt:row}});
      this.loaded.get(row.sessionId)?.observation?.record('integration/mcp-management',{...row});
      const m=this.metadata.get(row.sessionId);if(m&&!['running','cancel-requested'].includes(row.state))this.append(m,'runtime/notice',{message:'MCP '+row.action+' for '+row.server+': '+row.state+'. '+(row.result==='unknown'?'Its effects may be unknown; the command was not replayed.':'This is the SDK command report; connection and credential health need separate verification.'),mcpManagement:{...row}});
      if(!['running','cancel-requested'].includes(row.state))this.wakeGoals();
    });
    this.jobs=new PiJobs(join(this.dirs.state,'jobs'),row=>{
      this.publish(row.owner,{method:'job/updated',payload:{sessionId:row.owner,jobId:row.id,state:row.state,childId:row.childId}});
      if(['completed','failed','cancelled','unknown'].includes(row.state))void this.flushJobReceipts(row.owner).catch(()=>{}).finally(()=>this.wakeGoals());
    });
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
  contextPreferenceSnapshot(){return {ns:'dsh-context',revision:this.settings.revision,value:contextPreferences(this.settings.contextPreferences),writableFields:Object.keys(CONTEXT_PREFERENCE_OPTIONS)};}
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
  policy(m:Meta){return (pi:ExtensionAPI)=>{
    // Resource startup/reload may call the SDK's sendUserMessage API. Only
    // an admitted Host turn may deliver input into this conversation's loop.
    pi.on('input',()=>this.mcpReloading||!m.running?{action:'handled'}:undefined);
    pi.on('tool_call',async e=>{
    if(m.delegation&&!m.delegation.allowedTools.includes(e.toolName))return {block:true,reason:'This tool is outside the delegated job’s explicit grants.'};
    if((this.mcpReloading||!m.running)&&e.toolName!=='linux_desktop_stop')return {block:true,reason:'No admitted Host turn is available for this tool call.'};
    if(e.toolName==='linux_desktop_stop'){await Promise.all(this.jobs.list(m.id).filter(row=>row.kind==='desktop'&&['starting','running','stopping'].includes(row.state)).map(row=>this.jobs.cancel(m.id,row.id)));this.desktopSpecialist.cancel('pi:'+m.id);}
    if(m.surface==='browser'&&!['job_start','job_list','job_read','job_wait','job_cancel','get_goal','create_goal','update_goal','plan_read','plan_update','browser_tabs_list','browser_screenshot','browser_snapshot','browser_navigate','browser_click','browser_type','memory_recall','memory_source','tool_result_excerpt','home_devices','home_set','home_read','home_status','home_request','home_result','home_cancel'].includes(e.toolName))
      return {block:true,reason:'This browser chat can only use its browser tools.'};
    if((this.desktopSpecialist.busy()||this.jobs.busyKind('desktop'))&&['linux_desktop_connect','linux_desktop_snapshot','linux_desktop_action'].includes(e.toolName))return {block:true,reason:'A desktop specialist owns the desktop. Wait for it or Stop it before using direct desktop tools.'};
    if(m.surface!=='browser'&&this.loaded.get(m.id)?.mcp?.isRead(e.toolName))return;
    if(['job_list','job_read','job_wait','job_cancel','job_start','get_goal','plan_read','home_devices','home_read','home_status','home_result','home_cancel','desktop_delegate','desktop_evidence','memory_recall','memory_source','tool_result_excerpt','read','ls','find','grep','linux_system_profile','linux_desktop_observe','linux_desktop_connect','linux_desktop_snapshot','linux_desktop_stop','ask_user','browser_tabs_list','browser_screenshot','browser_snapshot'].includes(e.toolName))return;
    if(e.toolName==='bash'&&isRoutineQuery(e.input.command))return;
    if(m.policy==='read-only')return {block:true,reason:'Read-only chat: actions that can change state are disabled.'};
    if(['home_request','home_set'].includes(e.toolName))return; // Persistent NAS pairing grants the scoped Home capability.
    if(m.policy!=='danger-full-access'&&!await this.interactions.approve(m.delegation?.parentId??m.id,e.toolName,e.input,m.id))return {block:true,reason:'Action not approved, cancelled or no user interface connected.'};
  });};}
  async load(m:Meta,branchManager?:SessionManager){let record=this.loaded.get(m.id);if(record){record.mcp?.assertReady();return record;}
    if(this.mcpReloading)throw Error('Finish MCP session reload before loading another conversation.');
    if(m.surface!=='browser'&&this.mcpManagement.busy)throw Error('Finish MCP management before loading another Native conversation.');
    const model=await this.selected(m.selection);
    const memory=new DualMemoryClient('pi:'+m.id,m.cwd,undefined,message=>console.warn('[augmentor-memory]',message));
    const mcp=m.surface==='browser'?undefined:new ManagedMcp(this.dirs.agent,this.dirs.state,m.id,(event,retained)=>{
      record?.observation?.record('integration/mcp-authorization',{...event,retained});
      if(!retained)this.append(m,'runtime/warning',{message:'An MCP authorization observation could not be saved. Its historical evidence has a gap.'});
      if(event.state==='sign-in-required'||event.state==='refresh-failed')this.append(m,'runtime/notice',{message:event.state==='sign-in-required'?'An MCP server requires sign-in. Inspect its recorded authorization status before another action.':'An MCP authorization refresh failed. Inspect its recorded status before another action.'});
    },url=>this.mcpManagement.authorizationUrl(m.id,url),(event,retained)=>{
      record?.observation?.record('integration/mcp-connection',{...event,retained});
      this.publish(m.id,{method:'mcp/connection',payload:{sessionId:m.id,observation:{...event},retained}});
      if(!retained)this.append(m,'runtime/warning',{message:'An MCP connection observation could not be saved. Its historical evidence has a gap.'});
    },()=>({hostTurnId:record?.turnId,hostRequestId:record?.activeRequestId,modelRequestObservationId:record?.observation?.currentRequestId()}));
    mkdirSync(m.cwd,{recursive:true,mode:0o700});
    const execution:PiExecution=new PiExecution((kind,data,payload)=>record?.observation?.record(kind,data,payload),(message,incomplete)=>{record?.observation?.record('execution/notice',{message,incomplete});this.append(m,'runtime/notice',{message,incomplete});},{},undefined,(name):ExecutionContract|undefined=>{
      if(name==='desktop_delegate'||name==='desktop_evidence')return {effect:()=>name==='desktop_evidence'?'read':'change',outcome:(_args,result)=>{try{const part=result.content.find(part=>part.type==='text');const data=part?.type==='text'?JSON.parse(part.text):undefined,id=(data?.jobId??data?.result?.jobId);if(typeof id!=='string')return {status:'unknown'};const row=this.jobs.lookup(m.id,id);return {status:['starting','running','stopping'].includes(row.state)?'running':row.state==='completed'?'completed':row.state==='unknown'?'unknown':'failed',jobId:id};}catch{return {status:'unknown'};}}};
      const definition=resourceLoader.getExtensions().extensions.flatMap(extension=>[...extension.tools.values()]).find(tool=>tool.definition.name===name)?.definition;
      return (definition as (typeof definition & {augmentorExecution?:ExecutionContract}))?.augmentorExecution??(mcp?.isRead(name)?{effect:()=> 'read'}:undefined);
    },(toolCallId,toolName)=>mcp?.takeResultIdentity(toolCallId,toolName));
    const settingsManager=SettingsManager.inMemory({enableInstallTelemetry:false,enableAnalytics:false,cacheWarming:'off',retry:{enabled:false,provider:{maxRetries:0}},compaction:{enabled:!m.delegation},packages:[],defaultProjectTrust:'never'});
    const resources=m.delegation?.resources??readJson<Data>(join(this.dirs.config,'resources.json'),{sources:[],skills:[]});
    const goals=new PiGoals({getBranch:()=>manager.getBranch(),appendCustomEntry:(type,data)=>manager.appendCustomEntry(type,data),getSessionId:()=>manager.getSessionId()},()=>{this.publish(m.id,{method:'goal/updated',payload:{sessionId:m.id}});record?.observation?.record('goal/update',{activation:goals.armed?'armed':'disarmed'});});
    const provenance=new ContextProvenance(()=>this.observations.policy().capturePayloads);
    if(!Array.isArray(resources.sources)||!Array.isArray(resources.skills))throw new Error('Invalid Pi resource configuration');
    const resourceLoader:DefaultResourceLoader=new DefaultResourceLoader({cwd:m.cwd,agentDir:this.dirs.agent,settingsManager,noExtensions:true,noSkills:true,noContextFiles:true,noThemes:true,
      additionalExtensionPaths:m.surface==='browser'?[]:resources.sources,additionalSkillPaths:m.surface==='browser'?[]:resources.skills,additionalPromptTemplatePaths:[privateDir(join(this.dirs.agent,'prompts'))],
      extensionFactories:[piScheduling,piLlamaCppSchemas,this.policy(m),...(m.delegation?[]:[jobsExtension(m.id,this.jobs,(spec,signal)=>this.startJob(m,spec,signal))]),goals.extension,piPlans(revision=>{this.publish(m.id,{method:'plan/updated',payload:{sessionId:m.id,revision}});record?.observation?.record('planning/update',{revision});}),piToolBudget(changes=>record?.observation?.record('context/budget',{changes,units:'unicode-code-points'})),piReassessment(data=>record?.observation?.record('execution/checkpoint',data)),execution.extension,homePackage('pi:'+m.id),pi=>memoryPackage(pi,m.fork?undefined:'pi:'+m.id),piMemoryContext(memory,!m.fork,contribution=>provenance.memory(contribution)),...(mcp?mcp.factories():[]),...(m.surface==='browser'?[this.browser.package(m.delegation?.parentId??m.id)]:process.env.AUGMENTOR_PI_LINUX_TOOLS==='0'?[]:[linuxPackage(this.backend),desktopPackage('pi:'+m.id),this.desktopSpecialist.package({owner:'pi:'+m.id,cwd:m.cwd,agentDir:this.dirs.agent,modelRuntime:this.modelRuntime,policy:m.policy,approve:(name,args)=>this.interactions.approve(m.id,name,args),cancelInteractions:()=>this.interactions.cancel(m.id),progress:info=>this.append(m,'desktop/progress',info)},(brief,toolCallId,signal)=>this.awaitDesktopJob(m,brief,toolCallId,signal))]),{name:'augmentor-context-observer',factory:provenance.extension}],
      appendSystemPrompt:[browserRecovery,PLAN_GUIDANCE,GOAL_GUIDANCE,...(m.delegation?['You are a bounded delegated worker. Follow the supplied task and all constraints. Do not start jobs, persistent goals or other workers. Your tools are explicitly granted by the parent conversation. Report failures and unknown outcomes; verify changes.']:[JOB_GUIDANCE]),m.surface==='browser'?'You are Augmentor Agent for Browser, powered by Pi. Use the browser tools to inspect and act in the connected visible browser. Read a fresh snapshot before actions. Stop on stale targets or denied actions. Report unknown outcomes honestly; do not replay actions.': `You are Augmentor Agent Desktop, powered by Pi. The operating system is ${process.platform}. Use tools to check actual facts. Keep the user informed. Use linux_browser_open for visible Chromium; never claim dispatch proves a page loaded. Use the platform accessibility observations for desktop structure. Stop on stale targets or denied actions. Use linux_desktop_connect and the user’s OS consent for desktop control. Use fresh screenshots before each action, then verify the result. A model must support image input. Stop on focus changes; never replay an unknown input outcome. Ask the user only when required information is missing.`,...(m.surface!=='browser'&&process.env.AUGMENTOR_PI_LINUX_TOOLS!=='0'?[DESKTOP_DELEGATION_GUIDANCE]:[])],
    });await resourceLoader.reload();
    const errors=resourceLoader.getExtensions().errors;if(errors.length)throw new Error('Pi extension loading failed: '+errors.map(e=>e.error).join('; '));
    const manager=branchManager??(m.file&&existsSync(m.file)?SessionManager.open(m.file):SessionManager.create(m.cwd,join(this.dirs.sessions,m.id)));
    const repaired=trimSavedToolContext(manager);
    const reasoning=savedReasoning(m.reasoning,manager.buildSessionContext().thinkingLevel);requireThinking(model,reasoning.thinkingLevel);
    const created=await createAgentSession({cwd:m.cwd,agentDir:this.dirs.agent,modelRuntime:this.modelRuntime,model,thinkingLevel:reasoning.thinkingLevel,settingsManager,resourceLoader,sessionManager:manager,...(m.surface==='browser'?{tools:resourceLoader.getExtensions().extensions.flatMap(e=>[...e.tools.values()].filter(tool=>tool.definition.defaultActive!==false).map(tool=>tool.definition.name))}:{noTools:'builtin' as const,tools:['read','write','edit','bash','ls','find','grep'].map(name=>'+'+name)})});
    if(created.modelFallbackMessage){created.session.dispose();throw new Error('Pi attempted a model substitution: '+created.modelFallbackMessage);}
    if(created.session.model?.id!==m.selection.model||created.session.model?.provider!==m.selection.provider){created.session.dispose();throw new Error('Pi selected a different model.');}
    if(m.surface!=='browser')created.session.agent.toolExecution='sequential';
    if(m.delegation){const callable=created.session.getCallableToolNames();if(m.delegation.allowedTools.some(name=>!callable.includes(name))){created.session.dispose();throw Error('A delegated tool grant is unavailable in the child resource registry.');}created.session.setActiveToolsByName(m.delegation.allowedTools);}
    if(m.title)created.session.setSessionName(m.title);m.reasoning=reasoning;m.file=created.session.sessionFile;this.save(m);
    record={resources:structuredClone(resources),memory,meta:m,session:created.session,manager,events:this.events(m),goals,mcp,cancelled:false};this.loaded.set(m.id,record);
    let history=record.events;
    if(m.fork){m.memoryStartSeq??=history.at(-1)?.seq??0;this.save(m);history=history.filter(e=>e.seq>m.memoryStartSeq!);}
    await memory.append(history.flatMap(event=>piTranscriptEvent(event)));
    await created.session.bindExtensions({mode:'rpc',uiContext:this.interactions.ui(m.delegation?.parentId??m.id,m.id),onError:error=>{if(record?.reloading)record.reloadError=true;this.append(m,'runtime/error',{message:record?.reloading?'A Pi resource reported a reload problem. Inspect the configuration receipt before continuing.':error.error});}});
    record.execution=execution;
    record.steering=new PiSteering(created.session);
    record.reasoning=new PiReasoning(created.session,m.surface==='browser'?'augmentor-browser-pi':'augmentor-linux-pi',data=>record!.observation?.record('execution/reasoning',data));
    const installBindings=()=>{
    execution.install(created.session);record!.steering!.install();record!.reasoning!.install();
    provenance.attach(created.session);
    record.observation=observeSession(created.session,this.observations,m.id,
      ()=>({turnId:record!.turnId,compactionId:this.compactions.activeId(m.id),selected:{...m.selection},permissionPreset:m.policy,toolBudget:{...TOOL_BUDGET,units:'unicode-code-points'},execution:record!.execution?.describe(),reasoning:record!.reasoning?.snapshot()}),
      observation=>this.publish(m.id,{method:'observation/event',payload:{sessionId:m.id,observation}}),
      message=>this.append(m,'runtime/warning',{message}),provenance);
    return record!.observation;
    };
    const installed=installBindings();
    record.reload=async options=>{
      record!.goals.disarm();record!.reloading=true;record!.reloadError=false;
      try{
      // Unwind in reverse composition order; the public reload replaces the
      // runner captured by execution's nested-tool hooks, but keeps this owner.
      record!.observation?.dispose();record!.observation=undefined;
      record!.reasoning?.dispose();record!.steering?.dispose();execution.dispose();
      await created.session.reload({beforeSessionStart:()=>{
        if(options.removeAutoCodemode)created.session.setActiveToolsByName(created.session.getActiveToolNames().filter(name=>name!=='codemode'));
        installBindings();
      }});
      if(record!.reloadError||resourceLoader.getExtensions().errors.length)throw Error('An approved Pi resource failed to reload. Repair it before applying the configuration again.');
      const reloadedModel=created.session.model;
      if(!reloadedModel||reloadedModel.provider!==m.selection.provider||reloadedModel.id!==m.selection.model)throw Error('A reloaded resource changed the selected model. Choose the intended model explicitly before continuing.');
      requireThinking(reloadedModel,this.reasoningSettings(m).thinkingLevel);
      created.session.agent.toolExecution='sequential';
      const recordReload=()=>record!.observation?.record('session/reload',{reason:'mcp-session-options',piVersion:'1.1.0'});recordReload();
      }finally{record!.reloading=false;}
    };
    installed.record('session/load',{piVersion:'1.1.0',productVersion:RELEASE.version,
      surface:m.surface??'linux',policy:m.policy,...(m.fork?{fork:m.fork}:{})});
    if(mcp){const info=mcp.describe();if(info.servers.length||info.configurationErrors)installed.record('integration/mcp',info);if(info.configurationErrors)this.append(m,'runtime/warning',{message:'Managed MCP configuration contains errors. Some servers are unavailable; ordinary chat remains available.'});}
    if(repaired.length)installed.record('context/budget',{changes:repaired,units:'unicode-code-points',boundary:'before-session-owner-load'});
    created.session.subscribe(e=>{
      if(e.type==='message_start'&&e.message.role==='user'){
        const correction=record!.steering?.delivery(e.message);
        const requestId=correction??(!record!.initialDelivered?record!.activeRequestId:undefined);
        if(correction){record!.execution?.steerDelivered();record!.observation?.record('execution/steer-delivered',{clientRequestId:correction});}
        else if(requestId)record!.initialDelivered=true;
        if(requestId){this.queue(m).delivered(requestId);record!.reasoning?.admit(e.message);}
        const content=typeof e.message.content==='string'?[{type:'text',text:e.message.content}]:e.message.content;
        const admitted=requestId?this.queue(m).read(requestId):undefined,submittedContent=admitted?submittedParts(admitted.input??'',admitted.attachments):undefined;
        const goalSource=requestId&&!correction?this.queue(m).read(requestId).goalSource:undefined;
        if(goalSource){try{record!.goals.admit(goalSource,requestId!,e.message);}catch{record!.goals.disarm();record!.failed=true;record!.execution?.cancel();this.append(m,'runtime/error',{message:'Goal admission could not be saved or replayed. Inspect its original; no automatic continuation will be replayed.'});void record!.session.abort().catch(()=>{});}}
        this.append(m,'user/message',{source:{...(goalSource??{kind:'user'}),sessionId:m.id,...(requestId?{rpcId:requestId}:{})},content,...(submittedContent&&JSON.stringify(submittedContent)!==JSON.stringify(content)?{submittedContent}:{})});
      }
      if(e.type==='message_update'){
        const a=e.assistantMessageEvent,requestId=record!.observation?.currentRequestId();
        if(a.type==='text_delta')this.append(m,'assistant/chunk',{requestId,chunk:{type:'text-delta',text:a.delta}});
        if(a.type==='thinking_delta')this.append(m,'assistant/chunk',{requestId,chunk:{type:'reasoning-delta',text:a.delta}});
      }
      if(e.type==='message_end'&&e.message.role==='assistant'){
        this.append(m,'assistant/message',{requestId:record!.observation?.currentRequestId(),message:{content:e.message.content,stopReason:e.message.stopReason,timestamp:e.message.timestamp,usage:e.message.usage}});
        record!.failed=e.message.stopReason==='error';if(record!.failed&&!record!.steering?.waiting)this.append(m,'runtime/error',{message:e.message.errorMessage||'Model request failed'});
      }
      if(e.type==='tool_execution_start')this.append(m,'tool/call',{name:e.toolName,toolCallId:e.toolCallId,...(e.parentToolCallId?{parentToolCallId:e.parentToolCallId}:{})});
      if(e.type==='tool_execution_end')this.append(m,'tool/result',{name:e.toolName,toolCallId:e.toolCallId,...(e.parentToolCallId?{parentToolCallId:e.parentToolCallId}:{}),isError:e.isError,result:{...e.result,content:e.result.content.map((part:Data)=>part.type==='image'?{type:'text',text:'[Tool image omitted from this display projection; inspect native evidence]'}:part)}});
    });void this.flushJobReceipts(m.id).catch(()=>{});return record;
  }
  private savedJobEntry(m:Meta,id:string){
    if(!m.file||!existsSync(m.file))return false;
    try{const result=new NativeHistory(m.file,join(this.dirs.state,'job-native-index',m.id)).read(id,{limit:8192});return result.available&&!result.hasMore&&JSON.parse(result.text).id===id;}catch{return false;}
  }
  private async flushJobReceipts(owner:string):Promise<void>{
    const r=this.loaded.get(owner);if(!r||r.meta.running||r.meta.delegation)return;
    const pending=this.jobReceipts.get(owner);if(pending)return pending;
    const run=Promise.resolve().then(async()=>{
      for(const row of this.jobs.pendingAccounting(owner)){
        if(r.meta.running)return;
        const note='augmentor-job:'+row.id;
        if(row.usage&&!row.usageAccounted){
          const entry=r.manager.getBranch().find(entry=>entry.type==='usage'&&entry.kind==='delegation'&&entry.note===note)??r.manager.appendUsage('delegation',row.usage.provider,row.usage.model,row.usage.value,note);
          if(this.savedJobEntry(r.meta,entry.id))this.jobs.accounted(owner,row.id,{usageAccounted:true});
        }
        if(!row.notified){
          const exists=r.manager.getBranch().some(entry=>entry.type==='custom_message'&&entry.customType==='augmentor/job-settled-v1'&&(entry.details as Data)?.jobId===row.id);
          if(!exists)await r.session.sendCustomMessage({customType:'augmentor/job-settled-v1',content:'Background job '+row.id+' reported '+row.state+'. '+(row.reason??'Inspect job_read and verify the result.')+' This receipt does not start another turn.',display:true,details:{jobId:row.id,owner,state:row.state}},{triggerTurn:false});
          const entry=r.manager.getBranch().find(entry=>entry.type==='custom_message'&&entry.customType==='augmentor/job-settled-v1'&&(entry.details as Data)?.jobId===row.id);
          if(!entry)throw Error('Job notification was accepted but is not visible in native history yet.');
          if(!this.savedJobEntry(r.meta,entry.id))continue;
          this.jobs.accounted(owner,row.id,{notified:true});
          this.append(r.meta,'runtime/notice',{message:'Background '+row.spec.kind+' job '+row.id+' reported '+row.state+'. Inspect Jobs before another attempt.',jobId:row.id});
        }
      }
    }).finally(()=>this.jobReceipts.delete(owner));this.jobReceipts.set(owner,run);return run;
  }
  private async startJob(m:Meta,input:unknown,signal?:AbortSignal){
    if(m.delegation)throw Error('Delegated jobs cannot create other workers.');
    if(this.quiescing||this.mcpReloading||this.improvements.busy||this.mcpManagement.busy)throw Error('Finish runtime maintenance before starting a background job.');
    const spec=jobSpec(input),parent=this.loaded.get(m.id);if(!parent)throw Error('Load the parent conversation before starting a job.');
    const existing=this.jobs.existing(m.id,spec);if(existing)return existing;
    const readTool=(name:string)=>['read','ls','find','grep','plan_read','get_goal','tool_result_excerpt','memory_recall','memory_source','browser_tabs_list','browser_snapshot','browser_screenshot'].includes(name)||parent.mcp?.isRead(name)||parent.session.getToolDefinition(name)?.annotations?.readOnlyHint===true;
    let changes=false;
    if(spec.kind==='shell'){
      if(m.surface==='browser')throw Error('Background shell commands are unavailable in browser-only conversations.');
      changes=!isRoutineQuery(spec.task);
    }else if(spec.kind==='desktop'){
      if(m.surface==='browser'||!desktopCapabilities().available)throw Error('Desktop specialist jobs are unavailable on this surface or platform.');
      if(!parent.session.model?.input.includes('image'))throw Error('Desktop delegation requires the selected model to support image input. No model was substituted.');
      if(this.jobs.busyKind('desktop')||this.desktopSpecialist.busy())throw Error('A desktop specialist is already active. Stop or settle it before another run.');
      changes=true;
    }else{
      const callable=parent.session.getCallableToolNames();
      if(spec.allowedTools.some(name=>!callable.includes(name)||name.startsWith('job_')||['desktop_delegate','create_goal','update_goal'].includes(name)))throw Error('A delegated tool is unavailable or would grant recursive execution.');
      changes=spec.allowedTools.some(name=>!readTool(name));
    }
    if(changes&&m.policy==='read-only')throw Error('Read-only chat cannot grant changing tools or a changing background command.');
    if(changes&&m.policy!=='danger-full-access'&&!await this.interactions.approve(m.id,'background_'+spec.kind,{task:spec.task,allowedTools:spec.allowedTools,limits:spec.limits}))throw Error('Background job was not approved.');
    signal?.throwIfAborted();
    const result=this.jobs.start(m.id,spec,(row,control)=>spec.kind==='shell'?shellJob(m.cwd,row,control):spec.kind==='desktop'?this.desktopJob(structuredClone(m),row,control):this.delegateJob(structuredClone(m),row,control));
    if(!result.duplicate){parent.manager.appendCustomEntry('augmentor/job-start-v1',{jobId:result.job.id,kind:spec.kind,requestId:spec.requestId,allowedTools:spec.allowedTools,limits:spec.limits,selection:{...m.selection},permissionPreset:m.policy});parent.observation?.record('job/start',{jobId:result.job.id,kind:spec.kind,allowedTools:spec.allowedTools,limits:spec.limits});}
    return result;
  }
  private async awaitDesktopJob(m:Meta,brief:DesktopBrief,toolCallId:string,signal?:AbortSignal):Promise<DesktopResult>{
    const requestId='desktop:'+createHash('sha256').update((this.loaded.get(m.id)?.turnId??'idle')+'\0'+toolCallId).digest('hex');
    const started=await this.startJob(m,{requestId,kind:'desktop',task:JSON.stringify(desktopBrief(brief)),allowedTools:[]},signal);
    while(true){try{const read=await this.jobs.wait(m.id,started.job.id,30000,signal);if(!read.timedOut||['completed','failed','cancelled','unknown'].includes(read.job.state))break;}catch(error){if(!signal?.aborted)throw error;await this.jobs.cancel(m.id,started.job.id);break;}}
    const job=this.jobs.lookup(m.id,started.job.id);
    return {...(job.desktop??{version:COMPUTER_USE_VERSION,runId:'',status:job.state==='cancelled'?'cancelled':job.state==='failed'?'failed':'unknown',summary:job.reason??'Desktop job has no confirmed structured outcome.',verification:'Inspect its saved receipt and child originals before another attempt.',verificationSource:'runtime',observedAfterLastAction:false,actionAttempted:false,model:{provider:m.selection.provider,id:m.selection.model},counts:{requests:job.requests,tools:job.tools,images:0}}),...(job.state==='unknown'?{status:'unknown' as const,summary:job.reason??'Desktop settlement is unknown.'}:{}),jobId:job.id,childId:job.childId};
  }
  private async desktopJob(parent:Meta,row:JobRecord,control:JobControl):Promise<JobOutcome>{
    control.signal.throwIfAborted();const model=await this.selected(parent.selection);control.signal.throwIfAborted();
    const m:Meta={id:'job-'+row.id,delegation:{parentId:parent.id,jobId:row.id,allowedTools:[...row.spec.allowedTools],resources:{sources:[],skills:[]}},reasoning:{...this.reasoningSettings(parent)},surface:'linux',cwd:parent.cwd,selection:{...parent.selection},title:'Desktop specialist '+row.id,saved:false,policy:parent.policy,updatedAt:Date.now(),requests:[],running:false};
    const manager=SessionManager.create(m.cwd,privateDir(join(this.dirs.sessions,m.id)));m.file=manager.getSessionFile();this.metadata.set(m.id,m);this.save(m);control.update({childId:m.id});
    const effective=thinkingLevel(this.loaded.get(parent.id)?.reasoning?.snapshot()?.thinkingLevel??m.reasoning!.thinkingLevel);requireThinking(model,effective);
    const result=await this.desktopSpecialist.run({owner:'pi:'+parent.id,cwd:m.cwd,agentDir:this.dirs.agent,modelRuntime:this.modelRuntime,model,policy:parent.policy,approve:(name,args)=>this.interactions.approve(parent.id,name,args,m.id),cancelInteractions:()=>this.interactions.cancel(m.id),progress:info=>this.append(parent,'desktop/progress',{...info,jobId:row.id,childId:m.id}),tracking:{jobId:row.id,childId:m.id,manager,thinkingLevel:effective,limits:{requests:row.spec.limits.maxRequests,tools:row.spec.limits.maxTools,timeoutMs:row.spec.limits.timeoutMs},maxTotalOutputTokens:row.spec.limits.maxOutputTokens,
      checkpoint:(result,outputTokens,usage)=>control.update({requests:result.counts.requests,tools:result.counts.tools,outputTokens,desktop:{...structuredClone(result),jobId:row.id,childId:m.id},usage:{provider:model.provider,model:model.id,value:structuredClone(usage)}}),
      onSession:(session,result)=>{
        m.running=true;this.save(m);this.append(m,'turn/start',{requestId:'desktop:'+row.id,jobId:row.id,parentId:parent.id});
        const observation=observeSession(session,this.observations,m.id,()=>({turnId:row.id,selected:m.selection,permissionPreset:m.policy,execution:{specialist:true,limits:row.spec.limits}}),event=>this.publish(parent.id,{method:'job/observation',payload:{sessionId:parent.id,childId:m.id,jobId:row.id,observation:event}}),message=>this.append(m,'runtime/warning',{message}));observation.beginTurn({jobId:row.id,parentId:parent.id});
        const unsub=session.subscribe(event=>{
          if(event.type==='message_start'&&event.message.role==='user')this.append(m,'user/message',{source:{kind:'delegation',sessionId:m.id,parentId:parent.id,jobId:row.id},content:event.message.content});
          if(event.type==='message_update'&&event.assistantMessageEvent.type==='text_delta')this.append(m,'assistant/chunk',{chunk:{type:'text-delta',text:event.assistantMessageEvent.delta}});
          if(event.type==='message_end'&&event.message.role==='assistant')this.append(m,'assistant/message',{message:{content:event.message.content,stopReason:event.message.stopReason}});
          if(event.type==='tool_execution_start')this.append(m,'tool/call',{name:event.toolName,toolCallId:event.toolCallId});
          if(event.type==='tool_execution_end')this.append(m,'tool/result',{name:event.toolName,toolCallId:event.toolCallId,isError:event.isError,result:{...event.result,content:event.result.content.map((part:Data)=>part.type==='image'?{type:'text',text:'[Specialist image preserved in native history and desktop evidence]'}:part)}});
        });
        return ()=>{unsub();observation.record('turn/end',{status:result.status,jobId:row.id});observation.dispose();m.running=false;this.save(m);this.append(m,'turn/end',{reason:{kind:result.status},jobId:row.id});};
      }}},desktopBrief(JSON.parse(row.spec.task)),control.signal);
    const desktop={...result,jobId:row.id,childId:m.id};control.append(result.summary+'\n'+result.verification,'notice');
    return {state:result.status==='completed'?'completed':result.status==='unknown'?'unknown':result.status==='cancelled'?'cancelled':'failed',reason:result.summary,desktop,usage:{provider:model.provider,model:model.id,value:collectNativeUsage(manager)}};
  }
  private async delegateJob(parent:Meta,row:JobRecord,control:JobControl):Promise<JobOutcome>{
    control.signal.throwIfAborted();
    const m:Meta={id:'job-'+row.id,delegation:{parentId:parent.id,jobId:row.id,allowedTools:[...row.spec.allowedTools],resources:structuredClone(this.loaded.get(parent.id)!.resources)},reasoning:{...this.reasoningSettings(parent)},surface:parent.surface,cwd:parent.cwd,selection:{...parent.selection},title:'Delegated job '+row.id,saved:false,policy:parent.policy,updatedAt:Date.now(),requests:[],running:false};
    this.metadata.set(m.id,m);this.save(m);control.update({childId:m.id});
    let child:Loaded|undefined,unsubscribe:(()=>void)|undefined;
    const abort=()=>{if(child)void this.cancel(m.id,'parent-job-stop').catch(()=>{});};control.signal.addEventListener('abort',abort,{once:true});
    try{
      child=await this.load(m);control.signal.throwIfAborted();
      unsubscribe=boundChild(child.session,row,control);
      const requestId='job-input:'+row.id,input='Delegated task from the parent conversation. Preserve all supplied constraints. Report the result and any uncertainty.\n\n'+row.spec.task;
      this.queue(m).enqueue(requestId,input,true);this.submit(child,input,requestId);await child.task;
      const value=collectNativeUsage(child.manager);
      return {state:control.signal.aborted?'cancelled':child.failed||child.execution?.incomplete||this.queue(m).read(requestId).status!=='completed'||!child.initialDelivered?'failed':'completed',reason:control.signal.aborted?'Child stopped; its dispatched actions may have effects.':'Child turn settled. Verify the reported result and retained originals.',usage:{provider:m.selection.provider,model:m.selection.model,value}};
    }finally{
      control.signal.removeEventListener('abort',abort);unsubscribe?.();
      if(child){child.goals.disarm();child.observation?.record('job/child-close',{jobId:row.id,parentId:parent.id});child.observation?.dispose();child.reasoning?.dispose();child.steering?.dispose();child.execution?.dispose();child.memory.close();await child.memory.flush();await child.session.extensionRunner.emit({type:'session_shutdown',reason:'quit'});child.session.dispose();this.loaded.delete(m.id);}
      void this.flushJobReceipts(parent.id).catch(()=>{});this.wakeGoals();
    }
  }
  async cancel(id:unknown,source='user'){
    const target=this.getMeta(id);if(target.delegation&&source==='user')return this.jobs.cancel(target.delegation.parentId,target.delegation.jobId);
    const m=this.getMeta(id),queue=this.queue(m);queue.pause();const r=this.loaded.get(m.id);let aborting:Promise<void>|undefined;
    const reserved=queue.next;if(reserved?.goalSource)queue.remove(reserved.id);
    const cancellingCompaction=this.compactions.cancelSession(m.id),cancellingMcp=this.mcpManagement.cancelSession(m.id),jobsWereRunning=this.jobs.busyOwner(m.id);const cancellingJobs=this.jobs.cancelOwner(m.id);
    if(r){try{source==='user'?r.goals.stop():r.goals.disarm();}catch{r.goals.disarm();this.append(m,'runtime/warning',{message:'Goal state could not be paused. Continuation is disarmed; inspect the preserved native original.'});}}
    if(m.running&&r){if(r.preparingInput)r.interruptedInput=true;r.cancelled=true;r.execution?.cancel();for(const requestId of r.steering?.withdraw()??[])queue.withdrawSteer(requestId);r.session.abortCompaction();aborting=r.session.abort();}
    if(source==='user'||m.running)r?.observation?.record('control/stop',{wasRunning:m.running,source});this.desktopSpecialist.cancel('pi:'+m.id);this.interactions.cancel(m.id);
    if(r)await r.memory.activity('stop');if(m.surface!=='browser')await desktopControl('stop','pi:'+m.id).catch(()=>{});if(aborting)await aborting;await cancellingJobs;return {accepted:!!aborting||cancellingCompaction||cancellingMcp||jobsWereRunning,paused:true};
  }
  private async steer(m:Meta,id:string,expectedTurnId:unknown){
    const r=this.loaded.get(m.id),turnId=promptIdentity(expectedTurnId),queue=this.queue(m);
    if(!m.running||!r||r.cancelled||r.phase==='settling'||r.turnId!==turnId)throw Error('The observed steering turn is no longer active.');
    const prior=queue.read(id);if(prior.steerTurnId===turnId&&prior.status!=='waiting')return {accepted:true,duplicate:true,turnId};
    if(r.steering?.waiting)throw Error('A correction is already waiting for its safe boundary.');
    r.steering!.validate(prior.input!);
    const attachmentInput=await this.attachments.resolve(m.id,prior.input!,prior.attachments);
    if(!m.running||r.cancelled||this.loaded.get(m.id)?.phase==='settling'||r.turnId!==turnId)throw Error('The observed steering turn is no longer active.');
    if(!queue.promote(id,turnId))return {accepted:true,duplicate:true,turnId};
    r.execution!.steerRequested();this.interactions.cancel(m.id);
    const pending=r.steering!.enqueue(id,attachmentInput.text,result=>{
      if(result.action==='handled'){queue.handledSteer(id);r.execution!.steerHandled();this.append(m,'runtime/notice',{message:'The correction was handled by an input extension. No copy of that input was sent to the model.',submittedContent:submittedParts(prior.input??'',prior.attachments),source:{kind:'user',rpcId:id},incomplete:false});}
      r.observation?.record('execution/steer-input',{clientRequestId:id,action:result.action,handler:result.handler,skill:result.skill,template:result.template});
    },error=>{r.failed=true;r.execution!.steerFailed();this.append(m,'runtime/error',{message:'Correction input preparation failed: '+String(error)});},attachmentInput.images);
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
  workspaceSnapshot(){const data=this.workspaces.snapshot(),organization=this.organization.snapshot();return {revision:data.revision,items:data.items.map(row=>({...row,sessionIds:[...this.metadata.values()].filter(m=>resolve(m.cwd)===row.cwd).map(m=>m.id)})),organizationRevision:organization.revision,pinnedSessionIds:organization.pinnedSessionIds,archivedSessionIds:organization.archivedSessionIds};}
  private organizationTarget(p:Data){const m=this.getMeta(p.sessionId);if(m.delegation)throw Error('Delegated conversations are controlled by their parent job.');if(!['pin','unpin','archive','restore'].includes(p.action)||p.stop!==undefined&&typeof p.stop!=='boolean'||p.stop===true&&p.action!=='archive')throw Error('Choose a supported conversation organization action.');this.organization.check(p.expectedRevision);if(p.action==='archive'&&(this.jobs.problem||!this.mcpManagement.describe(m.id).available))throw Error('Work receipts are unavailable. Inspect them before archiving.');return m;}
  private archiveActivity(m:Meta){const activity:Data[]=[];if(this.compactions.busySession(m.id))activity.push({kind:'compaction',items:[{id:this.compactions.activeId(m.id)}]});if(m.running)activity.push({kind:'turn',items:[{id:m.id}]});const jobs=this.jobs.activeOwnerIds(m.id);if(jobs.length)activity.push({kind:'job',items:jobs.map(id=>({id}))});if(this.improvements.busySession(m.id))activity.push({kind:'prompt-improvement',items:[{id:m.id}]});if(this.mcpManagement.busySession(m.id))activity.push({kind:'mcp-management',items:[{id:m.id}]});return activity;}
  private organizeSession(p:Data){
    const m=this.organizationTarget(p);
    if(p.action==='archive'&&!this.organization.archived(m.id)){const activity=this.archiveActivity(m);if(activity.length)return {workspaces:this.workspaceSnapshot(),confirmation:{sessionId:m.id,displayTitle:m.title||'New conversation',activity}};}
    this.organization.mutate(p.action,m.id,p.expectedRevision);
    if(p.action==='archive'){this.queue(m).pause();this.loaded.get(m.id)?.goals.stop();}
    return {workspaces:this.workspaceSnapshot()};
  }
  private async stopAndArchive(p:Data){
    // Review on the admission chain; never hold it while existing producers settle.
    const review=this.serial.then(()=>{if(this.quiescing)throw Error('Runtime is closing for maintenance.');return this.organizationTarget(p);});this.serial=review.catch(()=>{});const m=await review;
    if(!this.organization.archived(m.id)){
      const improvement=this.improvements.cancelSession(m.id);await this.cancel(m.id);
      const pending=[improvement,this.loaded.get(m.id)?.task,this.mcpManagement.waitSession(m.id),this.compactions.waitSession(m.id)].filter(Boolean);let timer:ReturnType<typeof setTimeout>|undefined;
      try{await Promise.race([Promise.allSettled(pending),new Promise(resolve=>{timer=setTimeout(resolve,5000);})]);}finally{if(timer)clearTimeout(timer);}
    }
    const finish=this.serial.then(()=>{if(this.quiescing)throw Error('Runtime is closing for maintenance.');return this.organizeSession(p);});this.serial=finish.catch(()=>{});return finish;
  }
  private mcpInfo(m:Meta){if(m.surface==='browser')return {available:false,reason:'MCP is unavailable in browser-only conversations.'};return {...(this.loaded.get(m.id)?.mcp?.describe()??{available:false,reason:'MCP bindings are not loaded for this saved conversation.'}),management:this.mcpManagement.describe(m.id)};}
  submit(r:Loaded,input:string,id:string){r.mcp?.assertReady();const m=r.meta;if(this.organization.archived(m.id))throw Error('Restore the conversation before starting work.');if(m.running)throw new Error('This conversation is already working');
    if(this.mcpReloading)throw Error('Finish MCP session reload before sending a chat prompt.');
    if(m.surface!=='browser'&&this.mcpManagement.busy)throw Error('Finish or cancel MCP management before sending a Native chat prompt.');
    const reasoningPolicy=reasoningConfig(this.settings.reasoning),savedThinking=this.reasoningSettings(m);
    r.turnId=randomUUID();const queue=this.queue(m),goalSource=queue.read(id).goalSource;queue.dispatch(id,r.turnId);
    m.running=true;r.cancelled=false;r.failed=false;r.initialDelivered=false;r.preparingInput=false;r.interruptedInput=false;r.phase='preparing';r.activeRequestId=id;m.requests=[...m.requests.slice(-99),id];m.updatedAt=Date.now();this.save(m);this.append(m,'turn/start',{requestId:id});queue.accepted(id);
    r.observation?.beginTurn({clientRequestId:id});
    r.execution?.begin(r.manager);
    r.reasoning?.begin(reasoningPolicy,savedThinking,this.settings.revision);
    if(!m.title){m.title=(input||queue.read(id).attachments?.map(p=>p.attachment.name||'Attachment').join(', ')||'Attachment').replace(/\s+/g,' ').slice(0,80);r.session.setSessionName(m.title);this.append(m,'session/title',{title:m.title});this.save(m);}
    r.task=(async()=>{let failed=false,attempted=false,handled=false;try{
      await r.memory.activity('foreground');if(r.cancelled)return;
      const attachmentInput=await this.attachments.resolve(m.id,input,queue.read(id).attachments);if(r.cancelled)return;validateSteeringInput(r.session,input);r.phase='running';attempted=true;r.preparingInput=true;
      await r.session.prompt(attachmentInput.text,{images:attachmentInput.images,expandPromptTemplates:!goalSource,source:'rpc',preflightResult:disposition=>{
        r.preparingInput=false;
        if(r.cancelled)return;
        r.observation?.record('execution/input',{clientRequestId:id,disposition,expansion:'sdk-approved-skills-and-templates'});
        if(disposition==='handled'){
          handled=true;r.execution?.inputHandled();
          this.append(m,'runtime/notice',{message:'The input was handled by an input extension. No copy of that input was sent to the model.',disposition:'input-handled',submittedContent:submittedParts(input,queue.read(id).attachments),source:{kind:'user',sessionId:m.id,rpcId:id},incomplete:false});
        }
      }});
    }catch(error){failed=true;this.append(m,'runtime/error',{message:String(error)});}finally{
      r.phase='settling';
      try{r.goals.settle();}catch{r.goals.disarm();r.failed=true;this.append(m,'runtime/warning',{message:'Goal admission or pending pause could not be confirmed at settlement. Inspect its preserved original before resuming.'});}
      await r.memory.activity('stop');
      r.execution?.end(r.cancelled?'aborted':failed||r.failed||r.execution?.incomplete?'error':'completed');this.interactions.settleOwner(m.id);if(m.surface!=='browser'&&!this.jobs.busyKind('desktop',m.id))await desktopControl('stop','pi:'+m.id).catch(()=>{});const reason=r.cancelled?'aborted':failed||r.failed||r.execution?.incomplete?'error':'completed';
      // A terminal receipt is persisted before admitting another input. A crash
      // before this boundary produces an unknown receipt, never an automatic retry.
      const unknownInput=r.interruptedInput||attempted&&!r.initialDelivered&&!handled&&(r.cancelled||failed);r.preparingInput=false;
      queue.finish(id,unknownInput?'unconfirmed':reason==='aborted'?'cancelled':reason==='error'?'failed':'completed');if(reason!=='completed'||queue.uncertain)queue.pause();
      if(unknownInput)this.append(m,'runtime/notice',{message:'Input preparation stopped before model delivery. Its extension effects may be unknown; this prompt will not be replayed.',incomplete:true});
      if(r.goals.armed&&(reason!=='completed'||goalSource&&handled)){try{r.goals.fail(handled?'goal-input-handled':reason==='aborted'?'turn-interrupted':'turn-failed',handled?'A goal input was handled without model admission. Explicit human review is required.':'Work stopped or failed. Inspect its outcome before explicitly resuming the goal.');}catch{r.goals.disarm();}}
      m.running=false;m.updatedAt=Date.now();this.save(m);this.append(m,'turn/end',{reason:{kind:reason},requestId:id});r.observation?.record('turn/end',{reason,execution:r.execution?.describe()});r.turnId=undefined;r.activeRequestId=undefined;r.phase=undefined;
      void this.flushJobReceipts(m.id).catch(()=>{});if(!m.delegation&&!queue.paused)this.pump(m);
    }})();return {accepted:true,turnId:r.turnId};
  }
  private wakeGoals(){for(const r of this.loaded.values())if(r.goals.armed&&!r.meta.running)void this.pump(r.meta);}
  private pump(m:Meta){
    if(this.pumping.has(m.id))return this.pumping.get(m.id)!;
    const run=this.serial.then(async()=>{
      const queue=this.queue(m);
      if(this.organization.archived(m.id)||this.quiescing||this.mcpReloading||this.improvements.busy||m.surface!=='browser'&&this.mcpManagement.busy||m.running||this.compactions.blocked(m.id)||queue.paused||queue.uncertain)return;
      let item=queue.next;
      if(!item){if(this.jobs.busyOwner(m.id))return;const owner=this.loaded.get(m.id);if(!owner?.goals.armed)return;try{const source=owner.goals.reserve();if(!source)return;const requestId='goal:'+randomUUID();queue.enqueue(requestId,owner.goals.prompt(source),true,source);item=queue.next;}catch{try{owner.goals.fail('goal-queue-failed','Goal input could not be queued. Inspect the queue before explicitly resuming.');}catch{owner.goals.disarm();}return;}}
      if(!item)return;
      let r:Loaded;
      try{r=await this.load(m);}catch(error){queue.notSent(item.id);this.append(m,'runtime/error',{message:'Queued prompt was not sent: '+String(error)});return;}
      if(this.organization.archived(m.id)||this.quiescing||this.mcpReloading||this.improvements.busy||m.surface!=='browser'&&this.mcpManagement.busy||m.running||this.compactions.blocked(m.id)||queue.paused||queue.uncertain||queue.next?.id!==item.id)return;
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
    if(method==='session.organize'&&p.action==='archive'&&p.stop===true)return this.stopAndArchive(p);
    if(method==='session.cancelJob')return this.jobs.cancel(this.getMeta(p.sessionId).id,identifier(p.jobId));
    if(method==='session.waitJob')return this.jobs.wait(this.getMeta(p.sessionId).id,identifier(p.jobId),p.timeoutMs);
    if(method==='prompt.cancelImprovement')return this.improvements.cancel(p.requestId,p.scopeId);
    if(method==='prompt.improvementStatus')return this.improvements.status(p.requestId);
    if(method==='interaction.respond')return this.interactions.answer(identifier(p.rpcId),p.value,identifier(p.sessionId));
    if(method==='interaction.wait')return this.interactions.wait(identifier(p.rpcId),identifier(p.sessionId),identifier(p.clientId),p.action);
    // Serialize state-changing preparations so two clients cannot create/replace an execution owner.
    const run=this.serial.then(()=>{if(this.quiescing&&method!=='host.describe')throw new Error('Runtime is closing for maintenance. No action was submitted.');return this.handle(method,p,id);});this.serial=run.catch(()=>{});
    const result=await run;return result instanceof SteeringReply?result.settled.finally(()=>this.wakeGoals()):result;
  }
  async handle(method:string,p:Data,id:string):Promise<any>{
    if(p.sessionId&&this.organization.archived(p.sessionId)&&['session.prompt','session.continueQueue','session.startJob','session.updateGoal','session.compact','prompt.improve'].includes(method))throw Error('Restore the conversation before starting work.');
    if(this.mcpReloading&&(['prompt.improve','setup.save','models.configure','models.reload','session.create','session.branch','session.updateGoal','session.trimTools','session.compact','session.selectModel','session.selectReasoning','reasoning.configure','session.prompt','session.continueQueue'].includes(method)||method==='session.updateQueue'&&p.action?.kind==='steer'))throw Error('Finish MCP session reload before changing or starting a conversation.');
    if(method.startsWith('session.')&&p.sessionId&&this.metadata.get(p.sessionId)?.delegation&&!['session.history','session.nativeHistory','session.nativeRead','session.originalSearch','session.originalRead','session.plan','session.goal','session.queue','session.compaction','session.cancel'].includes(method))throw Error('Delegated conversations are controlled by their parent job.');
    if(this.jobs.busy&&['models.configure','models.reload','setup.save','reasoning.configure','session.mcpConfigure','session.mcpAction'].includes(method))throw Error('Stop and settle background jobs before changing their shared configuration.');
    if(this.compactions.busy&&['setup.save','models.configure','models.reload','reasoning.configure','session.mcpConfigure','session.mcpAction','prompt.improve'].includes(method))throw Error('Finish or cancel Pi compaction before changing shared configuration.');
    if(p.sessionId&&this.compactions.blocked(p.sessionId)&&['session.create','session.branch','session.trimTools','session.selectModel','session.selectReasoning','session.prompt','session.continueQueue','session.updateGoal','session.startJob'].includes(method))throw Error('Finish compaction or inspect and acknowledge its unknown outcome before changing this conversation.');
    switch(method){
    case 'session.compaction':{const m=this.getMeta(p.sessionId);return this.compactions.describe(m.id);}
    case 'session.acknowledgeCompaction':{const m=this.getMeta(p.sessionId);if(p.acknowledgeUnknownOutcome!==true)throw Error('Explicitly acknowledge that the compaction outcome remains unknown.');return this.compactions.acknowledge(m.id,identifier(p.requestId));}
    case 'session.compact':{
      const m=this.getMeta(p.sessionId),request={sessionId:m.id,requestId:identifier(p.requestId),provider:text(p.provider,256),model:text(p.model,512)};
      if(p.instructions!==undefined)throw Error('Manual Compact currently uses Pi’s default summary instructions.');
      const duplicate=this.compactions.duplicate(request);if(duplicate)return duplicate;
      if(m.running||this.jobs.busyOwner(m.id)||this.improvements.busy||this.mcpManagement.busy||this.loaded.get(m.id)?.goals.armed)throw Error('Stop active work and pause goal continuation before compacting this conversation.');
      if(m.selection.provider!==request.provider||m.selection.model!==request.model)throw Error('The selected model changed. Reopen Compact; nothing was sent.');
      // Lease/receipt precede async owner loading. Stop can cancel preparation;
      // the queue remains paused after settlement and is never auto-resumed.
      const accepted=this.compactions.begin(request,async(signal,checkpoint)=>{
        const r=await this.load(m);if(signal.aborted)return {state:'cancelled',sdkOutcome:'not-called'};
        if(r.session.isStreaming||r.session.isCompacting||r.session.model?.provider!==request.provider||r.session.model?.id!==request.model)return {state:'failed',sdkOutcome:'not-called'};
        const before=new Set(r.manager.getEntries().map(entry=>entry.id));
        checkpoint(r.manager.getLeafId(),()=>r.session.abortCompaction());
        // compact() awaits abort() before creating its AbortController. The
        // public start event closes that early cancellation race.
        let sdkAborted=false;
        const off=r.session.subscribe(event=>{if(event.type==='compaction_start'&&event.reason==='manual'&&signal.aborted)r.session.abortCompaction();if(event.type==='compaction_end'&&event.reason==='manual')sdkAborted=event.aborted;});
        let result:Awaited<ReturnType<AgentSession['compact']>>|undefined,rejected=false;
        try{if(!signal.aborted)result=await r.session.compact();}catch{rejected=true;}finally{off();}
        const added=r.manager.getEntries().filter(entry=>!before.has(entry.id)&&entry.type==='compaction');
        const entry=added.length===1&&r.manager.getBranch().some(candidate=>candidate.id===added[0].id)?added[0]:undefined;
        if(entry&&entry.type==='compaction')return {state:'completed',sdkOutcome:rejected?'rejected':'returned',entryId:entry.id,tokensBefore:entry.tokensBefore,...(result?.estimatedTokensAfter!==undefined?{estimatedTokensAfter:result.estimatedTokensAfter}:{})};
        if(added.length||result)return {state:'unknown',sdkOutcome:rejected?'rejected':'returned'};
        return {state:signal.aborted||sdkAborted?'cancelled':'failed',sdkOutcome:rejected?'rejected':'not-called'};
      });
      this.queue(m).pause();return accepted;
    }
    case 'session.jobs':{const m=this.getMeta(p.sessionId);return {available:!this.jobs.problem,reason:this.jobs.problem,items:this.jobs.list(m.id),scope:'exact-parent-conversation; reported producer outcomes; reads do not add usage'};}
    case 'session.job':{const m=this.getMeta(p.sessionId),job=this.jobs.lookup(m.id,identifier(p.jobId));return {job,output:this.jobs.output(m.id,job.id,p.from)};}
    case 'session.jobHistory':{const m=this.getMeta(p.sessionId),job=this.jobs.lookup(m.id,identifier(p.jobId));if(!job.childId)return {available:false,reason:'This job has no delegated conversation.'};return {available:true,childId:job.childId,...this.history(this.getMeta(job.childId)).page(p.maxMessages,p.beforeSeq)};}
    case 'session.jobNativeHistory':case 'session.jobNativeRead':case 'session.jobObservations':case 'session.jobPayload':{
      const parent=this.getMeta(p.sessionId),job=this.jobs.lookup(parent.id,identifier(p.jobId));if(!job.childId)return {available:false,reason:'This job has no child native history.'};
      const childMethod=({ 'session.jobNativeHistory':'session.nativeHistory','session.jobNativeRead':'session.nativeRead','session.jobObservations':'observation.list','session.jobPayload':'observation.payload'} as Record<string,string>)[method]!;
      return this.handle(childMethod,{...p,sessionId:job.childId},id);
    }
    case 'session.startJob':{const m=this.getMeta(p.sessionId);await this.load(m);return this.startJob(m,p.spec);}
    case 'session.removeJob':{const m=this.getMeta(p.sessionId);return this.jobs.remove(m.id,identifier(p.jobId));}
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
    case 'host.describe':return {protocol:PROTOCOL,pid:process.pid,activeUploads:this.uploads,activeCompactions:this.compactions.busy?1:0,activeTurns:[...this.metadata.values()].filter(m=>m.running).length,version:RELEASE.version,piVersion:'1.1.0',workspace:process.env.AUGMENTOR_PI_WORKSPACE||process.cwd(),attachmentLimits:{...IMAGE_LIMITS,maxFileBytes:FILE_LIMIT},capabilities:{manualCompaction:'public-sdk; native-boundary-receipts; cancel-and-no-replay',attachments:true,jobs:'durable-exact-owner; bounded-sdk-children-and-shell; no-replay; one-time-attribution',goals:'persistent-branch-state; explicit-human-arming; same-owner-continuation',plans:true,queue:true,steering:true,reasoning:true,promptImprovement:true,inspection:true,indexedDisplayHistory:true,indexedNativeHistory:true,managedMcp:'native-managed-profile; browser-unavailable; explicit-sdk-management',mcpManagement:true,mcpConfiguration:true,toolOriginals:'native-current-branch; MCP-and-nested; before-result-hooks; 63-MiB-JSON-limit',originalHistorySearch:'Pi selected ancestry/all saved entries and raw display originals',linuxTools:process.env.AUGMENTOR_PI_LINUX_TOOLS!=='0',desktopInput:desktopCapabilities().available,osCustomisation:false,localRouteEnforcement:false},promptInput:{source:'rpc',expandPromptTemplates:true,skills:'approved-session-resources',extensionCommands:'rejected-in-durable-queue',disposition:'PromptOptions.preflightResult',stopDuringInput:'provider-blocked; await-handler-settlement; uncertain-receipt'},steering:{input:'sdk-public-input-and-approved-resources',sdkInputTransforms:true,inFlightTools:'settle',continuation:'same-AgentSession',identity:'owned-message-reference'},execution:{...EXECUTION_POLICY,providerRetries:0,sessionRetries:false,actionGuard:'automatic-recovery-and-steered-continuation',completion:'response-or-tool-handoff; task success requires verification'},toolBudget:{...TOOL_BUDGET,units:'unicode-code-points',originals:'native-current-branch',idleRepair:true},desktopSpecialist:{version:'augmentor-computer-use/1',available:desktopCapabilities().available,selectedModelOnly:true,requiresImageModel:true,maxConcurrent:1,evidence:'local-files',coreIntegration:false},desktopControl:desktopCapabilities(),configDir:this.dirs.config,stateDir:this.dirs.state};
    case 'host.prepareShutdown':
      if(this.compactions.busy)throw Error('Stop and settle Pi compaction before shutting down the runtime.');
      if(this.uploads)throw Error('Finish file uploads before shutting down the runtime.');
      if(this.jobs.busy)throw Error('Stop and settle background jobs before shutting down the runtime');
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
    case 'workspace.list':return this.workspaceSnapshot();
    case 'session.organize':return this.organizeSession(p);
    case 'workspace.adopt':await this.workspaces.adopt(p.path,p.expectedRevision);return {...this.workspaceSnapshot(),adoptedWorkspaceId:workspacePath(p.path)};
    case 'workspace.rename':this.workspaces.rename(p.workspaceId,p.title,p.expectedRevision);return this.workspaceSnapshot();
    case 'workspace.remove':this.workspaces.remove(p.workspaceId,p.expectedRevision);return this.workspaceSnapshot();
    case 'workspace.move':this.workspaces.move(p.workspaceId,p.beforeWorkspaceId,p.expectedRevision);return this.workspaceSnapshot();
    case 'workspace.listDirectory':return listWorkspaceDirectory(p.path);
    case 'workspace.createDirectory':return createWorkspaceDirectory(p.path,p.name);
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
    case 'session.list':return {items:[...this.metadata.values()].filter(m=>!m.delegation).sort((a,b)=>b.updatedAt-a.updatedAt).map(m=>({sessionId:m.id,cwd:m.cwd,agentPreset:m.surface==='browser'?'augmentor-browser-pi':'augmentor-linux-pi',title:m.title,updatedAt:m.updatedAt,saved:m.saved,running:m.running||this.compactions.busySession(m.id),compacting:this.compactions.busySession(m.id),blank:!m.title,jobsRunning:this.jobs.busyOwner(m.id),...(m.fork?{fork:m.fork}:{})}))};
    case 'session.history':{const m=this.getMeta(p.sessionId);return this.history(m).page(p.maxMessages,p.beforeSeq);}
    case 'session.mcpInfo':return this.mcpInfo(this.getMeta(p.sessionId));
    case 'session.mcpActionStatus':{const m=this.getMeta(p.sessionId),receipt=this.mcpManagement.lookup(m.id,identifier(p.requestId));return p.includeCatalog===true?{...receipt,catalog:this.mcpInfo(m)}:receipt;}
    case 'session.mcpCancelAction':{const m=this.getMeta(p.sessionId);return this.mcpManagement.cancel(m.id,identifier(p.requestId));}
    case 'session.mcpSubmitRedirect':{const m=this.getMeta(p.sessionId);return this.mcpManagement.submitRedirect(m.id,identifier(p.requestId),p.url);}
    case 'session.mcpProfile':{
      const m=this.getMeta(p.sessionId);if(m.surface==='browser')throw Error('MCP configuration is unavailable in browser-only conversations.');
      const profile=readMcpProfile(join(this.dirs.agent,'mcp.json'));return {...(p.metadataOnly===true?{revision:profile.revision}:profile),scope:'private operator profile; may contain credentials; never retain in diagnostics or send to the model'};
    }
    case 'session.mcpConfigure':{
      const m=this.getMeta(p.sessionId),requestId=identifier(p.requestId),operation=p.operation;
      if(m.surface==='browser')throw Error('MCP configuration is unavailable in browser-only conversations.');
      if(!['save-profile','set-enabled','set-exposure'].includes(operation))throw Error('Choose a supported MCP configuration operation.');
      const server=operation==='save-profile'?'profile':identifier(p.server);
      if(typeof p.expectedRevision!=='string'||!(p.expectedRevision==='missing'||/^[a-f0-9]{64}$/.test(p.expectedRevision)))throw Error('Read the MCP profile revision before changing it.');
      if(operation==='save-profile'&&(typeof p.text!=='string'||Buffer.byteLength(p.text)>1024*1024))throw Error('The MCP JSON profile exceeds its limits.');
      if(operation==='set-enabled'&&typeof p.enabled!=='boolean')throw Error('Choose whether the MCP server is enabled.');
      if(operation==='set-exposure'&&!['codemode','deferred','direct','hidden'].includes(p.exposure))throw Error('Choose codemode, deferred, direct or hidden tool exposure.');
      const parametersSha256=mcpDigest(JSON.stringify([operation,p.expectedRevision,server,operation==='save-profile'?p.text:operation==='set-enabled'?p.enabled:p.exposure]));
      const input={sessionId:m.id,requestId,server,action:'configure' as const,parametersSha256},duplicate=this.mcpManagement.duplicate(input);if(duplicate)return duplicate;
      if(!this.connected(m.id))throw Error('Connect an operator surface before changing MCP configuration.');
      if(this.improvements.busy||[...this.metadata.values()].some(row=>row.surface!=='browser'&&(row.running||!this.queue(row).paused&&!!this.queue(row).next)))throw Error('Finish active Native turns and pause their waiting prompts before configuring MCP.');
      if(!this.loaded.get(m.id)?.mcp)throw Error('Load this Native conversation before changing MCP configuration.');
      const file=join(this.dirs.agent,'mcp.json'),before=readMcpProfile(file);
      if(before.revision!==p.expectedRevision)throw Error('The MCP profile changed since it was read. Reload it before saving.');
      let proposed=p.text;
      if(operation!=='save-profile'){
        let config;try{config=JSON.parse(before.text);}catch{throw Error('Repair the MCP JSON profile before changing a server.');}
        if(!config?.mcpServers||typeof config.mcpServers!=='object'||!Object.hasOwn(config.mcpServers,server))throw Error('Choose a server in the managed MCP profile.');
        const entry=config.mcpServers[server];if(!entry||typeof entry!=='object'||Array.isArray(entry))throw Error('Choose a server in the managed MCP profile.');
        if(operation==='set-enabled')entry.enabled=p.enabled;else entry.exposure=p.exposure;
        proposed=JSON.stringify(config,null,2)+'\n';
      }
      const targets=[...this.loaded.values()].filter(row=>row.mcp);
      return this.mcpManagement.configure(input,async(signal,checkpoint)=>{
       try{
        const profile=await prepareMcpProfile(proposed,m.cwd,this.dirs.agent);
        for(const row of targets)row.mcp!.preflight(profile);
        if(targets.some(row=>row.mcp!.needsSessionReload(profile))){
          // Public reload resets shared provider registrations. Exclude work
          // in every surface before save, and admit none until it settles.
          this.mcpReloading=true;
          if(this.improvements.busy||[...this.metadata.values()].some(row=>row.running||!this.queue(row).paused&&!!this.queue(row).next))throw Error('Finish all turns and pause waiting prompts before changing MCP session options.');
        }
        if(signal.aborted)throw Error('Cancelled before profile save.');
        const revision=saveMcpProfile(file,p.expectedRevision,profile,()=>{checkpoint({saveAttempted:true});for(const row of targets)row.mcp!.markPending();});
        checkpoint({savedRevision:revision,expectedSessions:targets.length,appliedSessions:0});
        let applied=0,reloaded=0,pendingOptions=false;
        // Once saved, finish applying instead of letting Cancel leave avoidable
        // stale owners. A crash/SDK rejection remains partial/unknown, no replay.
        for(const row of targets){
          if(row.mcp!.needsSessionReload(profile)){const options=row.mcp!.prepareSessionReload(profile);await row.reload!(options);row.mcp!.finishSessionReload(revision);reloaded++;}
          else await row.mcp!.apply(profile,revision);
          applied++;pendingOptions ||= row.mcp!.describe().configuration.pendingSessionOptions;checkpoint({appliedSessions:applied,reloadedSessions:reloaded,pendingSessionOptions:pendingOptions});
        }
       }finally{this.mcpReloading=false;this.wakeGoals();}
      });
    }
    case 'session.mcpAction':{
      const m=this.getMeta(p.sessionId),requestId=identifier(p.requestId),server=identifier(p.server);
      if(m.surface==='browser')throw Error('MCP management is unavailable in browser-only conversations.');
      if(!['login','logout','reconnect'].includes(p.action))throw Error('Choose sign in, sign out or reconnect.');
      const input={sessionId:m.id,requestId,server,action:p.action as McpManagementAction},duplicate=this.mcpManagement.duplicate(input);if(duplicate)return duplicate;
      if(!this.connected(m.id))throw Error('Connect an operator surface before starting MCP management.');
      if(this.improvements.busy||[...this.metadata.values()].some(row=>row.surface!=='browser'&&(row.running||!this.queue(row).paused&&!!this.queue(row).next)))throw Error('Finish active Native turns and pause their waiting prompts before managing MCP.');
      const r=this.loaded.get(m.id);if(!r?.mcp)throw Error('Load this Native conversation before managing MCP.');
      return this.mcpManagement.begin(input,r.mcp.managementCommand(input.action,server),r.session.extensionRunner.createCommandContext());
    }
    case 'session.originalSearch':case 'session.originalRead':{
      const m=this.getMeta(p.sessionId),source=p.source??'pi';if(!['pi','display'].includes(source))throw Error('Choose Pi entries or display originals.');
      const file=source==='pi'?m.file:join(this.dirs.sessions,m.id+'.events.jsonl');if(!file)return {available:false,reason:'This conversation has no saved native session.'};
      const cache=source==='pi'?this.nativeHistories:this.displayOriginals;let original=cache.get(m.id);if(!original||original.source!==file){original=new NativeHistory(file,join(this.dirs.state,source==='pi'?'native-index':'display-original-index',m.id),source==='display'?m.id:undefined);if(cache.size>=32)cache.delete(cache.keys().next().value!);cache.set(m.id,original);}
      if(method==='session.originalSearch')return original.search({query:p.query,scope:p.scope??(source==='display'?'all-entries':'selected-ancestry'),limit:p.limit,cursor:p.cursor,leafId:p.leafId===undefined?this.loaded.get(m.id)?.manager.getLeafId():p.leafId,nativeSessionId:p.sessionIdentity??(source==='pi'?p.nativeSessionId:undefined)});
      const result=original.read(identifier(p.entryId),{offset:p.offset,limit:p.limit,pathHash:p.pathHash,entryHash:p.entryHash,nativeSessionId:p.sessionIdentity??(source==='pi'?p.nativeSessionId:undefined)});if(!result.available)return result;const {nativeSessionId,...body}=result;return {...body,source,sessionIdentity:nativeSessionId,boundary:source==='pi'?result.boundary:'verified original display event; raw streamed fragments can be compacted in Chat; not Pi model context'};
    }
    case 'session.goal':{
      const m=this.getMeta(p.sessionId),loaded=this.loaded.get(m.id);
      if(loaded){try{return loaded.goals.view();}catch{return {available:false,activation:'disarmed',reason:'Goal replay is invalid, incomplete or exceeds its ancestry/byte limits; inspect preserved native originals.'};}}
      if(!m.file||!existsSync(m.file))return {...goalProjection(),activation:'disarmed',persistence:'no-saved-native-goal'};
      let native=this.nativeHistories.get(m.id);if(!native||native.source!==m.file){native=new NativeHistory(m.file,join(this.dirs.state,'native-index',m.id));if(this.nativeHistories.size>=32)this.nativeHistories.delete(this.nativeHistories.keys().next().value!);this.nativeHistories.set(m.id,native);}
      try{const saved=native.replayCustom(undefined,GOAL_ROUND_TYPE);if(!saved.available)return {...saved,activation:'disarmed'};return {...goalProjection(saved.entries),activation:'disarmed',nativeSessionId:saved.nativeSessionId,persistence:'saved-native-replay',coverage:saved.coverage};}catch{return {available:false,activation:'disarmed',reason:'Saved goal replay is invalid or incomplete; inspect preserved native originals.'};}
    }
    case 'session.updateGoal':{
      const m=this.getMeta(p.sessionId);if(m.surface!=='browser'&&this.mcpManagement.busy)throw Error('Finish or cancel MCP management before changing a goal.');
      if(!p.change||typeof p.change!=='object'||Array.isArray(p.change))throw Error('Supply a goal operation and exact reference.');
      if(m.running&&['create','resume'].includes(p.change.operation))throw Error('Wait for the current turn before arming goal continuation.');
      if(p.change.continueAutomatically===true&&this.queue(m).uncertain)throw Error('Inspect and acknowledge the interrupted prompt outcome before arming the goal.');
      const r=await this.load(m),result=r.goals.change(p.change,true);
      if(p.change.operation==='pause'&&m.running)await this.cancel(m.id);
      if(r.goals.armed){try{this.queue(m).resume();void this.pump(m);}catch(error){r.goals.disarm();throw error;}}
      return p.change.operation==='pause'?r.goals.view():result;
    }
    case 'session.plan':{
      const m=this.getMeta(p.sessionId),loaded=this.loaded.get(m.id);
      if(loaded){try{return {...currentPlan(loaded.manager),nativeSessionId:loaded.manager.getSessionId(),persistence:'native-session-memory; saved record confirmation is separate'};}catch{return {available:false,reason:'The latest plan record is invalid; inspect its preserved native original.'};}}
      if(!m.file||!existsSync(m.file))return {...planProjection(),persistence:'no-saved-native-plan'};
      let native=this.nativeHistories.get(m.id);if(!native||native.source!==m.file){native=new NativeHistory(m.file,join(this.dirs.state,'native-index',m.id));if(this.nativeHistories.size>=32)this.nativeHistories.delete(this.nativeHistories.keys().next().value!);this.nativeHistories.set(m.id,native);}
      const saved=native.latestCustom(PLAN_TYPE);if(!saved.available)return saved;
      try{return {...planProjection(saved.entry??undefined),nativeSessionId:saved.nativeSessionId,persistence:'saved-native-entry',coverage:saved.coverage};}catch{return {available:false,reason:'The latest saved plan record is invalid; inspect its preserved native original.',coverage:saved.coverage};}
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
      const hasImages=Array.isArray(p.content)&&p.content.some((part:Data)=>part.type==='image');if(hasImages&&!(await this.selected(m.selection)).input.includes('image'))throw Error('The selected model does not support image input.');
      const {input,attachments}=await this.attachments.admit(m.id,p.content),queue=this.queue(m);
      const existing=queue.lookup(requestId,input,attachments);if(existing||m.requests.includes(requestId))return {accepted:true,duplicate:true,requestId};
      if(m.surface!=='browser'&&this.mcpManagement.busy)throw Error('Finish or cancel MCP management before sending a Native chat prompt.');
      this.loaded.get(m.id)?.mcp?.assertReady();
      if(p.mode==='steer'){
        const r=this.loaded.get(m.id);if(!m.running||!r||r.cancelled||r.phase==='settling'||r.turnId!==p.expectedTurnId||queue.paused||queue.uncertain||r.steering?.waiting)throw Error('The observed steering turn is no longer available.');
        r.steering!.validate(input);queue.enqueue(requestId,input,true,undefined,attachments);return new SteeringReply(this.steer(m,requestId,p.expectedTurnId).then(result=>({...result,requestId})));
      }
      if(p.mode===undefined&&m.running)throw Error('This conversation is already working; use queue mode to add a waiting prompt.');
      if(p.resumeQueue!==undefined&&typeof p.resumeQueue!=='boolean')throw Error('Choose whether to resume the queue.');
      if(queue.uncertain)throw Error('A previous prompt has an unknown outcome. Inspect its history and explicitly acknowledge the interrupted receipt before sending more.');
      // Templates/skills use Session.prompt's SDK expansion, while registered
      // commands cannot bypass the persistent queue's admission/receipt rules.
      if(input.startsWith('/'))validateSteeringInput((await this.load(m)).session,input);
      if(this.mcpReloading||m.surface!=='browser'&&this.mcpManagement.busy)throw Error('Finish MCP management or session reload before admitting another prompt.');
      queue.enqueue(requestId,input,m.running||queue.paused||!!queue.next,undefined,attachments);
      if(p.resumeQueue===true||(p.mode===undefined&&!m.running&&p.resumeQueue!==false))queue.resume();
      if(!m.running&&!queue.paused){
        let r:Loaded;try{r=await this.load(m);}catch(error){queue.notSent(requestId);throw error;}
        if(this.mcpReloading||m.surface!=='browser'&&this.mcpManagement.busy){queue.notSent(requestId);throw Error('Finish MCP management or session reload before dispatching another prompt.');}
        if(!queue.paused&&queue.next?.id===requestId)return {...this.submit(r,input,requestId),requestId};
        void this.flushJobReceipts(m.id).catch(()=>{});if(!m.delegation&&!queue.paused)this.pump(m);
      }
      return {accepted:true,queued:true,requestId};
    }
    case 'session.queue':return this.queueSnapshot(p.sessionId);
    case 'session.updateQueue':{const m=this.getMeta(p.sessionId),itemId=promptIdentity(p.itemId);if(p.action?.kind==='steer')return new SteeringReply(this.steer(m,itemId,p.expectedTurnId));if(p.action?.kind==='edit'){if(!Array.isArray(p.action.content)||!p.action.content.every((part:Data)=>part.type==='text'&&typeof part.text==='string'))throw Error('Queued edits support text only.');this.queue(m).replaceWaiting(itemId,promptIdentity(p.newItemId),text(p.action.content.map((part:Data)=>part.text).join('\n')),p.expectedRevision);return {accepted:true,...this.queueSnapshot(m.id)};}if(p.action?.kind!=='remove')throw Error('Choose edit, steer or remove.');this.queue(m).remove(itemId);return {accepted:true,...this.queueSnapshot(m.id)};}
    case 'session.continueQueue':{const m=this.getMeta(p.sessionId);if(m.surface!=='browser'&&this.mcpManagement.busy)throw Error('Finish or cancel MCP management before continuing Native prompts.');this.loaded.get(m.id)?.mcp?.assertReady();this.queue(m).resume();this.pump(m);return {accepted:true};}
    case 'session.resolveQueue':{const m=this.getMeta(p.sessionId);if(m.running||p.acknowledgeUnknownOutcome!==true)throw Error('Inspect the saved history and explicitly acknowledge that the interrupted action outcome remains unknown.');this.queue(m).resolve(promptIdentity(p.itemId));this.append(m,'runtime/notice',{message:'The interrupted prompt receipt was acknowledged. Its action outcome may still be unknown. That prompt was not retried; waiting prompts remain paused.',incomplete:true});return {accepted:true};}
    case 'session.rename':{const m=this.getMeta(p.sessionId);m.title=text(p.title,200);this.loaded.get(m.id)?.session.setSessionName(m.title);this.save(m);this.append(m,'session/title',{title:m.title});return {title:m.title};}
    case 'chats.saved':{if(p.action&&p.action!=='state'){if(!['save','unsave'].includes(p.action))throw new Error('Invalid saved-chat action');const m=this.getMeta(p.sessionId);m.saved=p.action==='save';this.save(m);}return {saved:[...this.metadata.values()].filter(m=>m.saved).map(m=>m.id)};}
    case 'settings.describe':if(p.ns==='dsh-context')return {namespaces:[this.contextPreferenceSnapshot()]};return {namespaces:[{ns:'permission',revision:this.settings.revision,value:{defaultPreset:this.settings.defaultPreset}},{ns:'prompt-library',revision:this.settings.revision,value:await promptCall('prompts.list')},this.contextPreferenceSnapshot()]};
    case 'settings.mutate':{
      if(p.expectedRevision!==this.settings.revision)throw new Error('Settings changed. Reopen the dialog.');
      if(p.ns==='dsh-context'){const change=contextPreferenceChange(p.ops);const next={...this.settings,revision:this.settings.revision+1,contextPreferences:{...contextPreferences(this.settings.contextPreferences),[change.field]:change.value}};atomicJson(join(this.dirs.config,'settings.json'),next);this.settings=next;return this.contextPreferenceSnapshot();}
      if(p.ns!=='permission')throw Error('Unsupported settings namespace.');const op=p.ops?.[0];if(!Array.isArray(p.ops)||p.ops.length!==1||op.op!=='set'||op.path?.join('.')!=='defaultPreset'||!['read-only','workspace-write','danger-full-access'].includes(op.value))throw new Error('Unsupported settings change');this.settings.defaultPreset=op.value;this.persistSettings();return {ok:true};}
    case 'prompts.list':case 'prompts.save':case 'prompts.delete':return promptCall(method,p,id);
    case 'prompts.improvementSave':return promptCall('prompts.improvement.save',p,id);
    default:throw new Error('Unsupported method: '+method);
  }}
  async close(){this.quiescing=true;this.setup.cancel();await this.jobs.close();await this.improvements.close();for(const m of this.metadata.values())if(this.compactions.busySession(m.id)){this.compactions.cancelSession(m.id);await this.compactions.waitSession(m.id);}for(const r of this.loaded.values()){await this.cancel(r.meta.id,'runtime-shutdown');await r.task;await r.session.extensionRunner.emit({type:'session_shutdown',reason:'quit'});r.memory.close();await r.memory.flush();r.observation?.record('session/close',{source:'runtime-shutdown'});r.observation?.dispose();r.reasoning?.dispose();r.steering?.dispose();r.execution?.dispose();r.session.dispose();}await this.mcpManagement.settled();}
}

/** Normalized public native usage, including nested tools, with one owner. */
function collectNativeUsage(manager:SessionManager):Usage{
 const value:Usage={input:0,output:0,cacheRead:0,cacheWrite:0,totalTokens:0,cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}};
 for(const entry of manager.getEntries()){
  const usage=entry.type==='usage'?entry.usage:entry.type==='compaction'||entry.type==='branch_summary'?entry.usage:entry.type==='message'&&(entry.message.role==='assistant'||entry.message.role==='toolResult')?entry.message.usage:undefined;
  if(usage){for(const key of ['input','output','cacheRead','cacheWrite','totalTokens'] as const)value[key]+=usage[key]??0;for(const key of ['input','output','cacheRead','cacheWrite','total'] as const)value.cost[key]+=usage.cost?.[key]??0;}
 }
 return value;
}
