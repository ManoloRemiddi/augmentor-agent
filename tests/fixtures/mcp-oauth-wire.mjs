// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Independently authored loopback OAuth/MCP fixture. Tokens are synthetic.
import http from 'node:http';
import {once} from 'node:events';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
export async function oauthWire(){
 const stats={initialize:0,tools:0,authorization:0,codeGrants:0,refreshGrants:0,pkceVerified:0},codes=new Map(),metadataWaiters=new Set(),initializeWaiters=new Set();let generation=0,rejectAccess=false,failRefresh=false,holdMetadata=false,holdInitialize=false;
 const wait=(res,waiters)=>new Promise(resolve=>{const finish=()=>{waiters.delete(finish);res.removeListener('close',finish);resolve();};waiters.add(finish);res.once('close',finish);});
 const server=http.createServer(async(req,res)=>{
  try{
   const url=new URL(req.url,base),json=(value,status=200)=>res.writeHead(status,{'content-type':'application/json'}).end(JSON.stringify(value));let raw='';for await(const chunk of req)raw+=chunk;
   if(url.pathname==='/.well-known/oauth-protected-resource'||url.pathname==='/.well-known/oauth-protected-resource/mcp'){
    if(holdMetadata)await wait(res,metadataWaiters);if(res.destroyed)return;
    json({resource:base+'/mcp',authorization_servers:[base],scopes_supported:['read']});return;
   }
   if(url.pathname==='/.well-known/oauth-authorization-server'||url.pathname==='/.well-known/openid-configuration'){json({issuer:base,authorization_endpoint:base+'/authorize',token_endpoint:base+'/token',response_types_supported:['code'],grant_types_supported:['authorization_code','refresh_token'],code_challenge_methods_supported:['S256'],token_endpoint_auth_methods_supported:['none']});return;}
   if(url.pathname==='/authorize'){
    stats.authorization++;assert.equal(url.searchParams.get('code_challenge_method'),'S256');assert.equal(url.searchParams.get('client_id'),'authored-client');const code='AUTHORED_CODE_'+stats.authorization,redirect=new URL(url.searchParams.get('redirect_uri'));codes.set(code,{challenge:url.searchParams.get('code_challenge'),redirect:redirect.href});redirect.searchParams.set('code',code);redirect.searchParams.set('state',url.searchParams.get('state'));res.writeHead(302,{location:redirect.href}).end();return;
   }
   if(url.pathname==='/token'){
    const form=new URLSearchParams(raw);assert.equal(form.get('client_id'),'authored-client');
    if(form.get('grant_type')==='authorization_code'){const code=codes.get(form.get('code'));assert(code,'one issued fixture code');codes.delete(form.get('code'));assert.equal(form.get('redirect_uri'),code.redirect);assert.equal(createHash('sha256').update(form.get('code_verifier')).digest('base64url'),code.challenge);stats.codeGrants++;stats.pkceVerified++;}
    else {assert.equal(form.get('grant_type'),'refresh_token');assert.equal(form.get('refresh_token'),'AUTHORED_REFRESH_'+generation);stats.refreshGrants++;if(failRefresh){json({error:'invalid_grant',error_description:'AUTHORED_PRIVATE_REFRESH_ERROR'},400);return;}}
    generation++;rejectAccess=false;json({access_token:'AUTHORED_ACCESS_'+generation,refresh_token:'AUTHORED_REFRESH_'+generation,token_type:'Bearer',expires_in:3600,scope:'read'});return;
   }
   if(url.pathname!=='/mcp'){json({error:'fixture endpoint unavailable'},404);return;}
   if(req.method==='DELETE'){res.writeHead(200).end();return;}
   if(req.method!=='POST'){res.writeHead(405).end();return;}
   const frame=JSON.parse(raw);if(frame.method==='initialize'&&holdInitialize)await wait(res,initializeWaiters);if(res.destroyed)return;
   if(!generation||rejectAccess||req.headers.authorization!=='Bearer AUTHORED_ACCESS_'+generation){res.writeHead(401,{'www-authenticate':'Bearer resource_metadata="'+base+'/.well-known/oauth-protected-resource", error="invalid_token"'}).end('AUTHORED_PRIVATE_AUTH_BODY');return;}
   if(frame.id===undefined){res.writeHead(202).end();return;}
   const answer=result=>json({jsonrpc:'2.0',id:frame.id,result});
   if(frame.method==='initialize'){stats.initialize++;res.setHeader('mcp-session-id','authored-oauth-session-'+generation);answer({protocolVersion:'2025-03-26',capabilities:{tools:{}},serverInfo:{name:'Authored OAuth MCP',version:'1'}});}
   else if(frame.method==='tools/list')answer({tools:[{name:'read_record',description:'Read a synthetic record',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true}}]});
   else if(frame.method==='tools/call'){stats.tools++;answer({content:[{type:'text',text:'AUTHORED_OAUTH_READ_RECEIPT'}]});}
   else if(frame.method==='resources/list'||frame.method==='resources/templates/list')answer(frame.method==='resources/list'?{resources:[]}:{resourceTemplates:[]});
   else answer({});
  }catch(error){res.writeHead(500,{'content-type':'text/plain'}).end('Authored OAuth fixture assertion failed');errors.push(String(error));}
 });
 const errors=[];server.listen(0,'127.0.0.1');await once(server,'listening');const base='http://127.0.0.1:'+server.address().port;
 return {base,stats,errors,config:{url:base+'/mcp',oauth:{clientId:'authored-client'},exposure:'direct',timeout:2},rejectToken(){rejectAccess=true;},failRefresh(){failRefresh=true;rejectAccess=true;},holdMetadata(){holdMetadata=true;},get pendingMetadata(){return metadataWaiters.size;},releaseMetadata(){holdMetadata=false;for(const finish of [...metadataWaiters])finish();},holdInitialize(){holdInitialize=true;},get pendingInitialize(){return initializeWaiters.size;},releaseInitialize(){holdInitialize=false;for(const finish of [...initializeWaiters])finish();},async close(){for(const waiters of [metadataWaiters,initializeWaiters])for(const finish of [...waiters])finish();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}};
}
