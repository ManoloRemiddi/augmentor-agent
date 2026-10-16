// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createServer, type IncomingMessage, type ServerResponse} from 'node:http';
import {randomBytes, timingSafeEqual} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {Readable} from 'node:stream';
import {pipeline} from 'node:stream/promises';
import {MAX_FRAME, identifier, request, type Data} from '../../protocol/src/index.js';
import {FILE_LIMIT} from './attachments.js';
import {PreviewReadError} from './file-preview.js';
import type {Host} from './host.js';

const allowed = new Set([
  'session.fileReferences','workspaceFiles.stat','workspaceFiles.read','workspaceFiles.readBytes',
  'draft.describe','draft.text','draft.remove','draft.prepare','draft.settle','draft.acknowledge',
  'host.describe', 'session.organize', 'workspace.list', 'workspace.adopt', 'workspace.rename', 'workspace.remove', 'workspace.move', 'workspace.listDirectory', 'workspace.createDirectory', 'models.list', 'models.validate', 'setup.test', 'setup.cancel', 'setup.save',
  'session.jobInspection', 'session.family', 'session.jobs', 'session.job', 'session.jobHistory', 'session.jobNativeHistory', 'session.jobNativeRead', 'session.jobObservations', 'session.jobPayload', 'session.startJob', 'session.cancelJob', 'session.removeJob', 'session.waitJob', 'session.list', 'session.create', 'session.setPlanMode', 'session.updateGoal', 'session.history', 'session.nativeHistory', 'session.nativeRead', 'session.goal', 'session.skills','session.permission','session.selectPermission','session.planMode', 'session.plan', 'session.originalSearch', 'session.originalRead', 'session.mcpInfo', 'session.mcpProfile', 'session.mcpConfigure', 'session.mcpAction', 'session.mcpActionStatus', 'session.mcpCancelAction', 'session.mcpSubmitRedirect', 'session.models', 'session.selectModel',
  'session.reasoning', 'session.selectReasoning', 'reasoning.describe', 'reasoning.configure',
  'prompt.improve', 'prompt.cancelImprovement', 'prompt.improvementStatus',
  'session.prompt', 'session.cancel', 'session.prepareBranch', 'session.settleBranch', 'session.branchRecovery', 'session.branch', 'session.rename', 'session.trimTools', 'chats.saved',
  'session.queue', 'session.updateQueue', 'session.continueQueue', 'session.resolveQueue', 'session.compact', 'session.compaction', 'session.acknowledgeCompaction',
  'observation.describe', 'observation.configure', 'observation.list', 'observation.search', 'observation.payload', 'observation.clear',
  'search.describe','search.set','search.refresh','wiki.describe','wiki.set','wiki.refresh','wiki.receipts','wiki.review','metafolders.describe','metafolders.set','appearance.describe','appearance.set','shortcuts.describe', 'shortcuts.edit', 'settings.describe', 'settings.mutate', 'prompts.list', 'prompts.save', 'prompts.delete', 'prompts.improvementSave', 'interaction.respond', 'interaction.wait',
  'models.settingsDescribe','models.settingsMutate','models.settingsDiscover','models.credentialDescribe','models.credentialSet','models.settingsRefresh','models.accountLogout',
  'models.accountDescribe','models.accountStart','models.accountStatus','models.accountRespond','models.accountCancel',
]);
interface Watch {sessionId: string; seen: number; interactive:boolean}
type Access={mode:'operator';token:string}|{mode:'read-only';token:string;sessionId:string;expiresAt:number};
const inspectionReads=new Set(['session.jobInspection','session.family','session.jobs','session.job','session.jobHistory', 'session.jobNativeHistory', 'session.jobNativeRead', 'session.jobObservations', 'session.jobPayload','host.describe','models.list','session.list','session.history','session.nativeHistory','session.nativeRead', 'session.goal', 'session.permission','session.planMode', 'session.plan', 'session.originalSearch', 'session.originalRead','session.mcpInfo','session.models','session.queue','session.compaction','observation.describe','observation.list', 'observation.search','observation.payload']);
interface LiveFrame {seq: number; sessionId: string; frame: Data}
const LIVE_BYTES = 16 * 1024 * 1024;

