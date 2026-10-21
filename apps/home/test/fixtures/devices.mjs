// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {Ledger} from '../../ledger.mjs';import {mkdtempSync,rmSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';import {createServer} from 'node:http';import {once} from 'node:events';import {WebSocketServer} from 'ws';
import {Devices} from '../../devices.mjs';
export async function fixture(t){
 let writes=[],state='off',registry={entity_id:'light.fixture',id:'registry-id',unique_id:'hardware-id',platform:'fixture',config_entry_id:'integration-id'};
 const server=createServer(async(req,res)=>{res.setHeader('Content-Type','application/json');if(req.method==='POST'){let raw='';for await(const part of req)raw+=part;writes.push({path:req.url,body:JSON.parse(raw)});state='on';res.end('[]');}else{const item={entity_id:'light.fixture',state,attributes:{friendly_name:'Fixture'}};res.end(JSON.stringify(req.url==='/api/states'?[item]:item));}});
 const ws=new WebSocketServer({server,path:'/api/websocket'});ws.on('connection',socket=>{socket.send(JSON.stringify({type:'auth_required'}));socket.on('message',raw=>{const m=JSON.parse(raw);socket.send(JSON.stringify(m.type==='auth'?{type:'auth_ok'}:{id:m.id,type:'result',success:true,result:m.type.endsWith('/list')?[registry]:registry}));});});
 server.listen(0,'127.0.0.1');await once(server,'listening');const ledger=new Ledger(':memory:'),db=ledger.db;
 const devices=new Devices({mcpUrl:`http://127.0.0.1:${server.address().port}/api/mcp/assist`,haToken:'fixture'},db);
 t.after(()=>{for(const client of ws.clients)client.terminate();ws.close();server.closeAllConnections();server.close();db.close();});
 return {devices,writes,ledger,url:`http://127.0.0.1:${server.address().port}`,replace(){registry={...registry,id:'replacement',unique_id:'new-device'};}};
}
