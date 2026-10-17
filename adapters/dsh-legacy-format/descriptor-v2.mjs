// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Authored validation of the public August DSH v2 descriptor contract. See the
// exact source revision and licence in release/dsh-legacy-format/SOURCES.json.
const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
const fail=()=>{throw Error('Unsupported historical DSH descriptor-v2 payload.');};
const keys=(value,required,optional)=>{if(!object(value)||required.some(k=>!Object.hasOwn(value,k))||Object.keys(value).some(k=>!required.includes(k)&&!optional.includes(k)))fail();};
/** Validate only; preserve the exact metadata, including empty optional strings.
 * Nothing here grants a model route, tool, child job or resumption authority. */
export function validateDescriptorV2(value){
 if(!object(value)||value.version!==2||typeof value.provider!=='string')fail();
 if(value.mode==='one-shot')keys(value,['version','mode','provider'],['label']);
 else if(value.mode==='continuable'){
  keys(value,['version','mode','provider','label'],['agentProvider','agentModel','persona','toolFilter']);
  if(typeof value.label!=='string')fail();
 }else fail();
 for(const k of ['label','agentProvider','agentModel','persona'])if(Object.hasOwn(value,k)&&typeof value[k]!=='string')fail();
 if(Object.hasOwn(value,'toolFilter')){
  const filter=value.toolFilter;keys(filter,[],['allow','deny']);if(!Object.hasOwn(filter,'allow')&&!Object.hasOwn(filter,'deny'))fail();
  for(const k of ['allow','deny'])if(Object.hasOwn(filter,k)&&(!Array.isArray(filter[k])||filter[k].some(x=>typeof x!=='string')))fail();
 }
}
