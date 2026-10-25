// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import http from 'node:http';
import {randomBytes,timingSafeEqual} from 'node:crypto';
import {readFileSync,writeFileSync,mkdirSync,lstatSync,openSync,closeSync,constants} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {installedConnection} from './connection.mjs';
const here=path.dirname(fileURLToPath(import.meta.url));
const equal=(a,b)=>{const x=Buffer.from(a),y=Buffer.from(b);return x.length===y.length&&timingSafeEqual(x,y);};
const security={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Cross-Origin-Resource-Policy':'same-origin','Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; font-src 'self' data:; img-src 'self' data: blob:; frame-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"};
function privateKey(state){
 mkdirSync(state,{recursive:true,mode:0o700});const dir=lstatSync(state);if(!dir.isDirectory()||dir.isSymbolicLink()||dir.uid!==process.getuid()||(dir.mode&0o077))throw Error('Use a private owned mobile state directory.');
 const file=path.join(state,'pairing-key');try{writeFileSync(file,randomBytes(32).toString('base64url'),{mode:0o600,flag:'wx'});}catch(e){if(e.code!=='EEXIST')throw e;}
 const fd=openSync(file,constants.O_RDONLY|constants.O_NOFOLLOW);try{const info=lstatSync(file);if(!info.isFile()||info.uid!==process.getuid()||(info.mode&0o077)||info.size>128)throw Error('Unsafe pairing key.');const key=readFileSync(fd,'utf8').trim();if(!/^[A-Za-z0-9_-]{43}$/.test(key))throw Error('Invalid pairing key.');return key;}finally{closeSync(fd);}
}
export function createMobileAH({connection,state,assets,origins,port=8767,fetcher=fetch,now=Date.now}){
 const target=new URL(connection.origin);if(target.origin!==connection.origin||target.protocol!=='http:'||target.hostname!=='127.0.0.1'||!target.port||!/^[a-f0-9]{64}$/.test(connection.token))throw Error('Use the attested loopback AH connection.');
 const allowed=new Set(origins);if(!allowed.size)throw Error('Declare an exact mobile origin.');
 for(const value of allowed){const u=new URL(value);if(u.origin!==value||u.username||!['https:','http:'].includes(u.protocol)||u.protocol==='http:'&&u.hostname!=='127.0.0.1')throw Error('Use HTTPS or loopback HTTP.');}
 const key=privateKey(state),sessions=new Map();let attempts=[];
 const allowedAssets=new Set(JSON.parse(readFileSync(path.join(assets,'assets.json'),'utf8')));
 const cookie=req=>(req.headers.cookie??'').split(';').map(x=>x.trim()).find(x=>x.startsWith('augmentor_ah_mobile='))?.slice('augmentor_ah_mobile='.length);
 const authenticated=req=>(sessions.get(cookie(req))??0)>now();
 const valid=req=>[...allowed].some(o=>new URL(o).host===req.headers.host)&&(req.headers.origin===undefined?req.method==='GET':allowed.has(req.headers.origin)&&new URL(req.headers.origin).host===req.headers.host)&&(req.headers['sec-fetch-site']!=='cross-site'||req.method==='GET'&&req.headers['sec-fetch-dest']==='document'&&['/','/agent'].includes(req.url?.split(/[?#]/)[0]));
 function reply(res,status,body,type='application/json; charset=utf-8',extra={}){const bytes=Buffer.isBuffer(body)?body:Buffer.from(JSON.stringify(body));res.writeHead(status,{...security,'Content-Type':type,'Content-Length':bytes.length,...extra});res.end(bytes);}
 async function body(req,limit){const chunks=[];let size=0;for await(const c of req){size+=c.length;if(size>limit)throw Error('Request too large.');chunks.push(c);}return Buffer.concat(chunks);}
 const server=http.createServer(async(req,res)=>{
  if(!valid(req))return reply(res,403,{error:{message:'Unrecognized mobile origin.'}});
  const url=new URL(req.url,'http://'+req.headers.host);if(url.origin!=='http://'+req.headers.host)return reply(res,403,{error:{message:'Invalid target.'}});
  try{
   if(req.method==='POST'&&url.pathname==='/mobile/pair'&&!url.search){
    if(req.headers['content-type']!=='application/json')return reply(res,400,{});
    attempts=attempts.filter(t=>now()-t<60000);if(attempts.length>=5)return reply(res,429,{error:{message:'Wait one minute before pairing again.'}});
    const input=JSON.parse(await body(req,2048));if(typeof input.key!=='string'||!equal(input.key,key)){attempts.push(now());return reply(res,401,{error:{message:'Invalid pairing key.'}});}
    for(const [k,expiry]of sessions)if(expiry<=now())sessions.delete(k);if(sessions.size>=24)return reply(res,429,{error:{message:'Too many paired clients. Restart the mobile service to revoke them.'}});
    const token=randomBytes(32).toString('base64url');sessions.set(token,now()+43200000);
    return reply(res,200,{ok:true},undefined,{'Set-Cookie':`augmentor_ah_mobile=${token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200${req.headers.origin.startsWith('https:')?'; Secure':''}`});
   }
   if(req.method==='GET'&&['/','/agent'].includes(url.pathname))return reply(res,200,readFileSync(path.join(here,authenticated(req)?'agent.html':'pair.html')),'text/html; charset=utf-8');
   if(req.method==='GET'&&['/pair.js','/agent.css'].includes(url.pathname))return reply(res,200,readFileSync(path.join(here,url.pathname.slice(1))),url.pathname.endsWith('css')?'text/css':'text/javascript');
   if(!authenticated(req))return reply(res,401,{error:{message:'Pair this device with Augmentor Harness.'}});
   if(req.method==='POST'&&url.pathname==='/mobile/logout'){sessions.delete(cookie(req));return reply(res,200,{ok:true},undefined,{'Set-Cookie':'augmentor_ah_mobile=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'});}
   // Proxy only fixed AH carriers. Its operator token never reaches the phone.
   const getAPI=new Set(['/api/access','/api/events','/api/appearance/revision','/api/drafts/file','/api/attachments/image','/api/preview/bytes','/api/preview/office','/api/preview/office-generation']);
   const postAPI=new Set(['/api/voice/open','/api/voice/events','/api/voice/audio','/api/voice/control','/api/voice/close','/api/rpc','/api/drafts/attachment','/api/attachments/upload','/api/dictation/catalog','/api/dictation/open','/api/dictation/heartbeat','/api/dictation/transcribe','/api/dictation/close']);
   if(req.method==='GET'&&getAPI.has(url.pathname)||req.method==='POST'&&postAPI.has(url.pathname)){
    const data=req.method==='POST'?await body(req,req.headers['content-type']==='application/json'?1048576:20*1024*1024+1024):undefined;
    const abort=new AbortController(),cancel=()=>{if(!res.writableEnded)abort.abort();};res.once('close',cancel);
    try{
     const upstream=await fetcher(connection.origin+url.pathname+url.search,{method:req.method,headers:{Authorization:'Bearer '+connection.token,Origin:connection.origin,...(data?{'Content-Type':req.headers['content-type']??'application/octet-stream'}:{})},...(data?{body:data}:{}),redirect:'error',signal:AbortSignal.any([abort.signal,AbortSignal.timeout(125000)])});
     const bytes=Buffer.from(await upstream.arrayBuffer());if(bytes.length>24*1024*1024)throw Error('AH response is too large.');
     reply(res,upstream.status,bytes,upstream.headers.get('content-type')??'application/octet-stream',upstream.headers.has('x-augmentor-preview')?{'X-Augmentor-Preview':upstream.headers.get('x-augmentor-preview')}:{});
    }finally{res.removeListener('close',cancel);}return;
   }
   if(req.method==='GET'&&!url.search&&/^\/[A-Za-z0-9_@.-]+$/.test(url.pathname)&&allowedAssets.has(url.pathname.slice(1))){
    const ext=path.extname(url.pathname),type={'.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.png':'image/png','.woff2':'font/woff2','.woff':'font/woff','.ttf':'font/ttf','.txt':'text/plain','.json':'application/json'}[ext]??'application/octet-stream';
    if(ext==='.html')return reply(res,404,{});return reply(res,200,readFileSync(path.join(assets,url.pathname.slice(1))),type);
   }
   reply(res,404,{error:{message:'This mobile route is unavailable.'}});
  }catch{return reply(res,502,{error:{message:'Connection unconfirmed. Reconnect to inspect AH. No action was retried.'}});}
 });
 server.requestTimeout=135000;server.headersTimeout=10000;server.maxConnections=32;
 return {server,listen:()=>new Promise((resolve,reject)=>{server.once('error',reject);server.listen(port,'127.0.0.1',()=>resolve(server.address()));}),close:()=>new Promise(resolve=>{sessions.clear();server.close(resolve);server.closeIdleConnections();})};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const port=Number(process.env.AUGMENTOR_MOBILE_AH_PORT??8767),state=process.env.AUGMENTOR_MOBILE_AH_STATE??path.join(process.env.HOME,'.local/state/augmentor-mobile-ah');
 const assets=process.env.AUGMENTOR_MOBILE_AH_ASSETS;if(!assets)throw Error('Build and select mobile presentation assets first.');
 const connection=await installedConnection();const origins=JSON.parse(process.env.AUGMENTOR_MOBILE_AH_ORIGINS??JSON.stringify(['http://127.0.0.1:'+port]));
 const app=createMobileAH({connection,state,assets,origins,port});await app.listen();console.log('Augmentor Agent → existing AH available on loopback port '+port+'. Pairing key stays in the private state directory.');
 process.on('SIGINT',()=>void app.close());process.on('SIGTERM',()=>void app.close());
}
