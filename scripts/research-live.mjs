// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Explicit operator-only, bounded live qualification. Never prints credential bytes.
import fs from 'node:fs';import path from 'node:path';import{pathToFileURL,fileURLToPath}from'node:url';
const root=process.env.AUGMENTOR_PI_TEST_ROOT??path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const{TavilyResearch}=await import(pathToFileURL(path.join(root,'dist/runtime/src/research.js')));
const file=process.argv[2];if(!file)throw Error('Choose the private Search settings file.');const key=JSON.parse(fs.readFileSync(file,'utf8')).config?.tavilyApiKey;if(!key?.trim())throw Error('Tavily key missing.');
const client=new TavilyResearch(()=>key.trim());const queries=['DeepSeek Harness Trajectory context dashboard dsh-context','Pi coding agent session tree context compaction SDK earendil'];
const report={question:'How do DSH Trajectory / dsh-context and Pi session trees / context compaction differ, and what should Augmentor Harness preserve?',at:new Date().toISOString(),platform:process.platform,results:[],extractions:[]};
for(const query of queries){try{const r=await client.search(query,{max_results:5,include_domains:['github.com','pi.dev']});report.results.push({query,ok:true,sources:r.sources.map(x=>({url:x.url,title:x.title})),credits:r.credits});}catch(e){report.results.push({query,ok:false,code:e.code??'FAILED'});}}
for(const pattern of ['bowenliang123/dsh-context','pi.dev','earendil-works/pi']){const sources=report.results.flatMap(x=>x.sources??[]),s=sources.find(x=>x.url.includes(pattern));if(!s||report.extractions.length>=2)continue;try{const r=await client.fetch(s.url);report.extractions.push({url:r.url,ok:true,characters:r.content.length,format:r.format,truncated:r.truncated,credits:r.credits});}catch(e){report.extractions.push({url:s.url,ok:false,code:e.code??'FAILED'});}}
report.ok=report.results.length===2&&report.results.every(x=>x.ok)&&report.extractions.length===2&&report.extractions.every(x=>x.ok&&x.characters>100);
console.log(JSON.stringify(report,null,2));process.exitCode=report.ok?0:1;
