// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0

/** Authenticated Pi carrier for the unchanged MIT DSH download controller.
 * Long-lived Harness authority stays in the HEAD header. Only an exact, bounded
 * one-use grant reaches the browser's ordinary download manager.
 */
export class DshSessionExport {
 constructor({Controller,controller,save,origin=globalThis.location?.origin}){
  this.controller=controller;this.origin=origin;this.grants=new Map();
  this.original=new Controller(async(route,init)=>{
   const url=new URL(route,this.origin);if(url.origin!==this.origin||url.pathname!=='/api/session.export'||init?.method!=='HEAD')throw Error('Invalid conversation export preparation route.');
   const response=await controller.fetcher(url.pathname+url.search,{...init,headers:{Authorization:'Bearer '+controller.token}});
   if(response.ok){const grant=response.headers.get('x-augmentor-download'),expiresAt=Number(response.headers.get('x-augmentor-download-expires'));
    if(!grant||!/^\/api\/session\.export\/[a-f0-9]{64}$/.test(grant)||!Number.isSafeInteger(expiresAt)||expiresAt<=Date.now()||expiresAt>Date.now()+120_000)throw Error('The local export did not provide a valid one-use download link.');
    this.grants.set(route,{url:grant,expiresAt});
   }
   return response;
  },(route,filename)=>{
   const grant=this.grants.get(route);this.grants.delete(route);if(!grant||grant.expiresAt<=Date.now())throw Error('The prepared conversation download expired.');
   save(grant.url,filename.replace(/^dsh-session-/,'augmentor-session-'));
  });
  this.store=this.original.store;
 }
 async download(sessionId){
  const state=this.controller.state;if(state.readOnly||state.phase!=='ready'||state.sessionId!==sessionId||!state.capabilities?.sessionExport)throw Error('Open an operator conversation with export available before downloading.');
  await this.original.download(sessionId);return {accepted:this.store.getSnapshot().bySession[sessionId]?.status==='success'};
 }
 dismiss=sessionId=>this.original.dismiss(sessionId);
 async dispose(){await this.original.dispose();this.grants.clear();}
}