/** A local client of the existing Host. It never creates a second session owner. */
export class HarnessServer {
  readonly token = randomBytes(32).toString('hex');
  readonly watches = new Map<string, Watch>();
  private frames: (LiveFrame & {bytes: number})[] = [];
  private frameBytes = 0;
  private evicted = new Map<string, number>();
  private sequence = 0;
  private base = '';
  private inspections=new Map<string,Extract<Access,{mode:'read-only'}>>();
  private server = createServer((req, res) => void this.handle(req, res));
  constructor(readonly host: Host, readonly assets = fileURLToPath(new URL('../../../apps/harness/', import.meta.url))) {}
  async start(port = 0) {
    if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error('Invalid Harness port');
    await new Promise<void>((resolve, reject) => {
      this.server.once('error', reject);
      this.server.listen(port, '127.0.0.1', () => {this.server.off('error', reject); resolve();});
    });
    const address = this.server.address();
    if (!address || typeof address === 'string') throw new Error('Harness has no loopback listener');
    this.base = 'http://127.0.0.1:' + address.port;
    return {url: this.base + '/#token=' + this.token, origin: this.base};
  }
  connected(sessionId: string) {
    const now = Date.now();
    for (const [clientId, watch] of this.watches) {
      if (now - watch.seen > 15000) this.watches.delete(clientId);
    }
    return [...this.watches.values()].some(watch => watch.sessionId === sessionId&&watch.interactive);
  }
  openInspection(sessionId:string,through?:number){
    this.host.getMeta(sessionId);
    for(const [token,scope] of this.inspections)if(scope.expiresAt<=Date.now())this.inspections.delete(token);
    if(!this.base)throw Error('The conversation inspector is not available.');
    if(this.inspections.size>=128)throw Error('Too many active inspector links. Wait for a link to expire or restart the Pi runtime while idle.');
    const token=randomBytes(32).toString('hex'),expiresAt=Math.min(Date.now()+4*60*60*1000,through??Infinity);
    if(!Number.isFinite(expiresAt)||expiresAt<=Date.now())throw Error('The parent inspector has expired. Open a fresh parent link.');
    this.inspections.set(token,{mode:'read-only',token,sessionId,expiresAt});
    return {url:this.base+'/#token='+token+'&session='+encodeURIComponent(sessionId)+'&view=trajectory',origin:this.base,sessionId,mode:'read-only',expiresAt};
  }
  publish(sessionId: string, frame: Data) {
    const item = {seq: ++this.sequence, sessionId, frame, bytes: Buffer.byteLength(JSON.stringify(frame)) + 256};
    if (item.bytes > MAX_FRAME - 4096) {this.evicted.set(sessionId, item.seq); return;}
    this.frames.push(item); this.frameBytes += item.bytes;
    while (this.frames.length > 4096 || this.frameBytes > LIVE_BYTES) {
      const removed = this.frames.shift()!; this.frameBytes -= removed.bytes;
      this.evicted.set(removed.sessionId, Math.max(this.evicted.get(removed.sessionId) ?? 0, removed.seq));
    }
  }
  private access(req: IncomingMessage):Access|null {
    const value = req.headers.authorization;
    if (!value?.startsWith('Bearer ')) return null;
    const supplied = Buffer.from(value.slice(7)), expected = Buffer.from(this.token);
    if(supplied.length === expected.length && timingSafeEqual(supplied, expected))return {mode:'operator',token:this.token};
    const scope=this.inspections.get(value.slice(7));
    if(scope&&scope.expiresAt>Date.now())return scope;
    if(scope)this.inspections.delete(scope.token);
    return null;
  }
  private watchKey(access:Access,clientId:string){return access.mode==='operator'?clientId:access.token+':'+clientId;}
  private scopedSession(access:Access,sessionId:unknown){if(access.mode==='read-only'&&sessionId!==access.sessionId)throw Error('This inspector can read only its selected conversation.');}
  private async inspect(access:Extract<Access,{mode:'read-only'}>,method:string,params:Data,id:string){
    if(!inspectionReads.has(method))throw Error('This conversation inspector is read-only.');
    if(method.startsWith('session.')&&method!=='session.list'||method.startsWith('observation.')&&method!=='observation.describe')this.scopedSession(access,params.sessionId);
    if(method==='session.jobInspection')return this.openInspection(this.host.jobInspectionTarget(params.sessionId,params.jobId),access.expiresAt);
    const result=await this.host.dispatch(method,params,id),meta=this.host.getMeta(access.sessionId);
    if(method==='session.list')return {items:meta.delegation?[this.host.inspectionSessionRow(access.sessionId)]:result.items.filter((row:Data)=>row.sessionId===access.sessionId)};
    if(method==='host.describe')return {protocol:result.protocol,version:result.version,piVersion:result.piVersion,workspace:meta.cwd,capabilities:{inspection:true,...(result.capabilities?.sessionPermissions?{sessionPermissions:true}:{})}};
    if(method==='session.permission')return {...result,canSelect:false};
    if(method==='models.list')return {groups:result.groups.map((group:Data)=>({provider:group.provider,name:group.name,models:group.models.filter((model:Data)=>model.provider===meta.selection.provider&&model.model===meta.selection.model)})).filter((group:Data)=>group.models.length),default:meta.selection,pinned:[],hidden:[],failures:[]};
    return result;
  }
  private send(res: ServerResponse, status: number, value: unknown) {
    const raw = JSON.stringify(value);
    if (Buffer.byteLength(raw) > MAX_FRAME) throw new Error('Response exceeds the connection limit; request a smaller page');
    res.writeHead(status, {'Content-Type': 'application/json; charset=utf-8'});
    res.end(raw);
  }
  private async body(req: IncomingMessage) {
    let size = 0; const chunks: Buffer[] = [];
    for await (const chunk of req) {
      size += chunk.length;
      if (size > MAX_FRAME) throw new Error('Request exceeds the local connection limit');
      chunks.push(Buffer.from(chunk));
    }
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
  }
  private async handle(req: IncomingMessage, res: ServerResponse) {
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Referrer-Policy', 'no-referrer');
    res.setHeader('Cross-Origin-Resource-Policy', 'same-origin');
    res.setHeader('X-DNS-Prefetch-Control','off');
    res.setHeader('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self' data:; connect-src 'self'; img-src 'self' data: blob:; frame-src 'self'; base-uri 'none'; frame-ancestors 'none'");
    try {
      if (!this.base || req.headers.host !== new URL(this.base).host ||
        (req.headers.origin !== undefined && req.headers.origin !== this.base)) {
        this.send(res, 403, {error: {message: 'This client origin is not authorized'}}); return;
      }
      const url = new URL(req.url ?? '/', this.base);
      if (url.origin !== this.base) {this.send(res, 403, {error: {message: 'Invalid request origin'}}); return;}
      if(url.pathname.startsWith('/api/session.export/')){
        if(req.method!=='GET'||url.search||!/^\/api\/session\.export\/[a-f0-9]{64}$/.test(url.pathname))throw Error('Use an exact one-use conversation download link.');
        const abort=new AbortController(),cancel=()=>{if(!res.writableFinished)abort.abort(Error('Conversation download disconnected.'));};req.once('aborted',cancel);res.once('close',cancel);
        try{await this.host.receiveHarnessRequest(()=>this.host.sessionExports.download(url.pathname.slice('/api/session.export/'.length),abort.signal,async(stream,filename,signal)=>{
          res.writeHead(200,{'Content-Type':'application/zip','Content-Disposition':'attachment; filename="'+filename+'"'});
          await pipeline(Readable.fromWeb(stream as import('node:stream/web').ReadableStream<Uint8Array>),res,{signal});
        }));}finally{req.removeListener('aborted',cancel);res.removeListener('close',cancel);}return;
      }
      if (url.pathname.startsWith('/api/')) {
        const access=this.access(req);
        if (!access) {this.send(res, 401, {error: {message: 'Open a fresh private Harness link to connect'}}); return;}
        if(url.pathname==='/api/session.export'){
          if(req.method!=='HEAD'||access.mode!=='operator')throw Error('Only an operator can prepare a conversation download.');
          if(url.searchParams.get('includeDescendants')!=='true'||[...url.searchParams.keys()].some(key=>!['sessionId','includeDescendants'].includes(key))||url.searchParams.getAll('sessionId').length!==1||url.searchParams.getAll('includeDescendants').length!==1)throw Error('Choose an exact conversation export including verified descendants.');
          const sid=identifier(url.searchParams.get('sessionId')),abort=new AbortController(),cancel=()=>{if(!res.writableFinished)abort.abort(Error('Conversation export preparation disconnected.'));};req.once('aborted',cancel);res.once('close',cancel);
          try{const grant=await this.host.receiveHarnessRequest(()=>this.host.sessionExports.prepare(sid,abort.signal));
            if(abort.signal.aborted||res.destroyed){await this.host.sessionExports.revoke(grant.url);return;}res.writeHead(200,{'X-Augmentor-Download':grant.url,'X-Augmentor-Download-Expires':String(grant.expiresAt)});res.end();
          }finally{req.removeListener('aborted',cancel);res.removeListener('close',cancel);}return;
        }
        if(req.method==='GET'&&url.pathname==='/api/access'){this.send(res,200,{mode:access.mode,...(access.mode==='read-only'?{sessionId:access.sessionId,expiresAt:access.expiresAt}:{})});return;}
        if(url.pathname.startsWith('/api/dictation/')){
          if(access.mode!=='operator'||req.method!=='POST')throw Error('Draft dictation requires operator authority.');
          const action=url.pathname.slice('/api/dictation/'.length);
          if(!['catalog','open','heartbeat','transcribe','close'].includes(action))throw Error('Unknown dictation operation.');
          const abort=new AbortController(),cancel=()=>{if(!res.writableFinished)abort.abort(Error('Dictation request disconnected.'));};req.once('aborted',cancel);res.once('close',cancel);
          try{const result=await this.host.receiveHarnessRequest(async()=>{
            if(action==='transcribe'){
              if([...url.searchParams.keys()].some(key=>!['clientId','captureId'].includes(key))||url.searchParams.getAll('clientId').length!==1||url.searchParams.getAll('captureId').length!==1)throw Error('Supply exact dictation identities.');
              if(req.headers['content-type']!=='audio/wav'||Number(req.headers['content-length']??0)>19200044)throw Error('Supply a bounded WAV recording.');
              return this.host.dictation.transcribe(url.searchParams.get('clientId')!,url.searchParams.get('captureId')!,async signal=>{
                const stop=()=>req.destroy();signal.addEventListener('abort',stop,{once:true});
                try{signal.throwIfAborted();let size=0;const chunks:Buffer[]=[];for await(const chunk of req){size+=chunk.length;if(size>19200044)throw Error('Recording exceeds the ten-minute limit.');chunks.push(Buffer.from(chunk));}signal.throwIfAborted();return Buffer.concat(chunks);}finally{signal.removeEventListener('abort',stop);}
              },abort.signal);
            }
            if(url.search)throw Error('Use the dictation request body.');
            const p=await this.body(req);if(!p||typeof p!=='object'||Array.isArray(p))throw Error('Supply a dictation request.');
            const keys=action==='catalog'?['refresh']:action==='open'?['clientId','captureId','sessionId']:['clientId','captureId'];
            if(Object.keys(p).some(key=>!keys.includes(key)))throw Error('Unexpected dictation parameters.');
            if(action==='catalog'){if(p.refresh!==undefined&&typeof p.refresh!=='boolean')throw Error('Choose an explicit refresh.');return this.host.dictation.catalog(abort.signal,p.refresh===true);}
            if(typeof p.clientId!=='string'||typeof p.captureId!=='string'||p.sessionId!==undefined&&typeof p.sessionId!=='string')throw Error('Supply exact dictation identities.');
            if(action==='open')return this.host.dictation.open(p.clientId,p.captureId,p.sessionId,abort.signal);
            if(action==='heartbeat')return this.host.dictation.heartbeat(p.clientId,p.captureId);
            return this.host.dictation.closeCapture(p.clientId,p.captureId);
          });this.send(res,200,result);}finally{req.removeListener('aborted',cancel);res.removeListener('close',cancel);}return;
        }
        if(req.method==='GET'&&url.pathname==='/api/appearance/revision'){
          if(access.mode!=='operator')throw Error('Appearance profile revisions require operator authority.');
          this.send(res,200,{appearanceRevision:this.host.appearanceRevision,metafoldersRevision:this.host.metafoldersRevision,modelsRevision:this.host.modelsRevision});return;
        }
        if(req.method==='POST'&&url.pathname==='/api/drafts/attachment'){
          if(access.mode!=='operator')throw Error('This conversation inspector cannot read or edit unsent drafts.');
          const sid=identifier(url.searchParams.get('sessionId')),rawRevision=url.searchParams.get('expectedAttachmentsRevision');if(!rawRevision||! /^(0|[1-9][0-9]{0,15})$/.test(rawRevision)||url.searchParams.get('lastModified')===null)throw Error('Supply an exact draft attachment revision and file timestamp.');const expected=Number(rawRevision);
          if(Number(req.headers['content-length']??0)>FILE_LIMIT)throw Error('File exceeds the twenty MiB limit.');
          const input={id:identifier(url.searchParams.get('id')),name:url.searchParams.get('name'),kind:url.searchParams.get('kind'),mediaType:url.searchParams.get('mediaType')??'',lastModified:Number(url.searchParams.get('lastModified'))};
          const result=await this.host.receiveDraftAttachment(sid,async()=>{let bytes=0;const chunks:Buffer[]=[];for await(const chunk of req){bytes+=chunk.length;if(bytes>FILE_LIMIT)throw Error('File exceeds the twenty MiB limit.');chunks.push(Buffer.from(chunk));}return Buffer.concat(chunks);},expected,input);
          this.send(res,200,result);return;
        }
        if(req.method==='GET'&&url.pathname==='/api/drafts/file'){
          if(access.mode!=='operator')throw Error('This conversation inspector cannot read or edit unsent drafts.');
          const stored=this.host.draftAttachmentBytes(identifier(url.searchParams.get('sessionId')),identifier(url.searchParams.get('id')),url.searchParams.get('sha256'));
          res.writeHead(200,{'Content-Type':'application/octet-stream','Content-Length':stored.data.byteLength});res.end(stored.data);return;
        }
        if(req.method==='POST'&&url.pathname==='/api/attachments/upload'){
          if(access.mode!=='operator')throw Error('This conversation inspector is read-only.');
          const sid=identifier(url.searchParams.get('sessionId'));this.host.getMeta(sid);
          const announced=Number(req.headers['content-length']??0);if(announced>FILE_LIMIT)throw Error('File exceeds the twenty MiB limit.');
          const result=await this.host.receiveAttachmentUpload(sid,async()=>{
            let bytes=0;const chunks:Buffer[]=[];for await(const chunk of req){bytes+=chunk.length;if(bytes>FILE_LIMIT)throw Error('File exceeds the twenty MiB limit.');chunks.push(Buffer.from(chunk));}
            return Buffer.concat(chunks);
          },url.searchParams.get('name')??'attachment',url.searchParams.get('mediaType')??undefined);
          this.send(res,200,result);return;
        }
        if(req.method==='GET'&&url.pathname==='/api/attachments/image'){
          const sid=identifier(url.searchParams.get('sessionId'));this.scopedSession(access,sid);
          const ref=JSON.parse(url.searchParams.get('ref')??'null'),stored=await this.host.attachmentImage(sid,ref);
          res.writeHead(200,{'Content-Type':stored.ref.mediaType,'Content-Length':stored.data.byteLength});res.end(stored.data);return;
        }
        if (req.method === 'GET' && url.pathname === '/api/events') {
          const sessionId = identifier(url.searchParams.get('sessionId'));
          const clientId = identifier(url.searchParams.get('clientId'));
          this.scopedSession(access,sessionId);
          this.host.getMeta(sessionId);
          const watch = this.watches.get(this.watchKey(access,clientId));
          if (!watch || watch.sessionId !== sessionId) throw new Error('Subscribe to this session before polling');
          watch.seen = Date.now();
          const after = Number(url.searchParams.get('after') ?? 0);
          if (!Number.isSafeInteger(after) || after < 0) throw new Error('Invalid live event cursor');
          const eligible = this.frames.filter(frame => frame.sessionId === sessionId && frame.seq > after);
          const frames: LiveFrame[] = []; let bytes = 0;
          for (const item of eligible) {
            if (frames.length >= 100 || bytes + item.bytes > MAX_FRAME - 4096) break;
            bytes += item.bytes; frames.push({seq: item.seq, sessionId: item.sessionId, frame: item.frame});
          }
          this.send(res, 200, {frames, cursor: frames.at(-1)?.seq ?? this.sequence, hasMore: eligible.length > frames.length,
            gap: after < (this.evicted.get(sessionId) ?? 0),...(access.mode==='operator'&&Number.isSafeInteger(this.host.shortcutSettingsRevision)?{settingsRevision:this.host.shortcutSettingsRevision}:{}),...(access.mode==='operator'&&Number.isSafeInteger(this.host.appearanceRevision)?{appearanceRevision:this.host.appearanceRevision}:{}),...(access.mode==='operator'&&Number.isSafeInteger(this.host.metafoldersRevision)?{metafoldersRevision:this.host.metafoldersRevision}:{}),...(access.mode==='operator'&&Number.isSafeInteger(this.host.modelsRevision)?{modelsRevision:this.host.modelsRevision}:{})});
          return;
        }
        if(req.method==='GET'&&(url.pathname==='/api/preview/office'||url.pathname==='/api/preview/office-generation')){
          if(access.mode!=='operator')throw Error('Office previews require operator authority.');
          const abort=new AbortController(),cancel=()=>{if(!res.writableEnded)abort.abort();};req.once('aborted',cancel);res.once('close',cancel);
          try{await this.host.receiveHarnessRequest(async()=>{
            const sid=identifier(url.searchParams.get('sessionId'));
            if(url.pathname==='/api/preview/office-generation'){this.send(res,200,{generation:this.host.officeGeneration(sid,abort.signal)});return;}
            const value=await this.host.previewOffice(sid,{path:url.searchParams.get('path'),...(url.searchParams.has('priority')?{priority:url.searchParams.get('priority')}:{})},abort.signal);
            const {data,...meta}=value,metadata=Buffer.from(JSON.stringify(meta)),length=Buffer.alloc(4);
            if(metadata.length>256*1024)throw new PreviewReadError('document-render/failed','Office metadata exceeds its preview limit.',{reason:'output-too-large'});
            length.writeUInt32BE(metadata.length);res.writeHead(200,{'Content-Type':'application/octet-stream','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Length':4+metadata.length+data.byteLength});res.end(Buffer.concat([length,metadata,Buffer.from(data)]));
          });}finally{req.removeListener('aborted',cancel);res.removeListener('close',cancel);}return;
        }
        if(req.method==='GET'&&url.pathname==='/api/preview/bytes'){
          if(access.mode!=='operator')throw Error('File previews require operator authority.');
          const abort=new AbortController(),cancel=()=>{if(!res.writableEnded)abort.abort();};req.once('aborted',cancel);res.once('close',cancel);
          try{await this.host.receiveHarnessRequest(async()=>{const sid=identifier(url.searchParams.get('sessionId')),p={path:url.searchParams.get('path'),...(url.searchParams.has('baseFile')?{baseFile:url.searchParams.get('baseFile')}:{}),...(url.searchParams.has('expectedVersion')?{expectedVersion:url.searchParams.get('expectedVersion')}:{})};const value=await this.host.previewFile(sid,'bytes',p,abort.signal);const {data,...meta}=value;res.writeHead(200,{'Content-Type':'application/octet-stream','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Augmentor-Preview':Buffer.from(JSON.stringify(meta)).toString('base64')});res.end(data);});}finally{req.removeListener('aborted',cancel);res.removeListener('close',cancel);}return;
        }
        if (req.method === 'POST' && url.pathname === '/api/rpc') {
          const operation=async()=>{
          const rpc: unknown = await this.body(req); request(rpc);
          const params = rpc.params ?? {};
          if (rpc.method === 'events.subscribe') {
            const sessionId = identifier(params.sessionId), clientId = identifier(params.clientId);
            this.scopedSession(access,sessionId);
            this.host.getMeta(sessionId);
            this.watches.set(this.watchKey(access,clientId), {sessionId, seen: Date.now(),interactive:access.mode==='operator'});
            this.send(res, 200, {id: rpc.id, result: {subscribed: true, cursor: this.sequence,
              queue:{sessionId,...this.host.queueSnapshot(sessionId)},pending: access.mode==='operator'?this.host.interactions.frames(sessionId):[]}});
            return;
          }
          if(access.mode==='read-only'){const result=await this.inspect(access,rpc.method,params,rpc.id);this.send(res,200,{id:rpc.id,result});return;}
          if (!allowed.has(rpc.method)) throw new Error('Method is not exposed by Augmentor Harness');
          if (rpc.method === 'interaction.respond' || rpc.method === 'interaction.wait') {
            const watch = this.watches.get(this.watchKey(access,identifier(params.clientId)));
            if (!watch || watch.sessionId !== params.sessionId) throw new Error('Interaction belongs to another session');
            watch.seen = Date.now();
          }
          let result;
          if(['workspaceFiles.stat','workspaceFiles.read','workspaceFiles.readBytes'].includes(rpc.method)){const abort=new AbortController(),cancel=()=>{if(!res.writableEnded)abort.abort();};req.once('aborted',cancel);res.once('close',cancel);try{const paramsRead=rpc.method==='workspaceFiles.readBytes'&&params.range===undefined?{...params,range:{offset:0,length:256*1024}}:params;try{result={ok:true,value:await this.host.previewFile(params.sessionId,rpc.method==='workspaceFiles.stat'?'stat':rpc.method==='workspaceFiles.read'?'read':'bytes',paramsRead,abort.signal)};}catch(error){const e=error as any;result={ok:false,error:{code:e.code??'gateway/internal',message:e.message,details:e.details??{}}};}}finally{req.removeListener('aborted',cancel);res.removeListener('close',cancel);}}
          else if(rpc.method==='session.fileReferences'){const abort=new AbortController(),cancel=()=>{if(!res.writableEnded)abort.abort();};req.once('aborted',cancel);res.once('close',cancel);try{result=await this.host.listFileReferences(params.sessionId,params.query,abort.signal);}finally{req.removeListener('aborted',cancel);res.removeListener('close',cancel);}}
          else if(rpc.method==='session.jobInspection')result=this.openInspection(this.host.jobInspectionTarget(params.sessionId,params.jobId));
          else if(rpc.method==='models.settingsDiscover'){const abort=new AbortController(),cancel=()=>{if(!res.writableEnded)abort.abort();};req.once('aborted',cancel);res.once('close',cancel);try{result=await this.host.discoverModels(params.request??{},abort.signal);}finally{req.removeListener('aborted',cancel);res.removeListener('close',cancel);}}
          else result = await this.host.dispatch(rpc.method, params, rpc.id);
          this.send(res, 200, {id: rpc.id, result}); return;
          };
          if(access.mode==='operator')await this.host.receiveHarnessRequest(operation);else await operation();
          return;
        }
        this.send(res, 404, {error: {message: 'Unknown Harness API'}}); return;
      }
      if (req.method !== 'GET') {this.send(res, 405, {error: {message: 'Use GET for interface assets'}}); return;}
      const staticFiles = new Map([
        ['/', {path: join(this.assets, 'index.html'), type: 'text/html'}],
        ['/inspection', {path: join(this.assets, 'inspection.html'), type:'text/html'}],
        ['/app.js', {path: join(this.assets, 'app.js'), type: 'text/javascript'}],
        ['/plans.js', {path: join(this.assets, 'plans.js'), type: 'text/javascript'}],
        ['/jobs.js', {path: join(this.assets, 'jobs.js'), type: 'text/javascript'}],
        ['/goals.js', {path: join(this.assets, 'goals.js'), type: 'text/javascript'}],
        ['/native-history.mjs', {path: join(this.assets, 'native-history.mjs'), type: 'text/javascript'}],
        ['/original-search.mjs', {path: join(this.assets, 'original-search.mjs'), type: 'text/javascript'}],
        ['/chat-projection.js', {path: join(this.assets, 'chat-projection.js'), type: 'text/javascript'}],
        ['/message-actions.js', {path: join(this.assets, 'message-actions.js'), type: 'text/javascript'}],
        ['/prompt-library.js', {path: join(this.assets, 'prompt-library.js'), type: 'text/javascript'}],
        ['/prompt-improvement.js', {path: join(this.assets, 'prompt-improvement.js'), type: 'text/javascript'}],
        ['/reasoning.js', {path: join(this.assets, 'reasoning.js'), type: 'text/javascript'}],
        ['/mcp-management.js', {path: join(this.assets, 'mcp-management.js'), type: 'text/javascript'}],
        ['/shared-reasoning/pi-reasoning.mjs', {path:fileURLToPath(new URL('../../../apps/browser/extension/pi-reasoning.mjs',import.meta.url)),type:'text/javascript'}],
        ['/queue-view.js', {path: fileURLToPath(new URL('../../harness-ui/src/queue-view.js', import.meta.url)), type: 'text/javascript'}],
        ['/harness.css', {path: join(this.assets, 'harness.css'), type: 'text/css'}],
        ['/timeline.js', {path: fileURLToPath(new URL('../../harness-ui/src/dsh-timeline.js', import.meta.url)), type: 'text/javascript'}],
        ['/trajectory-contract.js', {path: fileURLToPath(new URL('../../harness-ui/src/trajectory-contract.js', import.meta.url)), type: 'text/javascript'}],
      ]);
      // Fixed, reviewed presentation assets; never expose arbitrary extension files.
      for(const name of ['prompt-animation.mjs', 'prompt-library.mjs','prompt-editor.mjs','clipboard.mjs','settings-form.mjs','maintenance-page.mjs','prompt-library.css']){
        staticFiles.set('/shared-prompts/'+name,{path:fileURLToPath(new URL('../../../apps/browser/extension/'+name,import.meta.url)),type:name.endsWith('.css')?'text/css':'text/javascript'});
      }
      const web=fileURLToPath(new URL('../../harness-web/',import.meta.url));
      if(/^\/[A-Za-z0-9_@.-]+$/.test(url.pathname)){
        try{const names=JSON.parse(readFileSync(join(web,'assets.json'),'utf8')) as string[];const name=url.pathname.slice(1);
          if(names.includes(name)){const ext=name.split('.').at(-1);staticFiles.set(url.pathname,{path:join(web,name),type:({html:'text/html',js:'text/javascript',mjs:'text/javascript',css:'text/css',png:'image/png',svg:'image/svg+xml',txt:'text/plain',json:'application/json',woff2:'font/woff2',woff:'font/woff',ttf:'font/ttf'} as Record<string,string>)[ext!]??'application/octet-stream'});}
        }catch{/* A missing GUI build leaves the reviewed source assets available. */}
      }
      const file = staticFiles.get(url.pathname);
      if (!file) {this.send(res, 404, {error: {message: 'Unknown interface asset'}}); return;}
      const bytes = readFileSync(file.path);
      // This reviewed, self-contained parser receives bytes by postMessage and
      // local BinaryDataFactory replies. It has no network or child-worker need.
      // Wasm decoding is confined here; the application's script policy stays intact.
      if(url.pathname==='/dsh-pdf-worker-6.3.289.mjs')res.setHeader('Content-Security-Policy',"default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'none'; worker-src 'none'");
      if(url.pathname==='/dsh-html-frame.html'){res.setHeader('X-Frame-Options','SAMEORIGIN');res.setHeader('X-DNS-Prefetch-Control','off');res.setHeader('Content-Security-Policy',"sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline' blob:; style-src 'unsafe-inline' blob:; img-src data: blob:; font-src data: blob:; media-src data: blob:; connect-src 'none'; worker-src 'none'; frame-src 'none'; form-action 'none'; base-uri 'none'; frame-ancestors 'self'");res.setHeader('Referrer-Policy','no-referrer');res.setHeader('Permissions-Policy','camera=(), microphone=(), geolocation=(), display-capture=(), payment=(), usb=(), serial=(), clipboard-read=(), clipboard-write=()');}
      if(url.pathname==='/dsh-excel-worker-0.2.1-alpha.2.mjs')res.setHeader('Content-Security-Policy',"default-src 'none'; script-src 'self'; connect-src 'none'; worker-src 'none'");
      res.writeHead(200, {'Content-Type': file.type + '; charset=utf-8'}); res.end(bytes);
    } catch (error) {
      if (res.headersSent) {res.destroy(); return;}
      this.send(res, 400, {error: error instanceof PreviewReadError
        ? {code:error.code,message:error.message,details:error.details}
        : {message: error instanceof Error ? error.message : 'Harness request failed'}});
    }
  }
  async close() {
    this.base=''; this.inspections.clear(); this.watches.clear(); this.frames = []; this.frameBytes = 0; this.evicted.clear();
    await new Promise<void>(resolve => {this.server.close(() => resolve()); this.server.closeAllConnections();});
  }
}
