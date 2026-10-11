// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {WorkspaceFileSearch,DEFAULT_FILE_SEARCH_EXCLUDED_DIRECTORIES} from '../vendor/dsh-file-reference/search.js';
/** Bounded path-only original DSH search instances. Metadata reads never load
 * an SDK owner. The caller supplies the current authorized session namespace. */
export class PiFileReferences {
 private searches=new Map<string,{cwd:string;search:WorkspaceFileSearch}>();
 async list(sid:string,cwd:string,query:unknown,signal:AbortSignal){
  if(typeof query!=='string'||query.length>4096||/[\x00-\x1f\x7f-\x9f]/.test(query))throw Error('Invalid file-reference query.');
  signal.throwIfAborted();let seat=this.searches.get(sid);
  if(seat&&seat.cwd!==cwd){seat.search.dispose();this.searches.delete(sid);seat=undefined;}
  if(!seat){while(this.searches.size>=8){const first=this.searches.keys().next().value!;this.searches.get(first)!.search.dispose();this.searches.delete(first);}seat={cwd,search:new WorkspaceFileSearch(cwd,{maxResults:20,maxEntries:50_000,excludedDirectories:DEFAULT_FILE_SEARCH_EXCLUDED_DIRECTORIES})};}
  this.searches.delete(sid);this.searches.set(sid,seat);return seat.search.list(query,signal);
 }
 invalidate(sid:string){this.searches.get(sid)?.search.invalidate();}
 close(){for(const seat of this.searches.values())seat.search.dispose();this.searches.clear();}
}
