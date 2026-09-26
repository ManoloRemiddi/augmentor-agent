#!/usr/bin/env node
// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import http from 'node:http'
import {readFile} from 'node:fs/promises'
import {fileURLToPath} from 'node:url'
import {resolve,extname,sep} from 'node:path'
import {createHash,timingSafeEqual} from 'node:crypto'
import {spawn} from 'node:child_process'
import {WebSocketServer,WebSocket} from 'ws'
import {loadProfile,preferences} from '../../../services/workspaces/profiles.mjs'
import {RELEASE} from '../../../dist/contracts/src/release.js'
export const MAX_FRAME=20*1024*1024
const root=fileURLToPath(new URL('../extension/',import.meta.url))
const types={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.woff2':'font/woff2'}
const digest=v=>createHash('sha256').update(String(v)).digest()
export function nativeConnection(ws,profile,{start=spawn}={}){
 const child=start(process.execPath,[fileURLToPath(new URL('../native-host.mjs',import.meta.url))],{stdio:['pipe','pipe','ignore'],env:{...process.env,AUGMENTOR_WORKSPACE_PROFILE:profile.id}})
 let buffer=Buffer.alloc(0),alive=true,closed=false
 const end=()=>{if(closed)return;closed=true;clearInterval(timer);child.stdin.end();child.kill();setTimeout(()=>child.kill('SIGKILL'),2000).unref();ws.terminate()}
 const timer=setInterval(()=>{if(!alive)return end();alive=false;ws.ping()},15000);timer.unref()
 ws.on('pong',()=>{alive=true})
 child.stdout.on('data',chunk=>{
  buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4){const n=buffer.readUInt32LE(0);if(n>MAX_FRAME)return end();if(buffer.length<n+4)break;const frame=buffer.subarray(4,4+n);buffer=buffer.subarray(4+n);if(ws.readyState!==WebSocket.OPEN||ws.bufferedAmount>MAX_FRAME*2)return end();ws.send(frame.toString())}
 })
 ws.on('message',(raw,binary)=>{if(binary||raw.length>1024*1024)return end();let frame;try{frame=JSON.parse(String(raw))}catch{return end()}
  if(frame.type==='embed/ping'){ws.send(JSON.stringify({type:'embed/pong'}));return}
  // No queue or replay: native messaging dispatch belongs to this live socket only.
  const body=Buffer.from(JSON.stringify(frame)),size=Buffer.alloc(4);size.writeUInt32LE(body.length)
  if(child.stdin.writableLength>2*1024*1024)return end();child.stdin.write(Buffer.concat([size,body]))
 })
 ws.on('close',end);ws.on('error',end);child.on('error',end);child.on('exit',end);child.stdin.on('error',end)
 return end
}
export function createEmbedServer({profileLoader=loadProfile,startNative=nativeConnection,assetRoot=root}={}){
 const wss=new WebSocketServer({noServer:true,maxPayload:1024*1024,perMessageDeflate:false})
 async function authorize(req){
  const url=new URL(req.url,'http://127.0.0.1'),match=/^\/embed\/([a-z][a-z0-9-]*)\/(.*)$/.exec(url.pathname)
  if(!match)throw Error('Unknown Augmentor workspace route')
  const p=profileLoader(match[1]),token=(await readFile(p.accessTokenFile,'utf8')).trim()
  if(token.length<32||!timingSafeEqual(digest(token),digest(req.headers.authorization?.replace(/^Bearer /,''))))throw Error('Workspace proxy authentication required')
  if(req.headers.origin&&req.headers.origin!==p.parentOrigin)throw Error('Workspace origin rejected')
  if(req.headers['sec-fetch-site']==='cross-site')throw Error('Cross-site request rejected')
  return {p,file:decodeURIComponent(match[2])}
 }
 const server=http.createServer(async(req,res)=>{
  const json=(code,value)=>{res.writeHead(code,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(value))}
  try{
   const {p,file}=await authorize(req)
   res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Referrer-Policy','no-referrer')
   res.setHeader('Content-Security-Policy',`default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors ${p.parentOrigin}; base-uri 'self'; form-action 'self'`)
   if(file==='config.json'&&req.method==='GET')return json(200,{id:p.id,name:p.name,version:RELEASE.version,parentOrigin:p.parentOrigin,publicPath:p.publicPath,harness:'dsh',preset:p.preset})
   if(file==='preferences'){
    if(req.method==='GET')return json(200,preferences(p))
    if(req.method!=='POST'||req.headers.origin!==p.parentOrigin||!req.headers['content-type']?.startsWith('application/json'))return json(403,{error:'Same-origin JSON required'})
    let body='';for await(const chunk of req){body+=chunk;if(Buffer.byteLength(body)>1024*1024)throw Error('Preferences too large')}
    return json(200,preferences(p,JSON.parse(body)))
   }
   if(!['GET','HEAD'].includes(req.method))return json(405,{error:'Unsupported method'})
   const name=file||'sidepanel.html',path=resolve(assetRoot,name)
   if(!path.startsWith(resolve(assetRoot)+sep)||name.split('/').some(part=>part.startsWith('.'))||!types[extname(path)])return json(404,{error:'File unavailable'})
   let content=await readFile(name==='embedded-entry.mjs'?fileURLToPath(new URL('./entry.mjs',import.meta.url)):path)
   if(['sidepanel.html','settings.html'].includes(name))content=Buffer.from(content.toString().replace(/src="(?:sidepanel.js|settings.mjs)"/,'src="embedded-entry.mjs"'))
   res.writeHead(200,{'Content-Type':types[extname(path)]});res.end(req.method==='HEAD'?undefined:content)
  }catch(error){json(error.code==='ENOENT'?404:403,{error:'Augmentor workspace is unavailable or the proxy is not authorized.'})}
 })
 server.on('upgrade',async(req,socket,head)=>{try{const {p,file}=await authorize(req);if(file!=='native'||req.headers.origin!==p.parentOrigin)throw Error('Invalid socket');wss.handleUpgrade(req,socket,head,ws=>startNative(ws,p))}catch{socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n')}})
 server.on('close',()=>{for(const c of wss.clients)c.terminate();wss.close()})
 return server
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const server=createEmbedServer();server.listen(Number(process.env.AUGMENTOR_EMBED_PORT||8872),'127.0.0.1',()=>console.log('Augmentor embedding service ready (loopback only)'))
 const stop=()=>{server.close();setTimeout(()=>process.exit(0),1000).unref()};process.on('SIGTERM',stop);process.on('SIGINT',stop)
}
