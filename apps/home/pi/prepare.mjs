// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Match the family's reviewed SDK/Photon inputs in an unselected Home image.
import {readFileSync,writeFileSync,existsSync,realpathSync,rmSync,cpSync,mkdirSync} from 'node:fs';
import {resolve,join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
if(!process.argv[2])throw Error('Provide an explicit unselected Home dependency prefix.');
const source=fileURLToPath(new URL('../../../',import.meta.url)),target=realpathSync(resolve(process.argv[2]));
if(existsSync(join(target,'desktop-release.json'))||existsSync(join(target,'.git')))throw Error('Never modify a sealed release or source checkout.');
const read=p=>JSON.parse(readFileSync(p,'utf8')),sha=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
for(const [name,version] of Object.entries({'@earendil-works/pi-coding-agent':'1.2.0','@earendil-works/pi-mcp':'1.2.0',typebox:'1.3.7',ws:'8.21.3'}))if(read(join(target,'node_modules',name,'package.json')).version!==version)throw Error('Unreviewed Home dependency '+name);
if(read(join(target,'package.json')).name!=='@augmentor/home-pi-runtime')throw Error('Choose the Home Pi dependency prefix.');
const family=read(join(source,existsSync(join(source,'family-package-lock.json'))?'family-package-lock.json':'package-lock.json')).packages;
const installed=read(join(target,'package-lock.json')).packages;
const sdkFamily={};
for(const [path,entry] of Object.entries(installed)){
 const name=path.split('node_modules/').at(-1);
 if(!name.startsWith('@earendil-works/'))continue;
 if(family['node_modules/'+name]?.version!==entry.version)throw Error('Home SDK family differs from the tested product: '+path);
 sdkFamily[name]=entry.version;
}
const vendor=join(source,'vendor/photon-node'),record=read(join(vendor,'BUILD.json')),expected=read(join(source,'release/photon/build.json'));
for(const [key,value] of Object.entries(expected))if(JSON.stringify(record[key])!==JSON.stringify(value))throw Error('Photon source/build identity differs');
if(sha(join(source,'release/photon/Cargo.lock'))!==record.cargoLockSha256)throw Error('Photon Rust lock differs');
for(const [name,digest] of Object.entries(record.files)){const file=resolve(vendor,name);if(!file.startsWith(vendor+'/')||sha(file)!==digest)throw Error('Photon file identity differs');}
const require=createRequire(join(target,'node_modules/@earendil-works/pi-coding-agent/package.json')),photon=realpathSync(dirname(require.resolve('@silvia-odwyer/photon-node/package.json')));
if(!photon.startsWith(target+'/node_modules/')||read(join(photon,'package.json')).version!==record.npmVersion)throw Error('Unexpected Photon dependency layout');
rmSync(photon,{recursive:true});cpSync(vendor,photon,{recursive:true});
mkdirSync(join(target,'licenses'),{recursive:true});writeFileSync(join(target,'licenses/home-sdk-family.json'),JSON.stringify(sdkFamily,null,2)+'\n');
const licences=join(target,'licenses/photon');mkdirSync(licences,{recursive:true});cpSync(join(vendor,'third-party'),licences,{recursive:true});cpSync(join(vendor,'BUILD.json'),join(licences,'BUILD.json'));
rmSync(join(target,'node_modules/@earendil-works/pi-coding-agent/dist/bundle'),{recursive:true,force:true});
writeFileSync(join(target,'distribution-overrides.json'),JSON.stringify({photon:{npmVersion:record.npmVersion,source:record.source,changes:record.changes,wasmSha256:record.files['photon_rs_bg.wasm']}},null,2)+'\n');
writeFileSync(join(target,'distribution-exclusions.json'),JSON.stringify([{name:'@earendil-works/pi-coding-agent',version:'1.2.0',path:'dist/bundle',reason:'unused CLI/RPC bundles; Home uses the public SDK'}],null,2)+'\n');
