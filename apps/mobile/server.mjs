// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import http from 'node:http';
import net from 'node:net';
import {randomBytes,timingSafeEqual} from 'node:crypto';
import {readFileSync,writeFileSync,mkdirSync,chmodSync,existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {WebSocketServer} from 'ws';
import {execFile} from 'node:child_process';

const here=path.dirname(fileURLToPath(import.meta.url));
export function createRemoteServer({state,origins,port=8765,vncPort=5975,resize=async()=>{}}) {
  mkdirSync(state,{recursive:true,mode:0o700});chmodSync(state,0o700);
  const keyFile=path.join(state,'pairing-key');
  if(!existsSync(keyFile))writeFileSync(keyFile,randomBytes(32).toString('base64url'),{mode:0o600});
  const key=readFileSync(keyFile,'utf8').trim();
  const allowed=new Set(origins);
  for(const origin of allowed){const u=new URL(origin);if(u.origin!==origin||u.username||!['http:','https:'].includes(u.protocol)||u.protocol==='http:'&&!['127.0.0.1','localhost'].includes(u.hostname))throw Error('Use exact HTTPS origins, or loopback HTTP.');}
  const sessions=new Map();let attempts=[];let control=null;
  const wss=new WebSocketServer({noServer:true,maxPayload:2*1024*1024,perMessageDeflate:false});
  function cookie(req){const token=(req.headers.cookie??'').split(';').map(x=>x.trim()).find(x=>x.startsWith('augmentor_desktop='))?.slice(18);return token;}
  function authorized(req){return (sessions.get(cookie(req))??0)>Date.now();}
  function valid(req,originRequired=false){
    const origin=req.headers.origin;
    return origin ? allowed.has(origin)&&new URL(origin).host===req.headers.host : !originRequired&&[...allowed].some(o=>new URL(o).host===req.headers.host);
  }
  function reply(res,status,value,type='application/json',extra={}){
    const body=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value));
    res.writeHead(status,{'Content-Type':type,'Content-Length':body.length,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",...extra});res.end(body);
  }
  const files=new Map([['/',['web/index.html','text/html']],['/app.js',['build/app.js','text/javascript']],['/third-party.txt',['build/third-party.txt','text/plain; charset=utf-8']],['/style.css',['web/style.css','text/css']],['/manifest.webmanifest',['web/manifest.webmanifest','application/manifest+json']],['/icon-192.png',['web/icon-192.png','image/png']],['/icon-512.png',['web/icon-512.png','image/png']]]);
  const server=http.createServer(async(req,res)=>{
    if(!valid(req,req.method==='POST'))return reply(res,403,{error:'Unrecognized origin.'});
    if(req.method==='GET'){
      const file=files.get(req.url);if(!file)return reply(res,404,{error:'Not found.'});
      try{return reply(res,200,readFileSync(path.join(here,file[0])),file[1]);}catch{return reply(res,503,{error:'Build the remote client first.'});}
    }
    if(req.method!=='POST'||!['/api/pair','/api/connect','/api/logout','/api/resize','/api/show'].includes(req.url))return reply(res,404,{error:'Not found.'});
    if(req.url!=='/api/pair'&&!authorized(req))return reply(res,401,{error:'Pair with your computer.'});
    if(req.headers['content-type']!=='application/json')return reply(res,400,{error:'Expected JSON.'});
    try{
      let size=0;const chunks=[];for await(const chunk of req){size+=chunk.length;if(size>16384){reply(res,413,{error:'Request too large.'});req.destroy();return;}chunks.push(chunk);}
      const body=JSON.parse(Buffer.concat(chunks));if(!body||typeof body!=='object'||Array.isArray(body))throw Error('Invalid request.');
      if(req.url==='/api/pair'){
        attempts=attempts.filter(t=>Date.now()-t<60000);if(attempts.length>=5)return reply(res,429,{error:'Wait one minute before trying again.'});
        const supplied=Buffer.from(typeof body.key==='string'?body.key:'');const expected=Buffer.from(key);
        if(supplied.length!==expected.length||!timingSafeEqual(supplied,expected)){attempts.push(Date.now());return reply(res,401,{error:'Invalid pairing key.'});}
        for(const [token,expires] of sessions)if(expires<Date.now())sessions.delete(token);
        const token=randomBytes(32).toString('base64url');sessions.set(token,Date.now()+43200000);
        return reply(res,200,{ok:true},'application/json',{'Set-Cookie':`augmentor_desktop=${token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200${req.headers.origin.startsWith('https:')?'; Secure':''}`});
      }
      if(req.url==='/api/logout'){
        const token=cookie(req);sessions.delete(token);for(const ws of wss.clients)if(ws.owner===token)ws.close(1000,'Disconnected');
        return reply(res,200,{ok:true},'application/json',{'Set-Cookie':'augmentor_desktop=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'});
      }
      if(req.url==='/api/connect'){
        if(control)return reply(res,409,{error:'Another tab or device is connected. Disconnect it, then reconnect here.'});
        return reply(res,200,{protocol:'augmentor-desktop/1',password:readFileSync(path.join(state,'vnc-secret'),'utf8').trim()});
      }
      if(control&&control.owner!==cookie(req))return reply(res,409,{error:'Another device is controlling this window.'});
      if(req.url==='/api/resize'){
        if(!Number.isInteger(body.width)||!Number.isInteger(body.height)||body.width<340||body.width>1600||body.height<300||body.height>1400)throw Error('Invalid viewport.');
        await resize(body.width,body.height);
      }else await resize(null,null,true);
      reply(res,200,{ok:true});
    }catch{return reply(res,400,{error:'Request could not be applied. No input was replayed.'});}
  });
  server.requestTimeout=15000;server.headersTimeout=10000;server.maxConnections=24;
  server.on('upgrade',(req,socket,head)=>{
    if(req.url!=='/desktop'||!valid(req,true)||!authorized(req)){socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n');return;}
    if(control){socket.end('HTTP/1.1 409 Conflict\r\nConnection: close\r\n\r\n');return;}
    wss.handleUpgrade(req,socket,head,ws=>{
      control=ws;ws.owner=cookie(req);ws.alive=true;ws.on('pong',()=>ws.alive=true);
      const upstream=net.createConnection({host:'127.0.0.1',port:vncPort});
      const interval=setInterval(()=>{if(!authorized(req)){ws.close(1008,'Pairing expired');upstream.destroy();}else if(!ws.alive){ws.terminate();upstream.destroy();}else{ws.alive=false;ws.ping();}},15000);
      let ready=false;upstream.on('connect',()=>{ready=true;});
      upstream.on('data',data=>{if(ws.readyState!==1)return;if(ws.bufferedAmount>4*1024*1024){ws.close(1013,'Connection too slow');return;}ws.send(data,{binary:true});});
      ws.on('message',(data,binary)=>{if(!binary||!ready||!authorized(req)){ws.close(1008,'Invalid input');return;}if(upstream.writableLength>2*1024*1024){ws.close(1013,'Connection too slow');return;}upstream.write(data);});
      upstream.on('error',()=>ws.close(1011,'Desktop unavailable'));upstream.on('close',()=>ws.close());
      ws.on('error',()=>upstream.destroy());ws.on('close',()=>{clearInterval(interval);upstream.destroy();if(control===ws)control=null;});
    });
  });
  return {server,wss,sessions,authorized,close:()=>{for(const ws of wss.clients)ws.terminate();wss.close();server.close();},listen:()=>new Promise(resolve=>server.listen(port,'127.0.0.1',resolve))};
}
if(process.argv[1]&&fileURLToPath(import.meta.url)===path.resolve(process.argv[1])){
  const state=process.env.AUGMENTOR_REMOTE_STATE; if(!state)throw Error('Use start.py to start the isolated Desktop.');
  let pending=Promise.resolve();
  const resize=(width,height,show=false)=>{
    const job=async()=>{
      const file=path.join(state,'viewport.json');let value=JSON.parse(readFileSync(file,'utf8'));
      if(width){value.width=width;value.height=height;}if(show)value.show=randomBytes(6).toString('hex');
      writeFileSync(file,JSON.stringify(value),{mode:0o600});
      if(width)await new Promise((resolve,reject)=>execFile(process.env.AUGMENTOR_X11VNC,['-display',process.env.DISPLAY,'-auth',process.env.XAUTHORITY,'-R',`clip:${width}x${height}+0+0`],{timeout:5000},error=>error?reject(error):resolve()));
    };
    const result=pending.then(job);pending=result.catch(()=>{});return result;
  };
  const app=createRemoteServer({state,origins:JSON.parse(process.env.AUGMENTOR_REMOTE_ORIGINS),vncPort:Number(process.env.AUGMENTOR_VNC_PORT),resize});
  await app.listen();console.log('Original Augmentor Desktop available on http://127.0.0.1:8765');
  process.on('SIGTERM',()=>app.close());process.on('SIGINT',()=>app.close());
}
