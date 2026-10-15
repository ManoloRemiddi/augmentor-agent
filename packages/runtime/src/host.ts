// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {PiVoice} from './voice.js';
import {piInputMode,promptInputMode,spokenRequestId,type InputMode} from './input-mode.js';
import {WikiBinding} from './wiki.js';
import {skillCatalog,prepareApprovedSkill,deliveredSkill,type PreparedSkill} from './session-skills.js';
import {permissionSelection,permissionHistory,permissionChange,permissionAtBoundary,permissionCommand,permissionOptions,type PermissionRecord} from './session-permission-contracts.js';
import {WikiPreferences} from './wiki-preferences.js';
import {SearchPreferences} from './search-preferences.js';
import {freeSearchExtension} from './free-search.js';
import {keylessSearchExtension} from './keyless-search.js';
import {WikiReceipts,wikiActionKey} from './wiki-receipts.js';
import {PiFilePreview,PreviewReadError} from './file-preview.js';
import {PiOfficePreview} from './office-preview.js';
import {createLinuxNativeOfficeConverter} from './office-native-linux.js';
import {PiFileReferences} from './file-references.js';
import {FILE_REFERENCE_PROMPT} from '../vendor/dsh-file-reference/guidance.js';
import {desktopCapabilities} from '../../desktop/src/capabilities.js';
import {desktopPackage,control as desktopControl} from '../../desktop/src/index.js';
import {DualMemoryClient} from '../../memory/src/dual.js';
import {managedPiMemory,piTranscriptEvent} from '../../memory/src/pi.js';
import {memoryPackage} from '../../memory/src/index.js';
import {promptCall} from '../../prompt-library/src/client.js';
import {listWorkspaceDirectory,createWorkspaceDirectory} from './workspace-picker.js';
import {WorkspaceRegistry,workspacePath} from './workspace-registry.js';
import {PiAttachments,submittedParts,IMAGE_LIMITS,FILE_LIMIT} from './attachments.js';
import {SessionExports} from './session-exports.js';
import {captureSessionArchive} from './session-archive.js';
import {HarnessDrafts} from './harness-drafts.js';
import {SessionOrganization} from './session-organization.js';
import {sessionFamily} from './session-family.js';
import {contextPreferences,contextPreferenceChange,CONTEXT_PREFERENCE_FIELDS} from './context-preferences.js';
import {ShortcutPreferences} from './shortcut-preferences.js';
import {ModelSettings} from './model-settings.js';
import {ModelAccountLogin,accountDeviceId} from './model-account-login.js';
import {ToolArgumentSnapshots} from './tool-argument-snapshots.js';
import {developerTools,developerToolsChange} from './developer-tools.js';
import {AppearancePreferences} from './appearance-preferences.js';
import {MetafolderPreferences} from './metafolder-preferences.js';
import {piPromptWrapping} from './prompt-wrapping.js';
import {lstatSync,mkdirSync,existsSync,readFileSync,readdirSync,writeFileSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {randomUUID,createHash} from 'node:crypto';
import {createAgentSession,ModelRuntime,SessionManager,DefaultResourceLoader,type AgentSession,type ExtensionAPI} from '@earendil-works/pi-coding-agent';
import {managedPiSettings} from './pi-privacy.js';
import {BrowserBroker} from '../../pi-browser/src/index.js';
import {homePackage} from '../../home-client/src/pi.js';
import {linuxPackage} from '../../pi-linux/src/index.js';
import {type Data,type DisplayEvent,PROTOCOL,identifier,text} from '../../protocol/src/index.js';
import {atomicJson,readJson,privateDir,paths} from './storage.js';
import {piScheduling} from './scheduling.js';
import {piLlamaCppSchemas} from './provider-compat.js';
import {Interactions} from './interactions.js';
import {piQuestions} from './questions.js';
import {isRoutineQuery} from './permissions.js';
import {branchContext,inspectBranchContext,branchPublicationContext} from './branches.js';
import {BranchPublications} from './branch-publications.js';
import {BranchIntents,branchBoundary,branchIntent,type BranchIntent} from './branch-intents.js';
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
import {PiPlanMode,PLAN_MODE_TYPE,currentPlanMode,planModeProjection,validatePlanMode,planCommand,type PlanModeRecord} from './plan-mode.js';
import {PiGoals,goalProjection,GOAL_GUIDANCE,GOAL_ROUND_TYPE} from './goals.js';
import {PiJobs,jobSpec,jobsExtension,shellJob,boundChild,JOB_GUIDANCE,type JobRecord,type JobSpec,type JobControl,type JobOutcome} from './jobs.js';
import type {Usage} from '@earendil-works/pi-ai';
const browserRecovery = readFileSync(new URL('../../../config/browser-recovery.md', import.meta.url), 'utf8');
interface Meta {permissionHistory?:PermissionRecord[];planModeBootstrap?:PlanModeRecord;delegation?:{parentId:string;jobId:string;allowedTools:string[];resources:Data};reasoning?:SavedReasoning;memoryStartSeq?:number;surface?:"linux"|"browser";id:string;cwd:string;file?:string;selection:Data;title:string;saved:boolean;policy:string;updatedAt:number;requests:string[];running:boolean;fork?:{sessionId:string;messageSeq:number;mode:'reply'|'edit'}}
interface Loaded {requestedMode?:InputMode;humanInput?:{requestId:string;mode:InputMode};inputMode?:InputMode|'unattributed';inputOrigin?:'user'|'goal'|'delegation'|'unattributed';voiceSeen?:boolean;skillInputs:Map<string,PreparedSkill>;permissionSteer?:{id:string;text:string};planMode:PiPlanMode;resources:Data;searchEnabled?:boolean;searchMode?:'configured'|'keyless';wiki?:WikiBinding;wikiRevision?:string;memory:DualMemoryClient;meta:Meta;session:AgentSession;manager:SessionManager;events:DisplayEvent[];goals:PiGoals;mcp?:ManagedMcp;reloading?:boolean;reloadError?:boolean;reload?:(options:{removeAutoCodemode:boolean;reason?:string})=>Promise<void>;reasoning?:PiReasoning;execution?:PiExecution;steering?:PiSteering;phase?:'preparing'|'running'|'settling';initialDelivered?:boolean;preparingInput?:boolean;interruptedInput?:boolean;observation?:ReturnType<typeof observeSession>;turnId?:string;activeRequestId?:string;cancelled:boolean;failed?:boolean;task?:Promise<void>}
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
  readonly branchIntents=new BranchIntents(join(this.dirs.state,'branch-intents.json'));
  private branchPublications=new BranchPublications(join(this.dirs.state,'branch-publications'),this.dirs.sessions);
  readonly appearance=new AppearancePreferences(join(this.dirs.config,'harness-appearance.json'));
  appearanceRevision=0;
  readonly wikiPreferences=new WikiPreferences(join(this.dirs.config,'wiki.json'));
  private wikiFailed=false;
  readonly searchPreferences=new SearchPreferences(join(this.dirs.config,'free-search.json'));
  private searchFailed=false;
  private searchSnapshot(){const profile=this.searchPreferences.describe(),targets=[...this.loaded.values()].filter(r=>r.meta.surface!=='browser'&&!r.meta.delegation),appliedSessions=targets.filter(r=>r.searchEnabled===profile.enabled&&(!profile.enabled||r.searchMode===profile.mode)).length;return {...profile,loadedSessions:targets.length,appliedSessions,pending:this.searchFailed||appliedSessions!==targets.length};}
  private searchReady(m:Meta){if(m.surface!=='browser'&&!m.delegation&&process.platform==='linux'&&this.searchSnapshot().pending)throw Error('Search settings are not confirmed in loaded conversations. Refresh Search settings before starting another Native turn.');}
  private searchGuard(){this.modelSettingsGuard();if(this.modelSettingsBusy||this.modelSettingsProblem||[...this.metadata.values()].some(m=>!this.queue(m).paused&&!!this.queue(m).next)||[...this.loaded.values()].some(r=>r.goals.armed))throw Error('Finish active work and pause queued prompts or goals before changing Search settings.');}
  private async applySearch(){
    this.searchGuard();this.mcpReloading=true;this.searchFailed=true;
    try{const profile=this.searchPreferences.describe();for(const row of [...this.loaded.values()].filter(r=>r.meta.surface!=='browser'&&!r.meta.delegation)){row.searchEnabled=undefined;row.searchMode=undefined;await row.reload!({removeAutoCodemode:false,reason:'search-profile'});if(this.searchPreferences.describe().revision!==profile.revision)throw Error('Search profile changed during application. Refresh before continuing.');}this.searchFailed=false;return this.searchSnapshot();}
    finally{this.mcpReloading=false;this.wakeGoals();}
  }
  private wikiSnapshot(){const profile=this.wikiPreferences.describe(),targets=[...this.loaded.values()].filter(r=>r.meta.surface!=='browser'&&!r.meta.delegation);const appliedSessions=targets.filter(r=>r.wikiRevision===profile.revision).length;return {...profile,loadedSessions:targets.length,appliedSessions,pending:this.wikiFailed||appliedSessions!==targets.length};}
  private wikiReceipts(){
    const profile=this.wikiPreferences.describe();if(!profile.value.vaultPath)return {configured:false,profileRevision:profile.revision,revision:null,rows:[],lock:null,blocked:false};
    const view=new WikiReceipts(this.dirs.state,profile.value.vaultPath).describe(),keys=new Set(view.rows.map(row=>row.key)),links=new Map<string,{sessionId:string;nativeEntryId:string;toolCallId:string}|null>();
    for(const owner of this.loaded.values())if(owner.meta.surface!=='browser'&&!owner.meta.delegation){for(const entry of owner.manager.getEntries().slice(-10000))if(entry.type==='message'&&entry.message.role==='assistant')for(const part of entry.message.content)if(part.type==='toolCall'){const key=wikiActionKey(owner.manager.getSessionId(),entry.id,part.id);if(keys.has(key))links.set(key,links.has(key)?null:{sessionId:owner.meta.id,nativeEntryId:entry.id,toolCallId:part.id});}}
    return {...view,configured:true,profileRevision:profile.revision,rows:view.rows.map(row=>({...row,source:links.get(row.key)??null}))};
  }
  private wikiReady(m:Meta){if(m.surface!=='browser'&&!m.delegation&&process.platform==='linux'&&this.wikiSnapshot().pending)throw Error('Wiki settings are not confirmed in loaded conversations. Refresh Wiki settings before starting another Native turn.');}
  private wikiGuard(){this.modelSettingsGuard();if(this.modelSettingsBusy||this.modelSettingsProblem||[...this.metadata.values()].some(m=>!this.queue(m).paused&&!!this.queue(m).next)||[...this.loaded.values()].some(r=>r.goals.armed))throw Error('Finish active work and pause queued prompts or goals before changing Wiki settings.');}
  private async applyWiki(){
    this.wikiGuard();this.mcpReloading=true;this.wikiFailed=true;
    try{const profile=this.wikiPreferences.describe();for(const row of [...this.loaded.values()].filter(r=>r.meta.surface!=='browser'&&!r.meta.delegation)){row.wikiRevision=undefined;await row.reload!({removeAutoCodemode:false,reason:'wiki-profile'});if(this.wikiPreferences.describe().revision!==profile.revision)throw Error('Wiki profile changed during application. Refresh before continuing.');row.wikiRevision=profile.revision;}this.wikiFailed=false;return this.wikiSnapshot();}
    finally{this.mcpReloading=false;this.wakeGoals();}
  }
  readonly metafolders=new MetafolderPreferences(join(this.dirs.config,'harness-metafolders.json'));
  metafoldersRevision=0;
  readonly attachments=new PiAttachments(this.dirs.state,(sid,part)=>this.events(this.getMeta(sid)).some(event=>event.type==='user/message'&&event.data.source?.sessionId!==sid&&(event.data.submittedContent??event.data.content??[]).some((p:Data)=>JSON.stringify(p)===JSON.stringify(part))));
  readonly sessionExports=new SessionExports(this.dirs.state,(sid,signal,parent)=>captureSessionArchive(this,sid,signal,parent));
  readonly voice=new PiVoice(undefined,(sid,message)=>{const m=this.metadata.get(sid);if(m)try{this.append(m,'runtime/warning',{message});}catch{/* Speech diagnostics cannot change agent execution. */}});
  async operatorDisconnected(sid:string){if(!this.connected(sid)){this.interactions.cancel(sid);await this.voice.release(sid);}}
  private voiceAuthority(m:Meta,surface:unknown){
    if(!['linux','browser'].includes(String(surface))||(m.surface??'linux')!==surface)throw Error('Choose the voice surface that owns this conversation.');
    const r=this.loaded.get(m.id),queue=this.queue(m);
    if(m.delegation||this.organization.archived(m.id))throw Error('Voice requires an available human conversation.');
    if(!this.connected(m.id))throw Error('Connect the conversation before opening voice.');
    if(this.quiescing||this.modelSettingsProblem||this.modelSettingsBusy||this.modelAccounts?.busy||this.mcpReloading||this.compactions.blocked(m.id)||this.mcpManagement.busySession(m.id)||this.improvements.busySession(m.id)||m.running||r?.reloading||r?.reloadError||queue.uncertain||!queue.paused&&queue.next)throw Error('Open an idle, confirmed conversation before starting voice.');
    r?.mcp?.assertReady();
  }
  private uploads=0;
  private harnessRequests=0;
  private referenceRequests=0;
  private previewReads=0;
  readonly filePreview=new PiFilePreview();
  private previewAuthority(sid:string){const m=this.getMeta(sid);if(this.quiescing||m.surface==='browser'||m.delegation||this.organization.archived(sid))throw new PreviewReadError('gateway/forbidden','File previews are unavailable in this conversation.');return m;}
  async previewFile(sid:string,kind:'stat'|'read'|'bytes',p:Data,signal=new AbortController().signal){const m=this.previewAuthority(sid),cwd=m.cwd;this.previewReads++;try{const result=await this.filePreview.read(cwd,kind,p,signal);if(this.previewAuthority(sid).cwd!==cwd)throw new PreviewReadError('gateway/forbidden','The preview workspace changed.');return result;}finally{this.previewReads--;}}
  private officePreview?:PiOfficePreview;
  private office(){
    if(this.officePreview)return this.officePreview;
    const backend=process.env.AUGMENTOR_OFFICE_BACKEND;
    if(backend&&backend!=='pinned-kit'&&backend!=='linux-native')throw new PreviewReadError('gateway/service-unavailable','Unknown Office backend.');
    return this.officePreview=new PiOfficePreview(async(scope,kind,p,signal)=>{if(this.previewAuthority(scope.sessionId).cwd!==scope.workspaceRoot)throw new PreviewReadError('gateway/forbidden','The preview workspace changed.');return this.previewFile(scope.sessionId,kind,p,signal);},backend==='linux-native'?createLinuxNativeOfficeConverter:undefined);
  }
  officeGeneration(sid:string,signal:AbortSignal){this.previewAuthority(sid);return this.office().generation(signal);}
  async previewOffice(sid:string,p:Data,signal:AbortSignal){const cwd=this.previewAuthority(sid).cwd;const result=await this.office().render({sessionId:sid,workspaceRoot:cwd},p,signal);if(this.previewAuthority(sid).cwd!==cwd)throw new PreviewReadError('gateway/forbidden','The preview workspace changed.');return result;}
  readonly fileReferences=new PiFileReferences();
  async listFileReferences(sid:string,query:unknown,signal=new AbortController().signal){const authority=()=>{const m=this.getMeta(sid);if(this.quiescing||m.surface==='browser'||m.delegation||this.organization.archived(sid))throw Error('File references are unavailable in this conversation.');return m;};const m=authority(),cwd=m.cwd;this.referenceRequests++;try{const result=await this.fileReferences.list(m.id,cwd,query,signal);if(authority().cwd!==cwd)throw Error('The reference workspace changed.');return result;}finally{this.referenceRequests--;}}
  async receiveHarnessRequest<T>(operation:()=>Promise<T>){if(this.quiescing)throw Error('Runtime is closing for maintenance.');this.harnessRequests++;try{return await operation();}finally{this.harnessRequests--;}}
  readonly harnessDrafts=new HarnessDrafts(this.dirs.state);
  private draftAuthority(sid:string){const m=this.getMeta(sid);if(this.quiescing||m.delegation||this.organization.archived(sid))throw Error('This conversation cannot edit Harness drafts.');return m;}
  async receiveDraftAttachment(sid:string,read:()=>Promise<Uint8Array>,expected:unknown,input:Data){this.draftAuthority(sid);this.harnessDrafts.checkAttachment(sid,expected,input);this.uploads++;try{const bytes=await read();this.draftAuthority(sid);this.harnessDrafts.checkAttachment(sid,expected,input,bytes.byteLength);const receipt=input.kind==='image'?await this.attachments.uploadImage(sid,bytes,input.name,input.mediaType):await this.attachments.upload(sid,bytes,input.name);this.draftAuthority(sid);const part=input.kind==='image'?{type:'image',...receipt}:{type:'file',attachment:(receipt as any).file,receiptId:receipt.receiptId};return this.harnessDrafts.attach(sid,expected,{...input,part},bytes);}finally{this.uploads--;}}
  draftAttachmentBytes(sid:string,id:unknown,sha256:unknown){this.getMeta(sid);return this.harnessDrafts.bytes(sid,id,sha256);}
  async receiveAttachmentUpload(sid:string,read:()=>Promise<Uint8Array>,name:string,mediaType?:any){
    const check=()=>{const m=this.getMeta(sid);if(this.quiescing||m.delegation||this.organization.archived(sid))throw Error('This conversation cannot accept uploads.');};
    check();this.uploads++;
    try{const data=await read();check();return await (mediaType?this.attachments.uploadImage(sid,data,name,mediaType):this.attachments.upload(sid,data,name));}
    finally{this.uploads--;}
  }
  async uploadFile(sid:string,data:Uint8Array,name:string,mediaType?:any){return this.receiveAttachmentUpload(sid,async()=>data,name,mediaType);}
  async attachmentImage(sid:string,ref:any){this.getMeta(sid);return this.attachments.image(sid,ref);}
  readonly interactions:Interactions;
  modelRuntime!:ModelRuntime;
  private modelChanges=0;private modelHint=0;private modelHintSignature='';
  get modelsRevision(){const signature=JSON.stringify([this.modelSettings.observationFingerprint,this.modelSettingsBusy,this.modelSettingsProblem,this.modelChanges??0,this.modelAccounts?.revision??0]);if(signature!==this.modelHintSignature){this.modelHintSignature=signature;this.modelHint=(this.modelHint??0)+1;}return this.modelHint;}
  private modelConfigurationProblem=false;
  private modelConfigurationBusy=false;
  private modelAccounts=new ModelAccountLogin(join(this.dirs.state,'model-account-logins.json'));
  private get modelSettingsProblem(){return !!(this.modelConfigurationProblem||this.modelAccounts?.needsRefresh);}
  private set modelSettingsProblem(value:boolean){this.modelConfigurationProblem=value;}
  private get modelSettingsBusy(){return !!(this.modelConfigurationBusy||this.modelAccounts?.busy);}
  private set modelSettingsBusy(value:boolean){this.modelConfigurationBusy=value;}
  private modelSettingsGuard(){if(this.quiescing||this.voice.active||this.modelSettingsBusy||this.mcpReloading||this.jobs.busy||this.compactions.busy||this.improvements.busy||this.mcpManagement.busy||[...this.metadata.values()].some(m=>m.running))throw Error('Finish or stop active work before changing model settings.');}
  private async applyModelSettings(config:Data,validated:ModelRuntime,deferred:ReadonlySet<string>){
    this.modelSettingsGuard();
    const file=join(this.dirs.agent,'models.json');let previous:Data|undefined;
    try{previous=readJson<Data>(file,{providers:{}});}catch{/* A complete valid configuration can repair malformed JSON. */}
    const prior=previous?.providers&&typeof previous.providers==='object'&&!Array.isArray(previous.providers)?previous.providers:{};
    const providers=[...new Set([...Object.keys(prior),...Object.keys(config.providers)])].filter(id=>JSON.stringify(prior[id])!==JSON.stringify(config.providers[id]));
    for(const r of this.loaded.values()){
      // A clean validator has no extension/virtual registrations. Unchanged
      // providers keep their existing SDK registrations and execution owner.
      if(!providers.includes(r.meta.selection.provider)||deferred.has(r.meta.selection.provider))continue;
      const model=validated.getModel(r.meta.selection.provider,r.meta.selection.model);
      if(!model)throw Error('A loaded conversation uses a model this edit removes. Keep that model configured.');
      requireThinking(model,r.session.thinkingLevel);
    }
    const currentOwners=[...this.loaded.values()].every(r=>JSON.stringify(this.modelRuntime.getModel(r.meta.selection.provider,r.meta.selection.model))===JSON.stringify(r.session.model));
    if(JSON.stringify(previous)===JSON.stringify(config)&&this.modelSettings.applied&&!this.modelSettingsProblem&&currentOwners)return;
    const fullRefresh=!this.modelSettings.applied||this.modelSettingsProblem||JSON.stringify({...previous,providers:undefined})!==JSON.stringify({...config,providers:undefined});
    this.modelSettingsBusy=true;
    this.modelSettingsProblem=true;
    try{
      try{atomicJson(file,config);}catch{throw Error('Model configuration persistence could not be confirmed. Refresh before editing again.');}
      this.modelSettingsProblem=true;
      await this.refreshModelSettings(fullRefresh?undefined:providers);
    }catch{throw Error('Model configuration application could not be confirmed. Refresh model settings before starting work. Nothing was retried.');}
    finally{this.modelSettingsBusy=false;}
  }
  private async refreshModelSettings(providers?:string[]){
    const fingerprint=this.modelSettings.fingerprint;
    const refreshed=await this.modelRuntime.refresh({allowNetwork:false,signal:AbortSignal.timeout(10000),...(providers?{providers}:{})});
    if(refreshed.aborted||refreshed.errors.size||this.modelRuntime.getError()||this.modelSettings.fingerprint!==fingerprint)throw Error('Pi could not apply the model configuration.');
    await this.reconcileModelOwners();
    this.modelSettings.markApplied(fingerprint);this.modelAccounts?.reconcile();this.modelSettingsProblem=false;
  }
  private async reconcileModelOwners(){
    for(const r of this.loaded.values()){
      const current=this.modelRuntime.getModel(r.meta.selection.provider,r.meta.selection.model);
      if(!current)throw Error('A loaded model is unavailable.');
      requireThinking(current,r.session.thinkingLevel);
      if(JSON.stringify(current)!==JSON.stringify(r.session.model))await r.session.setModel(current);
    }
  }
  private async logoutModelAccount(provider:unknown,revision:unknown){
    this.modelSettingsGuard();
    if(this.modelSettingsProblem||this.modelSettingsBusy||!this.modelSettings.applied)throw Error('Refresh model settings before signing out.');
    const account=await this.modelSettings.requireOAuthAccount(provider,revision);
    this.modelSettingsGuard();
    if([...this.metadata.values()].some(m=>!this.queue(m).paused&&!!this.queue(m).next)||[...this.loaded.values()].some(r=>r.goals.armed))throw Error('Pause queued prompts and goals before signing out.');
    const fingerprint=this.modelSettings.fingerprint;
    this.modelSettingsBusy=true;this.modelSettingsProblem=true;this.modelSettings.cancelDiscoveries();
    try{
      await this.modelRuntime.logout(account,{signal:AbortSignal.timeout(10000)});
      if(this.modelRuntime.getError()||this.modelSettings.fingerprint!==fingerprint)throw Error('Model configuration changed during sign-out.');
      await this.reconcileModelOwners();
      const view=await this.modelSettings.describe();
      if(view.accounts.some(row=>row.provider===account))throw Error('The account is still stored.');
      this.modelSettings.markApplied(fingerprint);this.modelSettingsProblem=false;
      return view;
    }catch{throw Error('Account sign-out could not be confirmed. Refresh model settings before starting work or trying again. Nothing was retried.');}
    finally{this.modelSettingsBusy=false;this.modelChanges=(this.modelChanges??0)+1;}
  }
  private async describeModelAccounts(){
    const credentials=await this.modelRuntime.listCredentials({signal:AbortSignal.timeout(5000)}).catch(()=>{throw Error('Pi credential metadata is unavailable.');});
    const providers=this.modelRuntime.getProviders().filter(provider=>typeof provider.auth.oauth?.login==='function').map(provider=>({provider:provider.id,name:provider.auth.oauth!.name}));
    if(providers.length>256||credentials.length>256)throw Error('The account catalog exceeds the editor limit.');
    return {...this.modelAccounts.describe(),providers,accounts:credentials.filter(row=>row.type==='oauth').map(row=>({provider:row.providerId,registered:!!this.modelRuntime.getProvider(row.providerId)}))};
  }
  private startModelAccount(provider:unknown,revision:unknown,requestId:unknown){
    this.modelSettingsGuard();
    if(this.modelSettingsProblem||!this.modelSettings.applied)throw Error('Refresh model settings before signing in.');
    if([...this.metadata.values()].some(m=>!this.queue(m).paused&&!!this.queue(m).next)||[...this.loaded.values()].some(r=>r.goals.armed))throw Error('Pause queued prompts and goals before signing in.');
    const account=this.modelSettings.requireOAuthLogin(provider,revision),fingerprint=this.modelSettings.fingerprint;
    this.modelSettings.cancelDiscoveries();
    return this.modelAccounts.start(account,requestId,async interaction=>{
      await this.modelRuntime.login(account,'oauth',interaction,{agentName:'Augmentor Harness',getDeviceId:()=>accountDeviceId(join(this.dirs.agent,'account-device.json'))});
      if(this.quiescing||this.modelRuntime.getError()||this.modelSettings.fingerprint!==fingerprint)throw Error('Account configuration is unconfirmed.');
      await this.reconcileModelOwners();
      const credentials=await this.modelRuntime.listCredentials({signal:interaction.signal});
      if(!credentials.some(row=>row.providerId===account&&row.type==='oauth'))throw Error('Account credential is unconfirmed.');
      this.modelSettings.markApplied(fingerprint);
    });
  }
  private async reloadModelSettings(){
    this.modelSettingsGuard();this.modelSettingsBusy=true;this.modelSettingsProblem=true;this.modelSettings.cancelDiscoveries();
    try{await this.refreshModelSettings();}
    catch{throw Error('Pi could not confirm the stored model configuration. Work stays blocked. Inspect the profile and refresh again. Nothing was retried.');}
    finally{this.modelSettingsBusy=false;}
  }
  private modelSettings=new ModelSettings(join(this.dirs.agent,'models.json'),()=>this.modelRuntime,()=>this.modelSettingsGuard(),(config,validated,deferred)=>this.applyModelSettings(config,validated,deferred));
  async discoverModels(request:Data,signal?:AbortSignal){if(this.quiescing||this.modelSettingsProblem||this.modelSettingsBusy)throw Error('Refresh model settings and finish maintenance before listing models.');return this.modelSettings.discover(request,signal);}
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
    this.interactions=new Interactions(publish,connected,Number(process.env.AUGMENTOR_PI_INTERACTION_TIMEOUT||120000),15000,(ownerId,id,kind,active)=>this.loaded.get(ownerId)?.observation?.waiting(id,kind,active));
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
  async init(){await this.sessionExports.init();this.modelRuntime=await ModelRuntime.create({authPath:join(this.dirs.agent,'auth.json'),modelsPath:join(this.dirs.agent,'models.json'),modelsStorePath:join(this.dirs.agent,'models-store.json'),allowModelNetwork:false});
    if(this.modelRuntime.getError())throw new Error(this.modelRuntime.getError());
    this.modelSettings.markApplied();
    for(const m of this.metadata.values()){
      this.queue(m).recover();
      if(m.running){if(this.history(m).last()?.type==='turn/end'){m.running=false;this.save(m);continue;}this.append(m,'turn/end',{reason:{kind:'interrupted'},message:'Runtime stopped. The previous action outcome may be unknown; the prompt was not replayed.'});m.running=false;this.save(m);}
    }
  }
  private queue(m:Meta){let queue=this.queues.get(m.id);if(!queue){queue=new PiPromptQueue(join(this.dirs.sessions,m.id+'.queue.json'),m.id,()=>this.publish(m.id,{method:'session/queue',payload:{sessionId:m.id,...this.queueSnapshot(m.id)}}));this.queues.set(m.id,queue);}return queue;}
  queueSnapshot(id:unknown){const m=this.getMeta(id),r=this.loaded.get(m.id);return this.queue(m).snapshot(!!r&&m.running&&!r.cancelled&&r.phase!=='settling');}
  save(m:Meta){atomicJson(join(this.dirs.sessions,m.id+'.meta.json'),m);}
  persistSettings(){this.settings.revision++;atomicJson(join(this.dirs.config,'settings.json'),this.settings);}
  private shortcutPreferences=new ShortcutPreferences(()=>{const raw=this.settings.shortcutBindings;if(raw===undefined)return null;if(typeof raw!=='string')throw Error('Shortcut preferences are unreadable.');return raw;},raw=>{if(!Number.isSafeInteger(this.settings.revision)||this.settings.revision<0)throw Error('The settings revision is unavailable.');const next={...this.settings,revision:this.settings.revision+1,shortcutBindings:raw};atomicJson(join(this.dirs.config,'settings.json'),next);this.settings=next;});
  get shortcutSettingsRevision(){return this.settings.revision;}
  private permissionSnapshot(m:Meta,before?:unknown){
    const all=permissionHistory(m);let end=all.length;
    if(before!==undefined){end=all.findIndex(r=>r.revision===before);if(end<0)throw Error('The permission-history cursor is unavailable.');}
    const entries=all.slice(Math.max(0,end-20),end);
    return {available:true,...permissionSelection(m),origin:m.delegation?{kind:'accepted-job-grant',parentId:m.delegation.parentId,jobId:m.delegation.jobId}:m.fork?{kind:'branch-boundary',...m.fork}:{kind:'conversation-metadata'},canSelect:!m.delegation&&!this.organization.archived(m.id),options:permissionOptions(),history:{entries,hasMore:end>entries.length,cursor:entries[0]?.revision??null},boundary:'future authorization checks; running work and accepted job grants stay unchanged',persistence:'atomic host metadata; message-sequence policy history'};
  }
  private selectPermission(p:Data){
    const m=this.getMeta(p.sessionId);if(m.delegation||this.organization.archived(m.id))throw Error('Restore a root operator conversation before changing permission mode.');
    const previous=permissionSelection(m),change=permissionChange(m,p.preset,p.expectedRevision,this.history(m).lastSeq,Date.now(),randomUUID());
    if(change.outcome==='noop')return {accepted:true,outcome:'noop',...this.permissionSnapshot(m)};
    const next={...m,policy:change.policy,permissionHistory:change.permissionHistory};this.save(next);m.policy=next.policy;m.permissionHistory=next.permissionHistory;
    const data={previous:previous.currentValue,currentValue:m.policy,revision:change.permissionHistory.at(-1)!.revision,boundary:'future authorization checks; running work and accepted job grants stay unchanged'};
    try{this.append(m,'session/permission',data);this.loaded.get(m.id)?.observation?.record('execution/permission',data);}catch{console.warn('Permission mode was saved; its display/diagnostic receipt has a gap.');}
    this.publish(m.id,{method:'permission/updated',payload:{sessionId:m.id,revision:data.revision}});return {accepted:true,outcome:'committed',...this.permissionSnapshot(m)};
  }
  private rejectManagedInput(m:Meta,r:Loaded|undefined,error:unknown){
    if(r&&this.loaded.get(m.id)===r&&m.running){r.failed=true;try{this.append(m,'runtime/error',{message:'Managed input was rejected before model delivery: '+String(error),incomplete:true});}catch{}}
    // The SDK reports a thrown input-handler error and continues. A managed
    // control/source failure must instead finish the input without inference.
    return {action:'handled' as const};
  }
  private permissionInput(m:Meta){return (pi:ExtensionAPI)=>pi.on('input',event=>{
    if(typeof event.text!=='string')return;
    const r=this.loaded.get(m.id);
    try{
      const command=permissionCommand(event.text);if(!command)return;
      const steering=event.streamingBehavior==='steer',source=steering?r?.permissionSteer?.text:r?.activeRequestId?this.queue(m).read(r.activeRequestId).input:undefined;
      if(!r||!m.running||r.cancelled||event.source!=='rpc'||(!steering&&!r.preparingInput)||source===undefined||source.trim()!==event.text.trim()||!permissionCommand(source))throw Error('A permission command requires the exact admitted human input.');
      if(event.images?.length)throw Error('Attachments cannot accompany /permission.');
      if(command.preset!==null)this.selectPermission({sessionId:m.id,preset:command.preset,expectedRevision:permissionSelection(m).revision});
      return {action:'handled' as const};
    }catch(error){return this.rejectManagedInput(m,r,error);}
  });}
  private skillsInput(m:Meta){return (pi:ExtensionAPI)=>pi.on('input',async event=>{
    if(typeof event.text!=='string')return;
    const r=this.loaded.get(m.id),steer=event.streamingBehavior==='steer',requestId=steer?r?.permissionSteer?.id:r?.activeRequestId;
    if(!r||event.source!=='rpc'||!m.running||r.cancelled||!requestId||!steer&&!r.preparingInput)return;
    const turnId=r.turnId,current=()=>this.loaded.get(m.id)===r&&m.running&&r.turnId===turnId&&(steer?r.permissionSteer?.id===requestId:r.activeRequestId===requestId&&r.preparingInput);
    try{
      const prepared=await prepareApprovedSkill(r.session.resourceLoader.getSkills().skills,event.text,name=>!!r.session.extensionRunner.getCommand(name)||r.session.promptTemplates.some(template=>template.name===name));
      if(!current()||r.cancelled)return {action:'handled' as const};
      if(!prepared)return;
      r.skillInputs.set(requestId,prepared);return {action:'transform' as const,text:prepared.text};
    }catch(error){return current()&&!r.cancelled?this.rejectManagedInput(m,r,error):{action:'handled' as const};}
  });}
  private skillsSnapshot(m:Meta){
    const r=this.loaded.get(m.id);
    if(m.surface==='browser'||m.delegation)return {sessionId:m.id,available:true,revision:'excluded',skills:[],origin:'this surface has no human skill resources'};
    if(!r||r.reloading||r.reloadError)return {sessionId:m.id,available:false,reason:'The selected conversation has no confirmed loaded SDK resources.'};
    return {sessionId:m.id,...skillCatalog(r.session.resourceLoader.getSkills().skills,name=>!!r.session.extensionRunner.getCommand(name)||r.session.promptTemplates.some(template=>template.name===name))};
  }
  private permissionDefaultSnapshot(){return {ns:'permission',revision:this.settings.revision,value:{defaultPreset:this.settings.defaultPreset},writableFields:['defaultPreset'],options:[{id:'read-only',label:'Read Only'},{id:'workspace-write',label:'Ask before actions'},{id:'danger-full-access',label:'Full access'}]};}
  private developerToolsSnapshot(){return {ns:'ui-settings',revision:this.settings.revision,value:developerTools(this.settings.developerTools),writableFields:['enabled']};}
  contextPreferenceSnapshot(){return {ns:'dsh-context',revision:this.settings.revision,value:contextPreferences(this.settings.contextPreferences),writableFields:CONTEXT_PREFERENCE_FIELDS};}
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
  getMeta(id:unknown){const m=this.metadata.get(identifier(id));if(!m)throw new Error('Conversation not found');permissionSelection(m);return m;}
  jobInspectionTarget(parentId:unknown,jobId:unknown){
    const parent=this.getMeta(parentId);
    if(parent.delegation||this.jobs.problem)throw Error('The parent job catalogue is unavailable for child inspection.');
    const job=this.jobs.lookup(parent.id,identifier(jobId)),child=job.childId?this.metadata.get(job.childId):undefined;
    if(!['delegate','desktop'].includes(job.spec.kind)||!child||child.id===parent.id||child.delegation?.parentId!==parent.id||child.delegation.jobId!==job.id)throw Error('This saved job has no verified child conversation.');
    return child.id;
  }
  inspectionSessionRow(id:unknown){
    const m=this.getMeta(id);let running=m.running;
    if(m.delegation){try{const job=this.jobs.lookup(m.delegation.parentId,m.delegation.jobId);running=job.childId===m.id&&['starting','running','stopping'].includes(job.state);}catch{running=false;}}
    return {sessionId:m.id,cwd:m.cwd,agentPreset:m.surface==='browser'?'augmentor-browser-pi':'augmentor-linux-pi',title:m.title,updatedAt:m.updatedAt,saved:m.saved,running,blank:!m.title};
  }
  reasoningSettings(m:Meta){return savedReasoning(m.reasoning,m.file&&existsSync(m.file)?SessionManager.open(m.file).buildSessionContext().thinkingLevel:'off');}
  async reasoningState(m:Meta){const loaded=await this.load(m),config=reasoningConfig(this.settings.reasoning),saved=this.reasoningSettings(m),model=loaded.session.model!;
    const preset=m.surface==='browser'?'augmentor-browser-pi':'augmentor-linux-pi';
    const route=config.routes.find(r=>r.provider===model.provider&&r.model===model.id);
    return {...saved,availableLevels:getSupportedThinkingLevels(model),policy:{...config,revision:this.settings.revision},route:route??null,lastDecision:loaded.reasoning?.snapshot()??null,adaptiveStatus:saved.mode==='manual'?'manual-override':!config.enabled?'policy-disabled':!config.presets.includes(preset)?'preset-excluded':!route?'unmapped-model':'configured'};
  }
  policy(m:Meta){return (pi:ExtensionAPI)=>{
    // Resource startup/reload may call the SDK's sendUserMessage API. Only
    // an admitted Host turn may deliver input into this conversation's loop.
    pi.on('input',()=>{permissionSelection(m);return this.mcpReloading||!m.running?{action:'handled'}:undefined;});
    pi.on('tool_call',async e=>{
    if(m.delegation&&!m.delegation.allowedTools.includes(e.toolName))return {block:true,reason:'This tool is outside the delegated job’s explicit grants.'};
    if((this.mcpReloading||!m.running)&&e.toolName!=='linux_desktop_stop')return {block:true,reason:'No admitted Host turn is available for this tool call.'};
    if(e.toolName==='linux_desktop_stop'){await Promise.all(this.jobs.list(m.id).filter(row=>row.kind==='desktop'&&['starting','running','stopping'].includes(row.state)).map(row=>this.jobs.cancel(m.id,row.id)));this.desktopSpecialist.cancel('pi:'+m.id);}
    if(m.surface==='browser'&&!['job_start','job_list','job_read','job_wait','job_cancel','get_goal','create_goal','update_goal','plan_read','plan_update','exit_plan_mode','browser_tabs_list','browser_screenshot','browser_snapshot','browser_navigate','browser_click','browser_type','memory_recall','memory_source','tool_result_excerpt','home_devices','home_set','home_read','home_status','home_request','home_result','home_cancel'].includes(e.toolName))
      return {block:true,reason:'This browser chat can only use its browser tools.'};
    if((this.desktopSpecialist.busy()||this.jobs.busyKind('desktop'))&&['linux_desktop_connect','linux_desktop_snapshot','linux_desktop_action'].includes(e.toolName))return {block:true,reason:'A desktop specialist owns the desktop. Wait for it or Stop it before using direct desktop tools.'};
    if(m.surface!=='browser'&&e.toolName==='wiki_query'&&this.loaded.get(m.id)?.wiki?.isRead(e.toolName))return;
    if(m.surface!=='browser'&&this.loaded.get(m.id)?.searchEnabled&&['web_search','web_fetch'].includes(e.toolName))return;
    if(m.surface!=='browser'&&this.loaded.get(m.id)?.mcp?.isRead(e.toolName))return;
    if(['job_list','job_read','job_wait','job_cancel','job_start','get_goal','plan_read','home_devices','home_read','home_status','home_result','home_cancel','desktop_delegate','desktop_evidence','memory_recall','memory_source','tool_result_excerpt','read','ls','find','grep','linux_system_profile','linux_desktop_observe','linux_desktop_connect','linux_desktop_snapshot','linux_desktop_stop','ask_user','exit_plan_mode','browser_tabs_list','browser_screenshot','browser_snapshot'].includes(e.toolName))return;
    if(e.toolName==='bash'&&isRoutineQuery(e.input.command))return;
    if(m.policy==='read-only')return {block:true,reason:'Read-only chat: actions that can change state are disabled.'};
    if(['home_request','home_set'].includes(e.toolName))return; // Persistent NAS pairing grants the scoped Home capability.
    if(m.policy!=='danger-full-access'&&!await this.interactions.approve(m.delegation?.parentId??m.id,e.toolName,e.input,m.id))return {block:true,reason:'Action not approved, cancelled or no user interface connected.'};
    if(permissionSelection(m).currentValue==='read-only')return {block:true,reason:'Permission mode changed to Read Only while approval was pending; no action was dispatched.'};
  });};}
  async load(m:Meta,branchManager?:SessionManager){permissionSelection(m);this.wikiReady(m);this.searchReady(m);let record=this.loaded.get(m.id);if(record){record.mcp?.assertReady();return record;}
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
      if(record?.searchEnabled&&['web_search','web_fetch'].includes(name))return {effect:()=> 'read'};
      const definition=resourceLoader.getExtensions().extensions.flatMap(extension=>[...extension.tools.values()]).find(tool=>tool.definition.name===name)?.definition;
      return (definition as (typeof definition & {augmentorExecution?:ExecutionContract}))?.augmentorExecution??(mcp?.isRead(name)?{effect:()=> 'read'}:undefined);
    },(toolCallId,toolName)=>mcp?.takeResultIdentity(toolCallId,toolName));
    const settingsManager=managedPiSettings(!m.delegation);
    const resources=m.delegation?.resources??readJson<Data>(join(this.dirs.config,'resources.json'),{sources:[],skills:[]});
    const goals=new PiGoals({getBranch:()=>manager.getBranch(),appendCustomEntry:(type,data)=>manager.appendCustomEntry(type,data),getSessionId:()=>manager.getSessionId()},()=>{this.publish(m.id,{method:'goal/updated',payload:{sessionId:m.id}});record?.observation?.record('goal/update',{activation:goals.armed?'armed':'disarmed'});});
    const provenance=new ContextProvenance(()=>this.observations.policy().capturePayloads);
    const managedMemory=managedPiMemory(memory,!m.fork,contribution=>{provenance.memory(contribution);if(contribution.mode==='voice'&&record)record.voiceSeen=true;},()=>record?.requestedMode??'text');
    if(!Array.isArray(resources.sources)||!Array.isArray(resources.skills))throw new Error('Invalid Pi resource configuration');
    const wikiNative=process.platform==='linux'&&m.surface!=='browser'&&!m.delegation;let wiki:WikiBinding|undefined,wikiRevision:string|undefined;
    const wikiFactory=(pi:ExtensionAPI)=>{const profile=this.wikiPreferences.describe();wiki=profile.value.enabled?new WikiBinding({...profile.value,enabled:true},this.dirs.state):undefined;wikiRevision=profile.revision;if(record)record.wiki=wiki;wiki?.factory(pi);};
    const checkPlanNames=()=>{if(m.delegation)return;const extensions=resourceLoader.getExtensions().extensions;if(extensions.flatMap(e=>[...e.tools.values()]).filter(t=>t.definition.name==='exit_plan_mode').length!==1||extensions.some(e=>e.commands.has('plan')||e.commands.has('permission')))throw Error('A product permission/plan command or exit_plan_mode tool collides with an approved resource. Inspect its configuration.');};
    const checkWikiNames=()=>{if(wiki){const names=resourceLoader.getExtensions().extensions.flatMap(extension=>[...extension.tools.values()].map(tool=>tool.definition.name));for(const name of ['wiki_query','wiki_write','wiki_rename','wiki_scaffold','wiki_archive','wiki_lint'])if(names.filter(value=>value===name).length!==1)throw Error('Wiki tool name collision; inspect approved resource configuration.');}};
    let searchEnabled:boolean|undefined,searchMode:'configured'|'keyless'|undefined;
    const searchFactory=(pi:ExtensionAPI)=>{const profile=this.searchPreferences.describe();searchEnabled=profile.enabled;searchMode=profile.mode;const confirmed=()=>{const p=this.searchPreferences.describe();if(!p.enabled||p.mode!==searchMode)throw Error('Search settings changed; refresh before continuing.');return p;};if(searchEnabled)(searchMode==='keyless'?keylessSearchExtension(()=>confirmed().keylessValue):freeSearchExtension(()=>confirmed().value))(pi);};
    const checkSearchNames=()=>{if(searchEnabled){const names=resourceLoader.getExtensions().extensions.flatMap(extension=>[...extension.tools.values()].map(tool=>tool.definition.name));for(const name of ['web_search','web_fetch'])if(names.filter(value=>value===name).length!==1)throw Error('Search tool name collision; inspect approved resource configuration.');}};
    let manager:SessionManager;
    const planMode=new PiPlanMode({manager:()=>manager,running:()=>record?.session.isStreaming??false,admitted:()=>m.running&&!record?.cancelled&&!record?.session.isCompacting,
      dismissed:()=>{if(goals.armed){goals.disarm();this.publish(m.id,{method:'goal/updated',payload:{sessionId:m.id}});}},
      sessionId:m.id,interactions:this.interactions,changed:()=>{this.publish(m.id,{method:'plan-mode/updated',payload:{sessionId:m.id}});record?.observation?.record('planning/mode',planMode.view());},warning:message=>this.append(m,'runtime/warning',{message}),
      append:value=>{
        const saved=manager.getSessionFile();if(!saved||!existsSync(saved)){m.planModeBootstrap=value;this.save(m);}
        manager.appendCustomEntry(PLAN_MODE_TYPE,value);
        if(saved&&existsSync(saved)&&m.planModeBootstrap){delete m.planModeBootstrap;this.save(m);}
      }});
    const resourceLoader:DefaultResourceLoader=new DefaultResourceLoader({cwd:m.cwd,agentDir:this.dirs.agent,settingsManager,noExtensions:true,noSkills:true,noContextFiles:true,noThemes:true,
      additionalExtensionPaths:m.surface==='browser'?[]:resources.sources,additionalSkillPaths:m.surface==='browser'?[]:resources.skills,additionalPromptTemplatePaths:[privateDir(join(this.dirs.agent,'prompts'))],
      extensionFactories:[piScheduling,piLlamaCppSchemas,this.policy(m),...(m.delegation?[]:[this.permissionInput(m)]),...(wikiNative?[{name:'augmentor-free-search',factory:searchFactory}]:[]),...(wikiNative?[{name:'augmentor-wiki',factory:wikiFactory}]:[]),...(m.delegation?[]:[jobsExtension(m.id,this.jobs,(spec,signal)=>this.startJob(m,spec,signal))]),goals.extension,...(m.delegation?[]:[planMode.extension]),piPlans(revision=>{this.publish(m.id,{method:'plan/updated',payload:{sessionId:m.id,revision}});record?.observation?.record('planning/update',{revision});}),piToolBudget(changes=>record?.observation?.record('context/budget',{changes,units:'unicode-code-points'})),piReassessment(data=>record?.observation?.record('execution/checkpoint',data)),execution.extension,homePackage('pi:'+m.id),pi=>memoryPackage(pi,m.fork?undefined:'pi:'+m.id),managedMemory.extension,...(mcp?mcp.factories():[]),...(m.surface==='browser'?[this.browser.package(m.delegation?.parentId??m.id)]:process.env.AUGMENTOR_PI_LINUX_TOOLS==='0'?[]:[piQuestions(this.interactions,m.delegation?.parentId??m.id,m.id),linuxPackage(this.backend),desktopPackage('pi:'+m.id),this.desktopSpecialist.package({owner:'pi:'+m.id,cwd:m.cwd,agentDir:this.dirs.agent,modelRuntime:this.modelRuntime,policy:m.policy,approve:(name,args)=>this.interactions.approve(m.id,name,args),cancelInteractions:()=>this.interactions.cancel(m.id),progress:info=>this.append(m,'desktop/progress',info)},(brief,toolCallId,signal)=>this.awaitDesktopJob(m,brief,toolCallId,signal))]),{name:'augmentor-prompt-wrapping',factory:piPromptWrapping(()=>({revision:this.settings.revision,value:this.settings.contextPreferences}),row=>provenance.promptWrapping(row))},{name:'augmentor-context-observer',factory:provenance.extension},...(!m.delegation&&m.surface!=='browser'?[this.skillsInput(m)]:[])],
      appendSystemPrompt:[browserRecovery,PLAN_GUIDANCE,GOAL_GUIDANCE,...(m.surface!=='browser'&&(!m.delegation||m.delegation.allowedTools.includes('read'))?[FILE_REFERENCE_PROMPT]:[]),...(m.delegation?['You are a bounded delegated worker. Follow the supplied task and all constraints. Do not start jobs, persistent goals or other workers. Your tools are explicitly granted by the parent conversation. Report failures and unknown outcomes; verify changes.']:[JOB_GUIDANCE]),m.surface==='browser'?'You are Augmentor Agent for Browser, powered by Pi. Use the browser tools to inspect and act in the connected visible browser. Read a fresh snapshot before actions. Stop on stale targets or denied actions. Report unknown outcomes honestly; do not replay actions.': `You are Augmentor Agent Desktop, powered by Pi. The operating system is ${process.platform}. Use tools to check actual facts. Keep the user informed. Use linux_browser_open for visible Chromium; never claim dispatch proves a page loaded. Use the platform accessibility observations for desktop structure. Stop on stale targets or denied actions. Use linux_desktop_connect and the user’s OS consent for desktop control. Use fresh screenshots before each action, then verify the result. A model must support image input. Stop on focus changes; never replay an unknown input outcome. Ask the user only when required information is missing.`,...(m.surface!=='browser'&&process.env.AUGMENTOR_PI_LINUX_TOOLS!=='0'?[DESKTOP_DELEGATION_GUIDANCE]:[])],
    });await resourceLoader.reload();
    checkPlanNames();checkWikiNames();
    checkSearchNames();
    const errors=resourceLoader.getExtensions().errors;if(errors.length)throw new Error('Pi extension loading failed: '+errors.map(e=>e.error).join('; '));
    manager=branchManager??(m.file&&existsSync(m.file)?SessionManager.open(m.file):SessionManager.create(m.cwd,join(this.dirs.sessions,m.id)));
    if((!m.file||!existsSync(m.file))&&m.planModeBootstrap&&!currentPlanMode(manager).entryId)manager.appendCustomEntry(PLAN_MODE_TYPE,validatePlanMode(m.planModeBootstrap));
    const repaired=trimSavedToolContext(manager);
    const reasoning=savedReasoning(m.reasoning,manager.buildSessionContext().thinkingLevel);requireThinking(model,reasoning.thinkingLevel);
    const created=await createAgentSession({cwd:m.cwd,agentDir:this.dirs.agent,modelRuntime:this.modelRuntime,model,thinkingLevel:reasoning.thinkingLevel,settingsManager,resourceLoader,sessionManager:manager,...(m.surface==='browser'?{tools:resourceLoader.getExtensions().extensions.flatMap(e=>[...e.tools.values()].filter(tool=>tool.definition.defaultActive!==false).map(tool=>tool.definition.name))}:{noTools:'builtin' as const,tools:['read','write','edit','bash','ls','find','grep'].map(name=>'+'+name)})});
    if(created.modelFallbackMessage){created.session.dispose();throw new Error('Pi attempted a model substitution: '+created.modelFallbackMessage);}
    if(created.session.model?.id!==m.selection.model||created.session.model?.provider!==m.selection.provider){created.session.dispose();throw new Error('Pi selected a different model.');}
    if(m.surface!=='browser')created.session.agent.toolExecution='sequential';
    if(m.delegation){const callable=created.session.getCallableToolNames();if(m.delegation.allowedTools.some(name=>!callable.includes(name))){created.session.dispose();throw Error('A delegated tool grant is unavailable in the child resource registry.');}created.session.setActiveToolsByName(m.delegation.allowedTools);}
    // The public SDK setter always appends. Loading a saved owner for inspection
    // must not repeat its already stored title; retain SDK name normalization.
    const nativeTitle=m.title.replace(/[\r\n]+/g,' ').trim();
    if(m.title&&(manager.getSessionName()??'')!==nativeTitle)created.session.setSessionName(m.title);m.reasoning=reasoning;m.file=created.session.sessionFile;this.save(m);
    record={skillInputs:new Map(),planMode,resources:structuredClone(resources),searchEnabled,searchMode,wiki,wikiRevision,memory,meta:m,session:created.session,manager,events:this.events(m),goals,mcp,cancelled:false};this.loaded.set(m.id,record);
    record.voiceSeen=record.events.some(event=>event.data.inputMode==='voice');record.inputMode='unattributed';record.inputOrigin='unattributed';
    let history=record.events;
    if(m.fork){m.memoryStartSeq??=history.at(-1)?.seq??0;this.save(m);history=history.filter(e=>e.seq>m.memoryStartSeq!);}
    await memory.append(history.flatMap(event=>piTranscriptEvent(event)));
    await created.session.bindExtensions({mode:'rpc',uiContext:this.interactions.ui(m.delegation?.parentId??m.id,m.id),onError:error=>{if(record?.reloading)record.reloadError=true;this.append(m,'runtime/error',{message:record?.reloading?'A Pi resource reported a reload problem. Inspect the configuration receipt before continuing.':error.error});}});
    record.execution=execution;
    record.steering=new PiSteering(created.session);
    record.reasoning=new PiReasoning(created.session,m.surface==='browser'?'augmentor-browser-pi':'augmentor-linux-pi',data=>record!.observation?.record('execution/reasoning',data));
    const installBindings=()=>{
    execution.install(created.session);record!.steering!.install();record!.reasoning!.install();
    if(!m.delegation)planMode.install(created.session);
    provenance.attach(created.session,()=>record!.events);
    record.observation=observeSession(created.session,this.observations,m.id,
      ()=>({turnId:record!.turnId,compactionId:this.compactions.activeId(m.id),selected:{...m.selection},permissionPreset:m.policy,toolBudget:{...TOOL_BUDGET,units:'unicode-code-points'},execution:record!.execution?.describe(),reasoning:record!.reasoning?.snapshot()}),
      observation=>this.publish(m.id,{method:'observation/event',payload:{sessionId:m.id,observation}}),
      message=>this.append(m,'runtime/warning',{message}),provenance,managedMemory.finalPayload,piInputMode(()=>!m.delegation&&record?.humanInput?{...record.humanInput,voiceSeen:record.voiceSeen===true}:undefined,row=>provenance.inputMode(row)));
    return record!.observation;
    };
    const installed=installBindings();
    record.reload=async options=>{
      if(this.voice.owns(m.id))throw Error('Close voice before reloading its conversation.');
      record!.goals.disarm();if(wikiNative){record!.searchEnabled=undefined;record!.searchMode=undefined;}record!.reloading=true;record!.reloadError=false;
      try{
      // Unwind in reverse composition order; the public reload replaces the
      // runner captured by execution's nested-tool hooks, but keeps this owner.
      record!.observation?.dispose();record!.observation=undefined;
      planMode.dispose();record!.reasoning?.dispose();record!.steering?.dispose();execution.dispose();
      await created.session.reload({beforeSessionStart:()=>{
        checkPlanNames();checkWikiNames();
        checkSearchNames();
        if(options.removeAutoCodemode)created.session.setActiveToolsByName(created.session.getActiveToolNames().filter(name=>name!=='codemode'));
        installBindings();
      }});
      if(record!.reloadError||resourceLoader.getExtensions().errors.length)throw Error('An approved Pi resource failed to reload. Repair it before applying the configuration again.');
      const reloadedModel=created.session.model;
      if(!reloadedModel||reloadedModel.provider!==m.selection.provider||reloadedModel.id!==m.selection.model)throw Error('A reloaded resource changed the selected model. Choose the intended model explicitly before continuing.');
      requireThinking(reloadedModel,this.reasoningSettings(m).thinkingLevel);
      created.session.agent.toolExecution='sequential';
      record!.searchEnabled=searchEnabled;record!.searchMode=searchMode;
      const recordReload=()=>record!.observation?.record('session/reload',{reason:options.reason??'mcp-session-options',piVersion:'1.1.0'});recordReload();this.publish(m.id,{method:'skills/updated',payload:{sessionId:m.id}});
      }catch(error){record!.reloadError=true;throw error;}finally{record!.reloading=false;}
    };
    installed.record('session/load',{piVersion:'1.1.0',productVersion:RELEASE.version,
      surface:m.surface??'linux',policy:m.policy,...(m.fork?{fork:m.fork}:{})});
    if(mcp){const info=mcp.describe();if(info.servers.length||info.configurationErrors)installed.record('integration/mcp',info);if(info.configurationErrors)this.append(m,'runtime/warning',{message:'Managed MCP configuration contains errors. Some servers are unavailable; ordinary chat remains available.'});}
    if(repaired.length)installed.record('context/budget',{changes:repaired,units:'unicode-code-points',boundary:'before-session-owner-load'});
    const toolArguments=new ToolArgumentSnapshots(undefined,(chunk,requestId)=>{if(this.loaded.get(m.id)===record&&m.running)this.append(m,'assistant/chunk',{requestId,chunk});});let messageCaptureId:string|undefined;
    created.session.subscribe(e=>{
      if(e.type==='agent_start')messageCaptureId=undefined;
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
        const origin=m.delegation?'delegation':goalSource?'goal':requestId?'user':'unattributed';
        record!.inputOrigin=origin;record!.inputMode=origin==='user'?(admitted?.inputMode??'text'):origin==='unattributed'?'unattributed':'text';
        record!.requestedMode=record!.inputMode==='voice'?'voice':'text';
        record!.humanInput=origin==='user'&&requestId?{requestId,mode:admitted?.inputMode??'text'}:undefined;
        if(record!.inputMode==='voice')record!.voiceSeen=true;
        if(requestId&&!goalSource&&!m.delegation&&!record!.cancelled&&record!.turnId&&this.connected(m.id))this.voice.admit(m.id,requestId,record!.turnId);
        else if(!m.delegation)void this.voice.stop(m.id);
        const skillInvocation=requestId?deliveredSkill(record!.skillInputs.get(requestId),content,e.message):undefined;if(requestId)record!.skillInputs.delete(requestId);
        this.append(m,'user/message',{inputMode:record!.inputMode,source:{...(goalSource??{kind:origin}),sessionId:m.id,...(requestId?{rpcId:requestId}:{})},content,...(skillInvocation?{skillInvocation}:{}),...(submittedContent&&JSON.stringify(submittedContent)!==JSON.stringify(content)?{submittedContent}:{})});
      }
      if(e.type==='message_update'){
        const a=e.assistantMessageEvent,requestId=record!.observation?.currentRequestId();
        if(a.type==='text_delta')this.append(m,'assistant/chunk',{requestId,chunk:{type:'text-delta',text:a.delta}});
        if(a.type==='thinking_delta')this.append(m,'assistant/chunk',{requestId,chunk:{type:'reasoning-delta',text:a.delta}});
        try{const chunk=toolArguments.update(a,requestId);if(chunk)this.append(m,'assistant/chunk',{requestId,chunk});}catch{/* Inspection cannot change tool dispatch. */}
      }
      if(e.type==='message_start'&&e.message.role==='assistant'){toolArguments.begin();messageCaptureId=toolArguments.identity();}
      if(e.type==='message_end'&&e.message.role==='assistant'){
        toolArguments.end();
        this.append(m,'assistant/message',{inputMode:record!.inputMode??'unattributed',inputOrigin:record!.inputOrigin??'unattributed',...(record!.humanInput?{humanRequestId:record!.humanInput.requestId}:{}),requestId:record!.observation?.currentRequestId(),captureId:messageCaptureId,message:{content:e.message.content,stopReason:e.message.stopReason,timestamp:e.message.timestamp,usage:e.message.usage}});
        record!.failed=e.message.stopReason==='error';if(record!.failed&&!record!.steering?.waiting)this.append(m,'runtime/error',{message:e.message.errorMessage||'Model request failed'});
      }
      if(e.type==='tool_execution_start')this.append(m,'tool/call',{requestId:record!.observation?.currentRequestId(),captureId:messageCaptureId,name:e.toolName,toolCallId:e.toolCallId,...(e.parentToolCallId?{parentToolCallId:e.parentToolCallId,...toolArguments.captureExecutionArguments(e.args)}:{})});
      if(e.type==='tool_execution_end')this.fileReferences.invalidate(m.id);
      if(e.type==='tool_execution_end')this.append(m,'tool/result',{requestId:record!.observation?.currentRequestId(),captureId:messageCaptureId,name:e.toolName,toolCallId:e.toolCallId,...(e.parentToolCallId?{parentToolCallId:e.parentToolCallId}:{}),isError:e.isError,result:{...e.result,content:e.result.content.map((part:Data)=>part.type==='image'?{type:'text',text:'[Tool image omitted from this display projection; inspect native evidence]'}:part)}});
      if(e.type==='agent_end'){messageCaptureId=undefined;toolArguments.end();}
      if(!m.delegation){if(this.connected(m.id))this.voice.observe(m.id,e,record!.turnId);else void this.voice.release(m.id);}
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
    if(changes&&permissionSelection(m).currentValue==='read-only')throw Error('Permission mode changed to Read Only while job approval was pending.');
    signal?.throwIfAborted();const admitted=structuredClone(m);
    const result=this.jobs.start(m.id,spec,(row,control)=>spec.kind==='shell'?shellJob(admitted.cwd,row,control):spec.kind==='desktop'?this.desktopJob(admitted,row,control):this.delegateJob(admitted,row,control));
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
    const provenance=new ContextProvenance(()=>this.observations.policy().capturePayloads);
    const result=await this.desktopSpecialist.run({owner:'pi:'+parent.id,cwd:m.cwd,agentDir:this.dirs.agent,modelRuntime:this.modelRuntime,model,policy:parent.policy,approve:(name,args)=>this.interactions.approve(parent.id,name,args,m.id),cancelInteractions:()=>this.interactions.cancel(m.id),progress:info=>this.append(parent,'desktop/progress',{...info,jobId:row.id,childId:m.id}),extensionFactories:[piPromptWrapping(()=>({revision:this.settings.revision,value:this.settings.contextPreferences}),record=>provenance.promptWrapping(record)),provenance.extension],tracking:{jobId:row.id,childId:m.id,manager,thinkingLevel:effective,limits:{requests:row.spec.limits.maxRequests,tools:row.spec.limits.maxTools,timeoutMs:row.spec.limits.timeoutMs},maxTotalOutputTokens:row.spec.limits.maxOutputTokens,
      checkpoint:(result,outputTokens,usage)=>control.update({requests:result.counts.requests,tools:result.counts.tools,outputTokens,desktop:{...structuredClone(result),jobId:row.id,childId:m.id},usage:{provider:model.provider,model:model.id,value:structuredClone(usage)}}),
      onSession:(session,result)=>{
        m.running=true;this.save(m);this.append(m,'turn/start',{requestId:'desktop:'+row.id,jobId:row.id,parentId:parent.id});
        provenance.attach(session);const observation=observeSession(session,this.observations,m.id,()=>({turnId:row.id,selected:m.selection,permissionPreset:m.policy,execution:{specialist:true,limits:row.spec.limits}}),event=>this.publish(parent.id,{method:'job/observation',payload:{sessionId:parent.id,childId:m.id,jobId:row.id,observation:event}}),message=>this.append(m,'runtime/warning',{message}),provenance);observation.beginTurn({jobId:row.id,parentId:parent.id});
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
      if(child){child.goals.disarm();child.observation?.record('job/child-close',{jobId:row.id,parentId:parent.id});child.observation?.dispose();child.planMode.dispose();child.reasoning?.dispose();child.steering?.dispose();child.execution?.dispose();child.memory.close();await child.memory.flush();await child.session.extensionRunner.emit({type:'session_shutdown',reason:'quit'});child.session.dispose();this.loaded.delete(m.id);}
      void this.flushJobReceipts(parent.id).catch(()=>{});this.wakeGoals();
    }
  }
  async cancel(id:unknown,source='user'){
    const target=this.getMeta(id);if(target.delegation&&source==='user')return this.jobs.cancel(target.delegation.parentId,target.delegation.jobId);
    const m=this.getMeta(id),stoppingVoice=this.voice.stop(m.id),queue=this.queue(m);queue.pause();const r=this.loaded.get(m.id);let aborting:Promise<void>|undefined;
    const reserved=queue.next;if(reserved?.goalSource)queue.remove(reserved.id);
    const cancellingCompaction=this.compactions.cancelSession(m.id),cancellingMcp=this.mcpManagement.cancelSession(m.id),jobsWereRunning=this.jobs.busyOwner(m.id);const cancellingJobs=this.jobs.cancelOwner(m.id);
    if(r){try{source==='user'?r.goals.stop():r.goals.disarm();}catch{r.goals.disarm();this.append(m,'runtime/warning',{message:'Goal state could not be paused. Continuation is disarmed; inspect the preserved native original.'});}}
    if(m.running&&r){if(r.preparingInput)r.interruptedInput=true;r.cancelled=true;r.execution?.cancel();for(const requestId of r.steering?.withdraw()??[])queue.withdrawSteer(requestId);r.session.abortCompaction();aborting=r.session.abort();}
    if(source==='user'||m.running)r?.observation?.record('control/stop',{wasRunning:m.running,source});this.desktopSpecialist.cancel('pi:'+m.id);this.interactions.cancel(m.id);
    if(r)await r.memory.activity('stop');if(m.surface!=='browser')await desktopControl('stop','pi:'+m.id).catch(()=>{});if(aborting)await aborting;await cancellingJobs;await stoppingVoice;return {accepted:!!aborting||cancellingCompaction||cancellingMcp||jobsWereRunning,paused:true};
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
    const permissionSteer={id,text:attachmentInput.text};r.permissionSteer=permissionSteer;
    r.requestedMode=prior.inputMode??'text';
    const pending=r.steering!.enqueue(id,attachmentInput.text,result=>{
      if(result.action==='handled'){queue.handledSteer(id);r.execution!.steerHandled();this.append(m,'runtime/notice',{message:'The correction was handled by an input extension. No copy of that input was sent to the model.',submittedContent:submittedParts(prior.input??'',prior.attachments),source:{kind:'user',rpcId:id},incomplete:false});}
      r.observation?.record('execution/steer-input',{clientRequestId:id,action:result.action,handler:result.handler,skill:result.skill??r.skillInputs.get(id)?.receipt.name,template:result.template});
    },error=>{r.failed=true;r.execution!.steerFailed();this.append(m,'runtime/error',{message:'Correction input preparation failed: '+String(error)});},attachmentInput.images);
    r.observation?.record('execution/steer-requested',{clientRequestId:id,boundary:'provider-supersession; dispatched-tools-settle',input:'sdk-public-input-and-approved-resources'});
    this.append(m,'runtime/notice',{message:'Steering accepted. Obsolete generation is stopping; any dispatched tools will settle before the correction.',incomplete:false});
    try{const result=await pending;return {accepted:true,turnId,...(result.action==='handled'?{handled:true}:result.action==='cancelled'?{interruptedPreparation:true}:{})};}finally{if(r.permissionSteer===permissionSteer)delete r.permissionSteer;}
  }
  prepareBranch(p:Data){
    const boundary=branchBoundary(p),source=this.getMeta(boundary.sessionId);
    if(source.running)throw Error('Stop the current response before preparing a branch.');
    if(!source.file||!existsSync(source.file))throw Error('This conversation has no persisted Pi history yet.');
    inspectBranchContext(source.file,this.dirs.sessions,this.loaded.get(source.id)?.events??this.events(source),boundary.messageSeq,boundary.mode);
    return this.branchIntents.reserve(boundary,randomUUID());
  }
  private branchTargetEmpty(sid:string){
    if(this.loaded.has(sid)||this.metadata.has(sid))return false;
    if(process.platform==='linux'&&this.branchPublications.has(sid))return false;
    for(const name of readdirSync(this.dirs.sessions).filter(name=>name===sid||name.startsWith(sid+'.'))){
      const path=join(this.dirs.sessions,name),info=lstatSync(path);
      if(name!==sid||!info.isDirectory()||info.isSymbolicLink()||readdirSync(path).length)return false;
    }
    return true;
  }
  private committedBranch(intent:BranchIntent){
    const row=this.metadata.get(intent.newSessionId),fork={sessionId:intent.sessionId,messageSeq:intent.messageSeq,mode:intent.mode};
    const disk=readJson<Meta|null>(join(this.dirs.sessions,intent.newSessionId+'.meta.json'),null);
    if(!row||JSON.stringify(row.fork)!==JSON.stringify(fork)||!disk||disk.id!==row.id||JSON.stringify(disk.fork)!==JSON.stringify(fork)||disk.file&&!existsSync(disk.file)||!existsSync(join(this.dirs.sessions,row.id+'.events.jsonl')))throw Error('The branch is not fully published. Preserve its original files for recovery.');
    if(process.platform==='linux'&&this.branchPublications.has(intent.newSessionId))this.branchPublications.finish(intent);
    return row;
  }
  settleBranch(p:Data){
    const intent=branchIntent(p);this.getMeta(intent.sessionId);
    if(p.outcome==='created'){
      const row=this.committedBranch(intent),cleared=this.branchIntents.settle(intent);
      return {settled:true,cleared,outcome:'created',...this.branchRow(row)};
    }
    if(p.outcome!=='not-created')throw Error('Choose an explicit branch settlement outcome.');
    if(!this.branchTargetEmpty(intent.newSessionId))return {settled:false,outcome:'not-created',newSessionId:intent.newSessionId};
    return {settled:this.branchIntents.settle(intent),outcome:'not-created',newSessionId:intent.newSessionId};
  }
  async branch(p:Data){
    if(p.prepared!==undefined&&typeof p.prepared!=='boolean')throw Error('Invalid prepared branch flag.');
    const source=this.getMeta(p.sessionId),sid=identifier(p.newSessionId);
    if(!Number.isSafeInteger(p.messageSeq)||p.messageSeq<1||!['reply','edit'].includes(p.mode))throw new Error('Invalid branch target');
    const fork={sessionId:source.id,messageSeq:p.messageSeq,mode:p.mode as 'reply'|'edit'};
    const existing=this.metadata.get(sid);
    if(p.prepared===true&&process.platform==='linux'&&this.branchPublications.has(sid)){
      if(!existing){if(source.running)throw Error('Stop the current response before recovering its prepared branch.');this.branchIntents.begin(branchIntent(p));}
      const recovered=this.branchPublications.finish(branchIntent(p)) as Meta;
      if(!existing)this.metadata.set(sid,recovered);return this.branchRow(existing??recovered);
    }
    if(existing){if(JSON.stringify(existing.fork)!==JSON.stringify(fork))throw new Error('Conversation ID already exists');if(p.prepared===true)this.committedBranch(branchIntent(p));return this.branchRow(existing);}
    if(source.running)throw new Error('Stop the current response before branching or editing.');
    if(!source.file||!existsSync(source.file))throw new Error('This conversation has no persisted Pi history yet.');
    const reserved=this.branchIntents.list().find(row=>row.newSessionId===sid);
    if(p.prepared===true){this.branchIntents.begin(branchIntent(p));if(!this.branchTargetEmpty(sid))throw Error('Branch publication is incomplete. Original files were preserved; no branch was repeated.');}
    else if(p.prepared!==undefined&&p.prepared!==false||reserved)throw Error('Use the exact prepared branch identity before creating its child.');
    if(p.prepared===true&&process.platform==='linux'){
      const context=branchPublicationContext(source.file,this.loaded.get(source.id)?.events??this.events(source),p.messageSeq,p.mode);
      const m:Meta={reasoning:{...this.reasoningSettings(source)},memoryStartSeq:context.events.at(-1)?.seq??0,surface:source.surface,id:sid,cwd:source.cwd,file:context.name?join(this.dirs.sessions,sid,context.name):undefined,selection:{...source.selection},title:((p.mode==='edit'?'Edit · ':'Branch · ')+source.title).slice(0,200),saved:false,...permissionAtBoundary(source,p.messageSeq),updatedAt:Date.now(),requests:[],running:false,fork};
      const inherited=context.events.map(event=>event.type==='user/message'?{...event,data:{...event.data,source:{...event.data.source,sessionId:event.data.source?.sessionId??source.id}}}:event);
      let seq=inherited.at(-1)?.seq??0;if(p.mode==='reply')inherited.push({seq:++seq,type:'turn/end',data:{reason:{kind:'completed'}}});inherited.push({seq:++seq,type:'session/title',data:{title:m.title}});
      if(!Number.isSafeInteger(seq))throw Error('The branch display sequence is exhausted; originals preserved.');
      this.branchPublications.prepare(branchIntent(p),[...(context.name?[{kind:'native' as const,name:context.name,data:context.native!}]:[]),{kind:'events',name:'events.jsonl',data:inherited.map(e=>JSON.stringify(e)+'\n').join('')},{kind:'meta',name:'meta.json',data:JSON.stringify(m)+'\n'}]);
      const committed=this.branchPublications.finish(branchIntent(p)) as Meta;this.metadata.set(sid,committed);return this.branchRow(committed);
    }
    const directory=privateDir(join(this.dirs.sessions,sid));
    const context=branchContext(source.file,directory,this.loaded.get(source.id)?.events??this.events(source),p.messageSeq,p.mode);
    const m:Meta={reasoning:{...this.reasoningSettings(source)},memoryStartSeq:context.events.at(-1)?.seq??0,surface:source.surface,id:sid,cwd:source.cwd,file:context.file,selection:{...source.selection},title:((p.mode==='edit'?'Edit · ':'Branch · ')+source.title).slice(0,200),saved:false,...permissionAtBoundary(source,p.messageSeq),updatedAt:Date.now(),requests:[],running:false,fork};
    const inherited=context.events.map(event=>event.type==='user/message'?{...event,data:{...event.data,source:{...event.data.source,sessionId:event.data.source?.sessionId??source.id}}}:event);
    writeFileSync(join(this.dirs.sessions,sid+'.events.jsonl'),inherited.map(e=>JSON.stringify(e)+'\n').join(''),{mode:0o600});
    this.save(m);this.metadata.set(sid,m);
    if(p.mode==='reply')this.append(m,'turn/end',{reason:{kind:'completed'}});
    this.append(m,'session/title',{title:m.title});
    return this.branchRow(m);
  }
  branchRow(m:Meta){return {sessionId:m.id,cwd:m.cwd,agentPreset:m.surface==='browser'?'augmentor-browser-pi':'augmentor-linux-pi',title:m.title,saved:m.saved,running:m.running,selection:m.selection,fork:m.fork};}
  workspaceSnapshot(){const data=this.workspaces.snapshot(),organization=this.organization.snapshot();return {revision:data.revision,items:data.items.map(row=>({...row,sessionIds:[...this.metadata.values()].filter(m=>resolve(m.cwd)===row.cwd).map(m=>m.id)})),organizationRevision:organization.revision,pinnedSessionIds:organization.pinnedSessionIds,archivedSessionIds:organization.archivedSessionIds};}
  private organizationTarget(p:Data){const m=this.getMeta(p.sessionId);if(m.delegation)throw Error('Delegated conversations are controlled by their parent job.');if(!['pin','unpin','archive','restore'].includes(p.action)||p.stop!==undefined&&typeof p.stop!=='boolean'||p.stop===true&&p.action!=='archive')throw Error('Choose a supported conversation organization action.');this.organization.check(p.expectedRevision);if(p.action==='archive'&&this.voice.owns(m.id))throw Error('Close voice before archiving its conversation.');if(p.action==='archive'&&(this.jobs.problem||!this.mcpManagement.describe(m.id).available))throw Error('Work receipts are unavailable. Inspect them before archiving.');return m;}
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
  submit(r:Loaded,input:string,id:string){const permissionInput=permissionCommand(input);r.mcp?.assertReady();const m=r.meta;if(this.organization.archived(m.id))throw Error('Restore the conversation before starting work.');if(m.running)throw new Error('This conversation is already working');
    if(this.mcpReloading)throw Error('Finish MCP session reload before sending a chat prompt.');
    this.wikiReady(m);this.searchReady(m);
    if(m.surface!=='browser'&&this.mcpManagement.busy)throw Error('Finish or cancel MCP management before sending a Native chat prompt.');
    const reasoningPolicy=reasoningConfig(this.settings.reasoning),savedThinking=this.reasoningSettings(m);
    r.turnId=randomUUID();const queue=this.queue(m),goalSource=queue.read(id).goalSource;queue.dispatch(id,r.turnId);
    r.requestedMode=queue.read(id).inputMode??'text';r.humanInput=undefined;r.inputMode='unattributed';r.inputOrigin='unattributed';
    m.running=true;r.cancelled=false;r.failed=false;r.initialDelivered=false;r.preparingInput=false;r.interruptedInput=false;r.phase='preparing';r.activeRequestId=id;m.requests=[...m.requests.slice(-99),id];m.updatedAt=Date.now();this.save(m);this.append(m,'turn/start',{requestId:id});queue.accepted(id);
    r.observation?.beginTurn({clientRequestId:id});
    r.execution?.begin(r.manager);
    r.reasoning?.begin(reasoningPolicy,savedThinking,this.settings.revision);
    const modeInput=planCommand(input);
    if(!m.title&&!permissionInput&&(!modeInput||modeInput.message||queue.read(id).attachments?.length)){m.title=((modeInput?modeInput.message:input)||queue.read(id).attachments?.map(p=>p.attachment.name||'Attachment').join(', ')||'Attachment').replace(/\s+/g,' ').slice(0,80);r.session.setSessionName(m.title);this.append(m,'session/title',{title:m.title});this.save(m);}
    r.task=(async()=>{let failed=false,attempted=false,handled=false;try{
      await r.memory.activity('foreground');if(r.cancelled)return;
      const attachmentInput=await this.attachments.resolve(m.id,input,queue.read(id).attachments);if(r.cancelled)return;validateSteeringInput(r.session,input);r.phase='running';attempted=true;r.preparingInput=true;
      await r.session.prompt(attachmentInput.text,{images:attachmentInput.images,expandPromptTemplates:!goalSource,source:'rpc',preflightResult:disposition=>{
        r.preparingInput=false;
        if(r.cancelled)return;
        r.observation?.record('execution/input',{clientRequestId:id,disposition,expansion:'sdk-approved-skills-and-templates'});
        if(disposition==='handled'){
          handled=true;r.execution?.inputHandled();
          const mode=r.planMode.view(),isPlanCommand=modeInput&&!modeInput.message&&(mode.pending?!mode.active:mode.active)===modeInput.active;
          const message=permissionInput?'Permission mode: '+permissionSelection(m).currentValue+'.'+(permissionInput.preset===null?' Available: '+permissionOptions().map(row=>row.value).join(', ')+'.':'')+' Existing running work and job grants stay unchanged.':isPlanCommand?(modeInput.active?(mode.pending?'Entering plan mode at the next step.':'Plan mode on. Use /plan off to leave.'):(mode.pending?'Leaving plan mode at the next step.':'Plan mode off.')):'The input was handled by an input extension. No copy of that input was sent to the model.';
          this.append(m,'runtime/notice',{message,disposition:'input-handled',submittedContent:submittedParts(input,queue.read(id).attachments),source:{kind:'user',sessionId:m.id,rpcId:id},incomplete:false});
        }
      }});
    }catch(error){failed=true;this.append(m,'runtime/error',{message:String(error)});}finally{
      r.skillInputs.clear();r.phase='settling';
      try{r.goals.settle();}catch{r.goals.disarm();r.failed=true;this.append(m,'runtime/warning',{message:'Goal admission or pending pause could not be confirmed at settlement. Inspect its preserved original before resuming.'});}
      await r.memory.activity('stop');
      r.execution?.end(r.cancelled?'aborted':failed||r.failed||r.execution?.incomplete?'error':'completed');this.interactions.settleOwner(m.id);if(m.surface!=='browser'&&!this.jobs.busyKind('desktop',m.id))await desktopControl('stop','pi:'+m.id).catch(()=>{});const reason=r.cancelled?'aborted':failed||r.failed||r.execution?.incomplete?'error':'completed';
      // A terminal receipt is persisted before admitting another input. A crash
      // before this boundary produces an unknown receipt, never an automatic retry.
      const unknownInput=r.interruptedInput||attempted&&!r.initialDelivered&&!handled&&(r.cancelled||failed);r.preparingInput=false;
      queue.finish(id,unknownInput?'unconfirmed':reason==='aborted'?'cancelled':reason==='error'?'failed':'completed');if(reason!=='completed'||queue.uncertain)queue.pause();
      if(unknownInput)this.append(m,'runtime/notice',{message:'Input preparation stopped before model delivery. Its extension effects may be unknown; this prompt will not be replayed.',incomplete:true});
      if(r.goals.armed&&(reason!=='completed'||goalSource&&handled)){try{r.goals.fail(handled?'goal-input-handled':reason==='aborted'?'turn-interrupted':'turn-failed',handled?'A goal input was handled without model admission. Explicit human review is required.':'Work stopped or failed. Inspect its outcome before explicitly resuming the goal.');}catch{r.goals.disarm();}}
      if(m.file&&existsSync(m.file))delete m.planModeBootstrap;
      if(r.turnId)this.voice.finish(m.id,r.turnId,reason==='completed');
      m.running=false;m.updatedAt=Date.now();this.save(m);this.append(m,'turn/end',{reason:{kind:reason},requestId:id});r.observation?.record('turn/end',{reason,execution:r.execution?.describe()});r.turnId=undefined;r.activeRequestId=undefined;r.phase=undefined;r.humanInput=undefined;r.requestedMode=undefined;r.inputMode='unattributed';r.inputOrigin='unattributed';
      void this.flushJobReceipts(m.id).catch(()=>{});if(!m.delegation&&!queue.paused)this.pump(m);
    }})();return {accepted:true,turnId:r.turnId};
  }
  private wakeGoals(){for(const r of this.loaded.values())if(r.goals.armed&&!r.meta.running)void this.pump(r.meta);}
  private pump(m:Meta){
    if(this.pumping.has(m.id))return this.pumping.get(m.id)!;
    const run=this.serial.then(async()=>{
      const queue=this.queue(m);
      if(this.organization.archived(m.id)||this.quiescing||this.modelSettingsProblem||this.modelSettingsBusy||this.mcpReloading||this.improvements.busy||m.surface!=='browser'&&this.mcpManagement.busy||m.running||this.compactions.blocked(m.id)||queue.paused||queue.uncertain)return;
      let item=queue.next;
      if(!item){if(this.jobs.busyOwner(m.id))return;const owner=this.loaded.get(m.id);if(!owner?.goals.armed)return;try{const source=owner.goals.reserve();if(!source)return;const requestId='goal:'+randomUUID();queue.enqueue(requestId,owner.goals.prompt(source),true,source);item=queue.next;}catch{try{owner.goals.fail('goal-queue-failed','Goal input could not be queued. Inspect the queue before explicitly resuming.');}catch{owner.goals.disarm();}return;}}
      if(!item)return;
      let r:Loaded;
      try{r=await this.load(m);}catch(error){queue.notSent(item.id);this.append(m,'runtime/error',{message:'Queued prompt was not sent: '+String(error)});return;}
      if(this.organization.archived(m.id)||this.quiescing||this.modelSettingsProblem||this.modelSettingsBusy||this.mcpReloading||this.improvements.busy||m.surface!=='browser'&&this.mcpManagement.busy||m.running||this.compactions.blocked(m.id)||queue.paused||queue.uncertain||queue.next?.id!==item.id)return;
      this.submit(r,item.input!,item.id);
    });
    this.serial=run.catch(()=>{});this.pumping.set(m.id,run);
    void run.catch(error=>{this.queue(m).pause();console.warn('[augmentor-queue] Dispatch stopped:',String(error));}).finally(()=>this.pumping.delete(m.id));return run;
  }
  async dispatch(method:string,p:Data,id:string){
    if(this.quiescing&&method!=='host.describe')throw new Error('Runtime is closing for maintenance. No action was submitted.');
    if(['workspaceFiles.stat','workspaceFiles.read','workspaceFiles.readBytes'].includes(method)){try{const pRead=method==='workspaceFiles.readBytes'&&p.range===undefined?{...p,range:{offset:0,length:256*1024}}:p;return {ok:true,value:await this.previewFile(p.sessionId,method==='workspaceFiles.stat'?'stat':method==='workspaceFiles.read'?'read':'bytes',pRead)};}catch(error){const e=error as any;return {ok:false,error:{code:e.code??'gateway/internal',message:e.message,details:e.details??{}}};}}
    if(method==='session.fileReferences')return this.listFileReferences(p.sessionId,p.query);
    if(method==='models.accountStatus')return this.modelAccounts.describe(p.requestId);
    if(method==='models.accountRespond')return this.modelAccounts.respond(p.requestId,p.promptId,p.value);
    if(method==='models.accountCancel')return this.modelAccounts.cancel(p.requestId);
    if(method==='setup.test'){if(this.modelSettingsBusy)throw Error('Finish model account changes before testing another connection.');return this.setup.test(p);}
    if(method==='setup.cancel')return this.setup.cancel();
    if(method==='models.settingsDiscover')return this.discoverModels(p.request??{});
    // These synchronous policy reads/writes create no SDK owner and must not wait behind an approval-holding preparation.
    if(method==='session.permission')return this.permissionSnapshot(this.getMeta(p.sessionId),p.beforeRevision);
    if(method==='session.skills')return this.skillsSnapshot(this.getMeta(p.sessionId));
    if(method==='session.selectPermission')return this.selectPermission(p);
    if(method==='session.cancel')return this.cancel(p.sessionId);
    if(method==='voice.close'){const m=this.getMeta(p.sessionId);if(m.delegation)throw Error('Delegated conversations have no voice connection.');await this.voice.release(m.id);return {closed:true};}
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
    if(this.modelAccounts?.busy&&['session.setPlanMode','session.updateGoal','session.updateQueue','session.mcpConfigure','session.mcpAction','session.organize','session.trimTools','workspace.remove','workspace.move','reasoning.configure'].includes(method))throw Error('Finish or cancel account sign-in before changing shared model execution settings.');
    if((this.modelSettingsProblem||this.modelSettingsBusy)&&(['session.prompt','session.continueQueue','session.selectModel','session.selectReasoning','session.compact','session.create','session.branch','session.prepareBranch','session.startJob','session.setPlanMode','prompt.improve','setup.save'].includes(method)||method==='session.updateQueue'&&p.action?.kind==='steer'))throw Error('Refresh model settings to confirm the stored configuration before starting or changing work.');
    if(p.sessionId&&this.organization.archived(p.sessionId)&&(['session.prompt','session.continueQueue','session.startJob','session.setPlanMode','session.updateGoal','session.compact','prompt.improve','session.prepareBranch'].includes(method)||method==='session.branch'&&p.prepared===true))throw Error('Restore the conversation before starting work.');
    if(this.mcpReloading&&(['prompt.improve','setup.save','models.configure','models.reload','session.create','session.branch','session.prepareBranch','session.setPlanMode','session.updateGoal','session.trimTools','session.compact','session.selectModel','session.selectReasoning','reasoning.configure','session.prompt','session.continueQueue'].includes(method)||method==='session.updateQueue'&&p.action?.kind==='steer'))throw Error('Finish MCP session reload before changing or starting a conversation.');
    if(method.startsWith('session.')&&p.sessionId&&this.metadata.get(p.sessionId)?.delegation&&!['session.models','session.history','session.nativeHistory','session.nativeRead','session.originalSearch','session.originalRead','session.planMode','session.plan','session.goal','session.queue','session.compaction','session.cancel'].includes(method))throw Error('Delegated conversations are controlled by their parent job.');
    if(this.jobs.busy&&['models.configure','models.reload','setup.save','reasoning.configure','session.mcpConfigure','session.mcpAction'].includes(method))throw Error('Stop and settle background jobs before changing their shared configuration.');
    if(this.compactions.busy&&['setup.save','models.configure','models.reload','reasoning.configure','session.mcpConfigure','session.mcpAction','prompt.improve'].includes(method))throw Error('Finish or cancel Pi compaction before changing shared configuration.');
    if(p.sessionId&&this.compactions.blocked(p.sessionId)&&['session.create','session.branch','session.prepareBranch','session.trimTools','session.selectModel','session.selectReasoning','session.prompt','session.continueQueue','session.setPlanMode','session.updateGoal','session.startJob'].includes(method))throw Error('Finish compaction or inspect and acknowledge its unknown outcome before changing this conversation.');
    if(this.voice.active&&['models.configure','models.reload','setup.save','reasoning.configure','session.mcpConfigure','session.mcpAction'].includes(method))throw Error('Close voice before changing shared execution resources.');
    if(p.sessionId&&this.voice.owns(p.sessionId)&&['session.compact','session.trimTools'].includes(method))throw Error('Close voice before compacting or repairing its conversation.');
    switch(method){
    case 'models.settingsDescribe':{const view=await this.modelSettings.describe();return {...view,writable:!this.modelSettingsProblem,runtimeStatus:this.modelSettingsProblem?'needs-refresh':'confirmed',modelsRevision:this.modelsRevision};}
    case 'models.settingsMutate':return {...await this.modelSettings.mutate(p.ops,p.revision),modelsRevision:this.modelsRevision};
    case 'models.credentialDescribe':return this.modelSettings.credential(p.ref);
    case 'models.credentialSet':return {...await this.modelSettings.setCredential(p.ref,p.value,p.revision),modelsRevision:this.modelsRevision};
    case 'models.accountLogout':return {...await this.logoutModelAccount(p.provider,p.revision),modelsRevision:this.modelsRevision};
    case 'models.accountDescribe':return this.describeModelAccounts();
    case 'models.accountStart':return this.startModelAccount(p.provider,p.revision,p.requestId);
    case 'models.settingsDiscover':return this.discoverModels(p.request??{});
    case 'models.settingsRefresh':await this.reloadModelSettings();return {...await this.modelSettings.describe(),modelsRevision:this.modelsRevision};
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
    case 'session.family':{const m=this.getMeta(p.sessionId);return sessionFamily(m,this.jobs.list(m.id),sid=>this.metadata.get(sid),this.jobs.problem);}
    case 'session.jobs':{const m=this.getMeta(p.sessionId);return {available:!this.jobs.problem,reason:this.jobs.problem,items:this.jobs.list(m.id),scope:'exact-parent-conversation; reported producer outcomes; reads do not add usage'};}
    case 'session.job':{const m=this.getMeta(p.sessionId),job=this.jobs.lookup(m.id,identifier(p.jobId));return {job,output:this.jobs.output(m.id,job.id,p.from)};}
    case 'session.jobHistory':{const m=this.getMeta(p.sessionId),job=this.jobs.lookup(m.id,identifier(p.jobId));if(!job.childId)return {available:false,reason:'This job has no delegated conversation.'};const childId=this.jobInspectionTarget(m.id,job.id);return {available:true,childId,...this.history(this.getMeta(childId)).page(p.maxMessages,p.beforeSeq)};}
    case 'session.jobNativeHistory':case 'session.jobNativeRead':case 'session.jobObservations':case 'session.jobPayload':{
      const parent=this.getMeta(p.sessionId),job=this.jobs.lookup(parent.id,identifier(p.jobId));if(!job.childId)return {available:false,reason:'This job has no child native history.'};
      const childMethod=({ 'session.jobNativeHistory':'session.nativeHistory','session.jobNativeRead':'session.nativeRead','session.jobObservations':'observation.list','session.jobPayload':'observation.payload'} as Record<string,string>)[method]!;
      const childId=this.jobInspectionTarget(parent.id,job.id);return this.handle(childMethod,{...p,sessionId:childId},id);
    }
    case 'session.startJob':{
      const m=this.getMeta(p.sessionId),existing=this.jobs.existing(m.id,p.spec);
      // The exact owner/request fingerprint is a retained receipt, not a new
      // admission. Inspect it before constructing a cold parent or integrations.
      if(existing)return existing;
      await this.load(m);return this.startJob(m,p.spec);
    }
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
    case 'observation.describe':return {protocol:OBSERVATION_PROTOCOL,revision:this.settings.revision,capturePayloads:this.observations.policy().capturePayloads,retention:DEFAULT_RETENTION,boundary:'provider-payload-after-hooks',capabilities:{metadata:true,payloads:true,reasoningDecisions:true,indexedMetadata:true,metadataSearch:'retained metadata only; payload bodies excluded; bounded scan cursors',payloadSearch:'retained redacted JSON snapshots; authenticated resumable cursors; explicit missing coverage',payloadVerification:'optional expected sha256; verified captured source blocks',attachments:'inline-payloads-only',parsedProviderEvents:true,providerEventCoverage:'parsed events supplied by the provider; 8 MiB per request; partial coverage reported',contextBoundaries:PROVENANCE_VERSION,contextBoundaryCoverage:'public SDK transforms, converted context, provider hooks and managed memory; 8 MiB aggregate snapshot bodies; partial states reported',sourceProvenance:false,instructionSourceLinks:'captured before-agent options; bounded literal current-system text matches, not causal attribution',nativeEntryLineage:'public SDK projection matched to before-transform redacted JSON; ambiguous matches reported',historicalCoverage:'recorded-during-managed-operation'},telemetry:{installReporting:'disabled-by-host',analytics:'disabled-by-host',cacheWarming:'off-by-host',providerRetries:0,sessionRetries:'disabled-by-host',networkAudit:'synthetic-core-test; configured extensions and live services require separate review'}};
    case 'observation.configure':{if(p.expectedRevision!==this.settings.revision)throw new Error('Settings changed. Refresh inspection settings.');if(typeof p.capturePayloads!=='boolean')throw new Error('Choose whether to retain private request payloads.');this.settings.observation={capturePayloads:p.capturePayloads};this.persistSettings();return this.handle('observation.describe',{},id);}
    case 'observation.search':{const m=this.getMeta(p.sessionId);return this.observations.search(m.id,{query:p.query,scope:p.scope,cursor:p.cursor,limit:p.limit});}
    case 'observation.list':{const m=this.getMeta(p.sessionId);return this.observations.page(m.id,{beforeSeq:p.beforeSeq,afterSeq:p.afterSeq,limit:p.limit,query:p.query});}
    case 'observation.payload':{const m=this.getMeta(p.sessionId);return this.observations.payload(m.id,identifier(p.eventId),p.offset,p.limit,p.sha256);}
    case 'observation.clear':{const m=this.getMeta(p.sessionId);this.observations.clear(m.id);return {cleared:true,scope:'diagnostic records only'};}
    case 'voice.ticket':{
      const m=this.getMeta(p.sessionId);this.voiceAuthority(m,p.surface);
      if(this.voice.active)throw Error('Close the existing voice connection before opening another.');
      await this.load(m);this.voiceAuthority(m,p.surface);
      try{const ticket=await this.voice.ticket(m.id,p.surface);this.voiceAuthority(m,p.surface);return ticket;}
      catch(error){await this.voice.release(m.id);throw error;}
    }
    case 'host.describe':return {protocol:PROTOCOL,pid:process.pid,activeVoiceBridges:this.voice.active?1:0,activeUploads:this.uploads,activeSessionExports:this.sessionExports.active,activeFileReferences:this.referenceRequests,activeFilePreviews:this.previewReads,activeOfficePreviews:this.officePreview?.busy?1:0,activeHarnessRequests:this.harnessRequests,activeModelDiscoveries:this.modelSettings.activeDiscoveries,activeModelAccountLogins:this.modelAccounts?.busy?1:0,unsentHarnessDrafts:this.harnessDrafts.dirtyCount(),activeCompactions:this.compactions.busy?1:0,activeTurns:[...this.metadata.values()].filter(m=>m.running).length,version:RELEASE.version,piVersion:'1.1.0',workspace:process.env.AUGMENTOR_PI_WORKSPACE||process.cwd(),attachmentLimits:{...IMAGE_LIMITS,maxFileBytes:FILE_LIMIT},capabilities:{voiceBridge:true,sessionExport:!this.sessionExports.problem,skillReferences:true,sessionPermissions:true,permissionDefaults:true,searchSettings:process.platform==='linux',searchModes:process.platform==='linux',wikiSettings:process.platform==='linux',durableBranches:true,recoverableBranchPublication:process.platform==='linux',modelSettings:true,modelSettingsRevisions:true,modelDiscovery:true,modelAccountLogout:true,modelAccountLogin:true,shortcuts:true,appearancePreferences:true,metafolders:true,htmlPreviewSettings:true,manualCompaction:'public-sdk; native-boundary-receipts; cancel-and-no-replay',attachments:true,jobs:'durable-exact-owner; bounded-sdk-children-and-shell; no-replay; one-time-attribution',goals:'persistent-branch-state; explicit-human-arming; same-owner-continuation',plans:true,planMode:true,queue:true,steering:true,reasoning:true,promptImprovement:true,inspection:true,indexedDisplayHistory:true,indexedNativeHistory:true,managedMcp:'native-managed-profile; browser-unavailable; explicit-sdk-management',mcpManagement:true,mcpConfiguration:true,toolOriginals:'native-current-branch; MCP-and-nested; before-result-hooks; 63-MiB-JSON-limit',originalHistorySearch:'Pi selected ancestry/all saved entries and raw display originals',linuxTools:process.env.AUGMENTOR_PI_LINUX_TOOLS!=='0',desktopInput:desktopCapabilities().available,osCustomisation:false,localRouteEnforcement:false},promptInput:{source:'rpc',inputModes:{default:'text',voice:'explicit mode, canonical speech request id and live scoped lease at first admission; durable thereafter'},expandPromptTemplates:true,skills:'approved-session-resources',extensionCommands:'rejected-in-durable-queue; product /plan and /permission use admitted SDK input',disposition:'PromptOptions.preflightResult',stopDuringInput:'provider-blocked; await-handler-settlement; uncertain-receipt'},steering:{input:'sdk-public-input-and-approved-resources',sdkInputTransforms:true,inFlightTools:'settle',continuation:'same-AgentSession',identity:'owned-message-reference'},execution:{...EXECUTION_POLICY,providerRetries:0,sessionRetries:false,actionGuard:'automatic-recovery-and-steered-continuation',completion:'response-or-tool-handoff; task success requires verification'},toolBudget:{...TOOL_BUDGET,units:'unicode-code-points',originals:'native-current-branch',idleRepair:true},desktopSpecialist:{version:'augmentor-computer-use/1',available:desktopCapabilities().available,selectedModelOnly:true,requiresImageModel:true,maxConcurrent:1,evidence:'local-files',coreIntegration:false},desktopControl:desktopCapabilities(),configDir:this.dirs.config,stateDir:this.dirs.state};
    case 'host.prepareShutdown':
      if(this.voice.active)throw Error('Close voice before shutting down the runtime.');
      if(this.sessionExports.active)throw Error('Finish conversation downloads or wait for their one-minute links to expire before shutting down the runtime.');
      if(this.modelAccounts?.busy)throw Error('Cancel and settle account sign-in before shutting down the runtime.');
      if(this.compactions.busy)throw Error('Stop and settle Pi compaction before shutting down the runtime.');
      if(this.uploads)throw Error('Finish file uploads before shutting down the runtime.');
      if(this.previewReads)throw Error('Finish file-preview reads before shutting down the runtime.');
      if(this.officePreview?.busy)throw Error('Finish Office-preview conversion and cleanup before shutting down the runtime.');
      if(this.referenceRequests)throw Error('Finish file-reference lookups before shutting down the runtime.');
      if(this.harnessDrafts.dirtyCount())throw Error('Send or clear unsent Harness drafts before shutting down the runtime.');
      if(this.jobs.busy)throw Error('Stop and settle background jobs before shutting down the runtime');
      if(this.improvements.busy)throw Error('Finish or cancel prompt improvement before shutting down the runtime');
      if([...this.metadata.values()].some(m=>m.running))throw new Error('Stop active Pi tasks before shutting down the runtime');
      if(this.harnessRequests)throw Error('Finish Harness requests before shutting down the runtime.');
      this.quiescing=true;this.setup.cancel();return {accepted:true};
    case 'draft.describe':{this.getMeta(p.sessionId);return this.harnessDrafts.describe(p.sessionId);}
    case 'draft.text':{this.draftAuthority(p.sessionId);return this.harnessDrafts.setText(p.sessionId,p.expectedTextRevision,p.text,p.references);}
    case 'draft.remove':{this.draftAuthority(p.sessionId);return this.harnessDrafts.remove(p.sessionId,p.expectedAttachmentsRevision,p.attachmentId);}
    case 'draft.prepare':{this.draftAuthority(p.sessionId);if(!Array.isArray(p.content)||p.content.some((part:Data)=>part.type!=='text'&&!part.attachment))throw Error('Prepare only already-uploaded draft parts.');const parts=await this.attachments.admit(p.sessionId,p.content);if(parts.input!==this.harnessDrafts.describe(p.sessionId).text)throw Error('The submitted text differs from the saved draft.');return this.harnessDrafts.prepare(p.sessionId,p.expectedRevision,p.requestId,p.mode,parts.attachments);}
    case 'draft.settle':{this.draftAuthority(p.sessionId);const m=this.getMeta(p.sessionId),submission=this.harnessDrafts.describe(m.id).submission;if(!submission||submission.requestId!==p.requestId)throw Error('The saved submission identity differs.');const receipt=this.queue(m).lookup(p.requestId,submission.text,submission.attachments);if(!receipt||receipt.status==='unconfirmed'||receipt.status==='failed'&&receipt.input!==undefined)throw Error('The Pi queue has no accepted prompt with this identity; the draft is preserved.');return this.harnessDrafts.settle(m.id,p.requestId,true);}
    case 'draft.acknowledge':{this.draftAuthority(p.sessionId);if(p.acknowledgeUnknownOutcome!==true)throw Error('Acknowledge the uncertain draft without retrying.');return this.harnessDrafts.settle(p.sessionId,p.requestId,false);}
    case 'session.prepareBranch':return this.prepareBranch(p);
    case 'session.settleBranch':return this.settleBranch(p);
    case 'session.branchRecovery':{this.getMeta(p.sessionId);return {items:this.branchIntents.list(identifier(p.sessionId))};}
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
    case 'models.configure':if(this.improvements.busy)throw Error('Finish or cancel prompt improvement before changing providers');await this.modelSettings.configure(p.config);return this.catalog();
    case 'models.reload':if(this.improvements.busy)throw Error('Finish or cancel prompt improvement before reloading models');await this.reloadModelSettings();return this.catalog();
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
    case 'session.setPlanMode':{
      const m=this.getMeta(p.sessionId);if(m.surface!=='browser'&&this.mcpManagement.busy)throw Error('Finish or cancel MCP management before changing plan mode.');
      const r=await this.load(m);return r.planMode.select(p.active,p.expectedRevision);
    }
    case 'session.planMode':{
      const m=this.getMeta(p.sessionId);try{const loaded=this.loaded.get(m.id);if(loaded)return loaded.planMode.view();
      if(!m.file||!existsSync(m.file))return {...planModeProjection(m.planModeBootstrap?{type:'custom',data:m.planModeBootstrap}:undefined),persistence:m.planModeBootstrap?'pre-conversation-metadata':'no-saved-native-mode'};
      let native=this.nativeHistories.get(m.id);if(!native||native.source!==m.file){native=new NativeHistory(m.file,join(this.dirs.state,'native-index',m.id));if(this.nativeHistories.size>=32)this.nativeHistories.delete(this.nativeHistories.keys().next().value!);this.nativeHistories.set(m.id,native);}
      const saved=native.latestCustom(PLAN_MODE_TYPE);if(!saved.available)return saved;
      return {...planModeProjection(saved.entry??undefined),persistence:'saved-native-entry',coverage:saved.coverage};
      }catch{return {available:false,reason:'The latest plan-mode record is invalid or unavailable; inspect its preserved native original.'};}
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
      const inputMode=promptInputMode(p.inputMode);if(inputMode==='voice'&&!spokenRequestId(requestId))throw Error('Spoken input requires its stable speech request identity.');
      if(p.mode!==undefined&&!['queue','steer'].includes(p.mode))throw Error('Choose queue or steer mode.');
      const hasImages=Array.isArray(p.content)&&p.content.some((part:Data)=>part.type==='image');if(hasImages&&!(await this.selected(m.selection)).input.includes('image'))throw Error('The selected model does not support image input.');
      const {input,attachments}=await this.attachments.admit(m.id,p.content),queue=this.queue(m);
      if(permissionCommand(input)&&attachments.length)throw Error('Attachments cannot accompany /permission.');
      if(planCommand(input)?.active===false&&attachments.length)throw Error('Attachments cannot accompany /plan off.');
      const existing=queue.lookup(requestId,input,attachments,inputMode);if(existing)return {accepted:true,duplicate:true,requestId};
      if(m.requests.includes(requestId)){if(inputMode==='voice')throw Error('This legacy request has no verified spoken-input receipt. Inspect its history; nothing was replayed.');return {accepted:true,duplicate:true,requestId};}
      if(inputMode==='voice'&&(!this.voice.acceptsSpokenInput(m.id)||!this.connected(m.id)))throw Error('Reconnect the scoped voice bridge before submitting spoken input.');
      if(m.surface!=='browser'&&this.mcpManagement.busy)throw Error('Finish or cancel MCP management before sending a Native chat prompt.');
      this.loaded.get(m.id)?.mcp?.assertReady();
      if(p.mode==='steer'){
        const r=this.loaded.get(m.id);if(!m.running||!r||r.cancelled||r.phase==='settling'||r.turnId!==p.expectedTurnId||queue.paused||queue.uncertain||r.steering?.waiting)throw Error('The observed steering turn is no longer available.');
        r.steering!.validate(input);queue.enqueue(requestId,input,true,undefined,attachments,inputMode);return new SteeringReply(this.steer(m,requestId,p.expectedTurnId).then(result=>({...result,requestId})));
      }
      if(p.mode===undefined&&m.running)throw Error('This conversation is already working; use queue mode to add a waiting prompt.');
      if(p.resumeQueue!==undefined&&typeof p.resumeQueue!=='boolean')throw Error('Choose whether to resume the queue.');
      if(queue.uncertain)throw Error('A previous prompt has an unknown outcome. Inspect its history and explicitly acknowledge the interrupted receipt before sending more.');
      // Templates/skills use Session.prompt's SDK expansion, while registered
      // commands cannot bypass the persistent queue's admission/receipt rules.
      if(input.startsWith('/'))validateSteeringInput((await this.load(m)).session,input);
      if(this.mcpReloading||m.surface!=='browser'&&this.mcpManagement.busy)throw Error('Finish MCP management or session reload before admitting another prompt.');
      queue.enqueue(requestId,input,m.running||queue.paused||!!queue.next,undefined,attachments,inputMode);
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
    case 'shortcuts.describe':return {...await this.shortcutPreferences.describe(p.platform,p.definitions),settingsRevision:this.shortcutSettingsRevision};
    case 'shortcuts.edit':{const value=await this.shortcutPreferences.edit(p.platform,p.edit,p.revision);return {...value,snapshot:{...value.snapshot,settingsRevision:this.shortcutSettingsRevision}};}
    case 'wiki.receipts':return this.wikiReceipts();
    case 'wiki.review':{this.wikiGuard();const profile=this.wikiPreferences.describe();if(profile.revision!==p.expectedProfileRevision||!profile.value.vaultPath)throw Error('The stored Wiki vault changed. Refresh its receipt inspection before reviewing.');new WikiReceipts(this.dirs.state,profile.value.vaultPath).review(p as any);return this.wikiReceipts();}
    case 'wiki.describe':return this.wikiSnapshot();
    case 'wiki.set':{this.wikiGuard();this.wikiPreferences.set(p.value,p.expectedRevision,()=>{this.wikiFailed=true;});return this.applyWiki();}
    case 'wiki.refresh':return this.applyWiki();
    case 'search.describe':return this.searchSnapshot();
    case 'search.set':{this.searchGuard();const before=this.searchSnapshot();if(before.pending)throw Error('Apply stored Search settings before editing them.');const profile=this.searchPreferences.set(p.edit,p.expectedRevision,()=>{if(p.edit?.field==='enabled'&&p.edit.value!==before.enabled||p.edit?.field==='mode'&&before.enabled&&p.edit.value!==before.mode)this.searchFailed=true;});return profile.enabled!==before.enabled||profile.enabled&&profile.mode!==before.mode?this.applySearch():this.searchSnapshot();}
    case 'search.refresh':return this.applySearch();
    case 'metafolders.describe':{const value=this.metafolders.describe();this.metafoldersRevision=value.revision;return value;}
    case 'metafolders.set':{const value=this.metafolders.set(p.value,p.expectedRevision);this.metafoldersRevision=value.revision;return value;}
    case 'appearance.describe':{const value=this.appearance.describe();this.appearanceRevision=value.revision;return value;}
    case 'appearance.set':{const value=this.appearance.set(p.preference,p.expectedRevision);this.appearanceRevision=value.revision;return value;}
    case 'settings.describe':if(p.ns==='permission')return {namespaces:[this.permissionDefaultSnapshot()]};if(p.ns==='ui-settings')return {namespaces:[this.developerToolsSnapshot()]};if(p.ns==='dsh-context')return {namespaces:[this.contextPreferenceSnapshot()]};return {namespaces:[this.permissionDefaultSnapshot(),{ns:'prompt-library',revision:this.settings.revision,value:await promptCall('prompts.list')},this.contextPreferenceSnapshot()]};
    case 'settings.mutate':{
      if(p.expectedRevision!==this.settings.revision)throw new Error('Settings changed. Reopen the dialog.');
      if(p.ns==='ui-settings'){const enabled=developerToolsChange(p.ops),next={...this.settings,revision:this.settings.revision+1,developerTools:{enabled}};atomicJson(join(this.dirs.config,'settings.json'),next);this.settings=next;return this.developerToolsSnapshot();}
      if(p.ns==='dsh-context'){const change=contextPreferenceChange(p.ops);const next={...this.settings,revision:this.settings.revision+1,contextPreferences:{...contextPreferences(this.settings.contextPreferences),[change.field]:change.value}};atomicJson(join(this.dirs.config,'settings.json'),next);this.settings=next;return this.contextPreferenceSnapshot();}
      if(p.ns!=='permission')throw Error('Unsupported settings namespace.');const op=p.ops?.[0];if(!Array.isArray(p.ops)||p.ops.length!==1||op.op!=='set'||op.path?.join('.')!=='defaultPreset'||!['read-only','workspace-write','danger-full-access'].includes(op.value))throw new Error('Unsupported settings change');const next={...this.settings,revision:this.settings.revision+1,defaultPreset:op.value};atomicJson(join(this.dirs.config,'settings.json'),next);this.settings=next;return {ok:true};}
    case 'prompts.list':case 'prompts.save':case 'prompts.delete':return promptCall(method,p,id);
    case 'prompts.improvementSave':return promptCall('prompts.improvement.save',p,id);
    default:throw new Error('Unsupported method: '+method);
  }}
  async close(){this.quiescing=true;await this.voice.close();await this.sessionExports.close().catch(()=>console.warn('[augmentor-export] Private archive cleanup could not be verified; preserved scratch requires inspection.'));await this.modelAccounts.close();this.modelSettings.cancelDiscoveries();await this.officePreview?.close();this.fileReferences.close();this.setup.cancel();await this.jobs.close();await this.improvements.close();for(const m of this.metadata.values())if(this.compactions.busySession(m.id)){this.compactions.cancelSession(m.id);await this.compactions.waitSession(m.id);}for(const r of this.loaded.values()){await this.cancel(r.meta.id,'runtime-shutdown');await r.task;await r.session.extensionRunner.emit({type:'session_shutdown',reason:'quit'});r.memory.close();await r.memory.flush();r.observation?.record('session/close',{source:'runtime-shutdown'});r.observation?.dispose();r.planMode.dispose();r.reasoning?.dispose();r.steering?.dispose();r.execution?.dispose();r.session.dispose();}await this.mcpManagement.settled();}
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
