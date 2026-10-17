// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Read-only aggregation of provider-reported counts in Augmentor-owned journals.
import {readFileSync, readdirSync, lstatSync, existsSync} from 'node:fs';
import {join, resolve, relative, sep} from 'node:path';
import {homedir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {zstdDecompressSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {scanZstdFrames} from '../recovery/zstd-frames.mjs';

const personal=new Set(['augmentor-linux','augmentor-browser','augmentor-linux-product','augmentor-browser-product']);
const count=n=>Number.isSafeInteger(n)&&n>=0;
const inside=(root,path)=>{const r=relative(resolve(root),resolve(path));return r!==''&&!r.startsWith('..'+sep)&&r!=='..'&&!r.startsWith(sep);};
const dateKey=time=>{const d=new Date(time);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;};
function entries(path){try {return readdirSync(path,{withFileTypes:true}).filter(e=>!e.isSymbolicLink());}catch{return [];}}
function regular(path){const s=lstatSync(path);if(!s.isFile()||s.isSymbolicLink()||(process.getuid&&s.uid!==process.getuid()))throw Error('Unusable history');return s;}

export function collectUsage({dshHome,piState,codexState,now=Date.now(),milliseconds=12000}={}){
  const end=dateKey(now),startDate=new Date(now);startDate.setDate(startDate.getDate()-364);const start=dateKey(startDate);
  const days=new Map(),seen=new Set(),sources=new Set();let incomplete=0,records=0,bytes=0,files=0,total=0;
  const deadline=Date.now()+milliseconds;
  const read=path=>{if(Date.now()>deadline||files++>=4000)throw Error('History budget');const stat=regular(path);if(stat.size>64*1024*1024||(bytes+=stat.size)>512*1024*1024)throw Error('History budget');return readFileSync(path);};
  const json=path=>{if(regular(path).size>1024*1024)throw Error('Metadata too large');return JSON.parse(readFileSync(path,'utf8'));};
  function add(source,key,time,usage){
    const ms=typeof time==='number'?time:Date.parse(time);if(!Number.isFinite(ms)){incomplete++;return;}
    const day=dateKey(ms);if(day<start||day>end)return;
    if(!usage||!count(usage.total)||!count(usage.input)||!count(usage.output)){incomplete++;return;}
    if(seen.has(key))return;
    const row=days.get(day)??{date:day,total:0,input:0,output:0,cached:0};
    const next={...row};
    for(const field of ['total','input','output','cached']){
      const value=count(usage[field])?usage[field]:0;
      if(!count(row[field]+value)){incomplete++;return;}next[field]+=value;
    }
    if(!count(total+usage.total)){incomplete++;return;}
    total+=usage.total;seen.add(key);sources.add(source);records++;days.set(day,next);
  }
  const lines=raw=>{if(raw.length&&raw.at(-1)!==10){incomplete++;raw=raw.subarray(0,raw.lastIndexOf(10)+1);}return raw.toString('utf8').split('\n').filter(Boolean).map(line=>JSON.parse(line));};
  if(dshHome){
    const root=join(dshHome,'sessions');
    for(const cwd of entries(root).filter(e=>e.isDirectory()))for(const session of entries(join(root,cwd.name)).filter(e=>e.isDirectory())){
      const dir=join(root,cwd.name,session.name),compressed=join(dir,'session.v3.jsonl.zstd'),plain=join(dir,'session.v3.jsonl');
      const path=existsSync(compressed)?compressed:plain;if(!existsSync(path))continue;
      try{
        const raw=read(path);let chunks;
        if(path.endsWith('.zstd')){
          const {frames,tornStart}=scanZstdFrames(raw);if(!frames.length)throw Error('No complete history');if(tornStart!==undefined)incomplete++;
          const first=zstdDecompressSync(raw.subarray(frames[0].start,frames[0].end),{maxOutputLength:16*1024*1024});
          const header=JSON.parse(first.toString('utf8').split('\n')[0]);
          if(header.type!=='session'||header.version!==3||!personal.has(header.agentPreset))continue;
          let decoded=first.length;chunks=[first];
          for(const f of frames.slice(1)){const part=zstdDecompressSync(raw.subarray(f.start,f.end),{maxOutputLength:128*1024*1024-decoded});decoded+=part.length;chunks.push(part);}
        }else chunks=[raw];
        const rows=lines(Buffer.concat(chunks)),header=rows.shift();
        if(header?.type!=='session'||header.version!==3||!personal.has(header.agentPreset))continue;
        let seeded=header.isSeeded===true;
        for(const e of rows){
          if(e.type==='session/end-seed'){seeded=false;continue;}
          if(seeded||e.type!=='assistant/message')continue;
          const u=e.data?.usage;
          add('DSH',`dsh:${header.id}:${e.seq}`,e.time,u&&{total:u.totalTokens,input:u.inputTokens,output:u.outputTokens,cached:u.cacheReadTokens});
        }
      }catch{incomplete++;}
    }
  }
  if(piState){
    const root=join(piState,'sessions'),paths=new Set();
    for(const entry of entries(root).filter(e=>e.isFile()&&e.name.endsWith('.meta.json'))){
      try{const meta=json(join(root,entry.name));if(typeof meta.file!=='string'||!inside(root,meta.file)||relative(root,meta.file).split(sep).slice(0,-1).some((_,i,parts)=>lstatSync(join(root,...parts.slice(0,i+1))).isSymbolicLink())){if(meta.file)incomplete++;continue;}paths.add(meta.file);}catch{incomplete++;}
    }
    for(const path of paths)try{
      for(const e of lines(read(path))){const m=e.message;if(e.type!=='message'||m?.role!=='assistant')continue;const u=m.usage;
        add('Pi',`pi:${e.id}:${e.timestamp}`,e.timestamp,u&&{total:u.totalTokens,input:u.input,output:u.output,cached:u.cacheRead});}
    }catch{incomplete++;}
  }
  if(codexState){
    const roots=new Set();
    for(const e of entries(join(codexState,'sessions')).filter(e=>e.isFile()&&e.name.endsWith('.json')))try{
      const meta=json(join(codexState,'sessions',e.name)),id=meta.nativeOwner??meta.id;
      if(meta.status==='ready'&&typeof id==='string'&&/^[a-zA-Z0-9_-]{1,128}$/.test(id))roots.add(join(codexState,'threads',id,'runtime','sessions'));
    }catch{incomplete++;}
    function scan(root,depth=0){if(depth>4)return;for(const e of entries(root)){
      const path=join(root,e.name);if(e.isDirectory()){scan(path,depth+1);continue;}if(!e.isFile()||!e.name.endsWith('.jsonl'))continue;
      try{let previous=0;
        for(const e of lines(read(path))){if(e.type!=='event_msg'||e.payload?.type!=='token_count')continue;
          const u=e.payload.info?.total_token_usage;if(!u||![u.total_tokens,u.input_tokens,u.output_tokens].every(count)){incomplete++;continue;}
          const total=u.total_tokens;if(total<previous){incomplete++;previous=total;continue;}
          const delta=total-previous;previous=total;if(!delta)continue;
          // Native forks copy earlier records verbatim; count that provider usage once.
          const key='codex:'+createHash('sha256').update(JSON.stringify([e.timestamp,u])).digest('hex');
          const last=e.payload.info?.last_token_usage;
          const valid=last&&[last.total_tokens,last.input_tokens,last.output_tokens].every(count)&&last.total_tokens===delta;
          if(!valid){incomplete++;continue;}
          add('Codex',key,e.timestamp,{total:delta,input:last.input_tokens,output:last.output_tokens,cached:last.cached_input_tokens});
        }
      }catch{incomplete++;}
    }}
    for(const root of roots)scan(root);
  }
  const values=[...days.values()].sort((a,b)=>a.date.localeCompare(b.date));
  return {start,end,days:values,total,records,sources:[...sources],incomplete};
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const config=process.env.AUGMENTOR_SHARED_CONFIG??join(process.env.XDG_CONFIG_HOME??join(homedir(),'.config'),'augmentor');
  let dshHome;try{dshHome=JSON.parse(readFileSync(join(config,'harnesses.json'),'utf8')).dsh?.home;}catch{}
  const state=process.env.XDG_STATE_HOME??join(homedir(),'.local','state');
  console.log(JSON.stringify(collectUsage({dshHome,piState:process.env.AUGMENTOR_PI_STATE??join(state,'augmentor-pi'),codexState:process.env.AUGMENTOR_CODEX_STATE??join(state,'augmentor-codex')})));
}
