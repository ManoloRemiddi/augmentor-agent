// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import paths from 'node:path';

/** Compare filesystem paths using their native rules, including Windows separators/case. */
export function relativeBuildInput(directory, importer, pathApi=paths){
 if(!directory||!importer||!pathApi.isAbsolute(directory)||!pathApi.isAbsolute(importer))return;
 const relative=pathApi.relative(directory,importer);
 if(relative&&!pathApi.isAbsolute(relative)&&relative!=='..'&&!relative.startsWith('..'+pathApi.sep))return relative;
}

/** Patched temporary entries retain the original package's nested dependency resolution. */
export function spreadsheetOverlayResolver(entries,origins,pathApi=paths){
 return {name:'original-spreadsheet-patches',setup(build){build.onResolve({filter:/^[^./]/},async args=>{
  if(args.pluginData?.spreadsheetOriginalResolution)return;
  if(entries.has(args.path))return {path:entries.get(args.path)};
  for(const [overlay,original] of origins){
   const relative=relativeBuildInput(overlay,args.importer,pathApi);
   if(relative!==undefined)return build.resolve(args.path,{resolveDir:pathApi.dirname(pathApi.resolve(original,relative)),kind:args.kind,pluginData:{spreadsheetOriginalResolution:true}});
  }
 });}};
}
