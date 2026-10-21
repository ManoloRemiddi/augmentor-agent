// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {open,lstat,readdir} from 'node:fs/promises';import {constants} from 'node:fs';import {resolve,join} from 'node:path';import {createHash} from 'node:crypto';import {spawnSync} from 'node:child_process';
export const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
export async function readRegular(path,limit){
 const file=await open(path,constants.O_RDONLY|constants.O_NOFOLLOW|constants.O_NONBLOCK);
 try{
  const before=await file.stat({bigint:true});if(!before.isFile()||before.size>BigInt(limit))throw Error('Bounded regular source file required');const data=Buffer.alloc(Number(before.size)+1);let offset=0;
  while(offset<data.length){const {bytesRead}=await file.read(data,offset,data.length-offset,null);if(!bytesRead)break;offset+=bytesRead;}
  const after=await file.stat({bigint:true});if(offset!==Number(before.size)||['dev','ino','size','mtimeNs','ctimeNs'].some(k=>before[k]!==after[k]))throw Error('Source file changed during read');return data.subarray(0,offset);
 }finally{await file.close();}
}
export async function readFamily(path){
 const root=resolve(path),dir=join(root,'objects');for(const p of [root,dir]){const stat=await lstat(p);if(!stat.isDirectory()||stat.isSymbolicLink())throw Error('Source family needs real directories');}
 const manifestBytes=await readRegular(join(root,'family.json'),32*1024*1024),manifest=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(manifestBytes));
 if(manifest.schema!=='augmentor-dsh-source-family/1'||!Array.isArray(manifest.nodes)||manifest.nodes.length>160)throw Error('Unsupported bounded source family');
 const refs=new Map();let total=manifestBytes.length;
 for(const node of manifest.nodes){if(!Array.isArray(node.chunks)||node.chunks.length<1||node.chunks.length>8)throw Error('Invalid original-source chunks');let size=0;
  for(const ref of node.chunks){if(!ref||Object.keys(ref).sort().join(',')!=='bytes,sha256'||!(/^[a-f0-9]{64}$/).test(ref.sha256)||!Number.isSafeInteger(ref.bytes)||ref.bytes<1||ref.bytes>16*1024*1024||refs.has(ref.sha256)&&refs.get(ref.sha256)!==ref.bytes)throw Error('Invalid original-source object');refs.set(ref.sha256,ref.bytes);size+=ref.bytes;total+=ref.bytes;}
  if(size!==node.compressedBytes||size>64*1024*1024||total>256*1024*1024||refs.size>16384)throw Error('Source family exceeds its original byte bound');
 }
 const names=await readdir(dir);if(names.length!==refs.size||names.some(n=>!refs.has(n)))throw Error('Source family contains unreferenced objects');
 const object=async sha=>{const bytes=await readRegular(join(dir,sha),16*1024*1024);if(bytes.length!==refs.get(sha)||hash(bytes)!==sha)throw Error('Original-source object changed');return bytes;};
 for(const sha of refs.keys())await object(sha);
 const raw=async node=>{const data=Buffer.concat(await Promise.all(node.chunks.map(ref=>object(ref.sha256))));if(hash(data)!==node.sourceSha256||data.length!==node.compressedBytes)throw Error('Original compressed source hash differs');return data;};
 const rows=async node=>{const bytes=await raw(node),process=spawnSync('zstd',['-dc'],{input:bytes,maxBuffer:128*1024*1024,timeout:30000});if(process.status!==0)throw Error('Bounded source decompression failed');const text=new TextDecoder('utf-8',{fatal:true}).decode(process.stdout);if(!text.endsWith('\n'))throw Error('Incomplete physical source tail');if(hash(process.stdout.subarray(0,process.stdout.indexOf(10)+1))!==node.headerSha256)throw Error('Original physical header hash differs');const lines=text.slice(0,-1).split('\n');if(lines.length>400000||lines.some(line=>Buffer.byteLength(line)>16*1024*1024))throw Error('Physical source row bound exceeded');return lines.map(JSON.parse);};
 const verify=async()=>{if(hash(await readRegular(join(root,'family.json'),32*1024*1024))!==hash(manifestBytes))throw Error('Source family manifest changed');for(const sha of refs.keys())await object(sha);};
 return {root,manifest,manifestBytes,refs,object,raw,rows,verify,expandedBytes:total};
}
