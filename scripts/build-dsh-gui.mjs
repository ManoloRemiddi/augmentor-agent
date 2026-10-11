// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createRequire} from 'node:module';
import {copyFileSync,readFileSync, readdirSync, existsSync, mkdirSync, writeFileSync} from 'node:fs';
import {join, resolve, dirname} from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
const root=resolve(dirname(fileURLToPath(import.meta.url)), '..');
const ui=join(root,'apps/harness'),vendor=join(ui,'vendor/dsh');
const provenance=JSON.parse(readFileSync(join(vendor,'SOURCE.json'),'utf8'));
for(const entry of provenance.files){if(createHash('sha256').update(readFileSync(join(vendor,entry.path))).digest('hex')!==entry.sha256)throw Error('DSH source differs from reviewed public selection: '+entry.path);}
const {build}=createRequire(join(ui,'package.json'))('esbuild');
const packages=new Map();
for(const family of readdirSync(join(vendor,'packages'))){
  for(const name of readdirSync(join(vendor,'packages',family))){
    const directory=join(vendor,'packages',family,name),file=join(directory,'package.json');
    if(existsSync(file))packages.set(JSON.parse(readFileSync(file,'utf8')).name,directory);
  }
}
const result=await build({
  absWorkingDir:root,entryPoints:[join(ui,'dsh-app.jsx')],outdir:join(root,'dist/harness-web'),
  entryNames:'dsh-gui',bundle:true,format:'esm',platform:'browser',target:'chrome120',
  jsx:'automatic',minify:false,metafile:true,legalComments:'eof',
  nodePaths:[join(ui,'node_modules')],loader:{'.woff2':'file','.woff':'file','.ttf':'file','.png':'file','.svg':'dataurl'},
  define:{'process.env.NODE_ENV':'"production"','process.env.DSH_CLIENT_TITLE':'"Augmentor Harness"','process.env.DSH_CLIENT_VERSION':'"0.2.13"','process.env.DSH_CLIENT_COMMIT_HASH':'undefined','process.env.DSH_CLIENT_GIT_DIRTY':'"false"'},
  plugins:[{name:'pinned-public-dsh',setup(b){
    b.onResolve({filter:/^@dsh-gui\//},args=>({path:join(vendor,'packages/client',args.path.slice(9))}));
    b.onResolve({filter:/^@deepseek-ai\//},args=>{
      const parts=args.path.split('/'),name=parts.slice(0,2).join('/'),sub=parts.slice(2).join('/');
      const directory=packages.get(name);
      if(!directory)throw Error('Unselected DSH package: '+args.path);
      let target=sub==='client'?'src/client/index.ts':sub?'src/'+sub+'.ts':'src/index.ts';
      if(sub.startsWith('src/'))target=sub;
      const path=join(directory,target);
      if(!existsSync(path))throw Error('Unselected DSH export: '+args.path+' → '+path);
      return {path};
    });
  }}],
});
const forbidden=Object.keys(result.metafile.inputs).filter(path=>/vendor\/dsh\/.*(?:client-runtime|product-analytics|ui-settings-account|ui-settings-session-log|packages\/host)|node_modules\/(?:@deepseek-ai\/cordis|posthog|@sentry)/.test(path));
if(forbidden.length)throw Error('Supplier runtime/analytics entered the browser graph: '+forbidden.join(', '));
const npmRoots=new Map();
for(const name of Object.keys(result.metafile.inputs)){
  if(!name.includes('node_modules/'))continue;
  let directory=dirname(join(root,name));
  while(directory!==root&&(!existsSync(join(directory,'package.json'))||!JSON.parse(readFileSync(join(directory,'package.json'),'utf8')).name))directory=dirname(directory);
  if(directory===root)throw Error('No supplier manifest for browser input: '+name);
  const manifest=JSON.parse(readFileSync(join(directory,'package.json'),'utf8'));
  npmRoots.set(directory,manifest);
}
const licenses=[readFileSync(join(vendor,'LICENSE'),'utf8')];
const npmRecords=[];
for(const [directory,manifest] of [...npmRoots].sort((a,b)=>a[1].name.localeCompare(b[1].name))){
  const notices=readdirSync(directory).filter(name=>/^(license|notice|copying|copyright)([.\-_]|$)/i.test(name));
  if(!notices.length)throw Error('Missing browser supplier notice: '+manifest.name);
  licenses.push('\n--- '+manifest.name+' '+manifest.version+' ('+manifest.license+') ---\n'+notices.map(name=>readFileSync(join(directory,name),'utf8')).join('\n'));
  npmRecords.push({name:manifest.name,version:manifest.version,license:manifest.license,notices});
}
for(const family of ['cosmokit','schemastery']){
  const notice=join(vendor,'packages/vendor',family,'LICENSE');if(existsSync(notice))licenses.push('\n--- DSH vendor '+family+' ---\n'+readFileSync(notice,'utf8'));
}
mkdirSync(join(root,'dist/harness-web'),{recursive:true});
copyFileSync(join(vendor,'assets/favicon.svg'),join(root,'dist/harness-web/favicon.svg'));
writeFileSync(join(root,'dist/harness-web/THIRD-PARTY-NOTICES.txt'),licenses.join('\n')+'\n');
writeFileSync(join(root,'dist/harness-web/SOURCE.json'),JSON.stringify({dsh:provenance,npm:npmRecords},null,2)+'\n');
writeFileSync(join(root,'dist/harness-web/build-inputs.json'),JSON.stringify(result.metafile,null,2)+'\n');
console.log('Built the pinned public DSH GUI.');

writeFileSync(join(root,'dist/harness-web/assets.json'),JSON.stringify([...Object.keys(result.metafile.outputs).map(p=>p.split('/').at(-1)),'THIRD-PARTY-NOTICES.txt','SOURCE.json','favicon.svg'].sort())+'\n');
