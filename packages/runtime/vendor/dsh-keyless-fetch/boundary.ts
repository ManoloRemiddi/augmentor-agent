// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Only the original HTTP provider's value/error/deadline contracts; no DSH service. */
export type WebFetchBody={kind:'html'|'text';content:string};
export interface WebFetchRequest {url:string}
export interface WebFetchResult {url:string;statusCode:number;body:WebFetchBody;truncated:boolean}
export interface WebFetchProvider {id:string;available():boolean;fetch(request:WebFetchRequest,signal?:AbortSignal):Promise<WebFetchResult>}
export class WebError extends Error {constructor(message:string,readonly code:string,options?:ErrorOptions){super(message,options);this.name='WebError';}}
class TimeoutReason extends Error {constructor(readonly code:string){super('Public HTTP request deadline reached.');this.name='TimeoutError';}}
export function deadline(parent:AbortSignal|undefined,milliseconds:number,code:string){
 const controller=new AbortController(),reason=new TimeoutReason(code),timer=setTimeout(()=>controller.abort(reason),milliseconds);
 const abort=()=>controller.abort(parent?.reason);parent?.addEventListener('abort',abort,{once:true});if(parent?.aborted)abort();
 return {signal:controller.signal,[Symbol.dispose](){clearTimeout(timer);parent?.removeEventListener('abort',abort);}};
}
export function timeoutOf(signal:AbortSignal,code:string){return signal.reason instanceof TimeoutReason&&signal.reason.code===code?signal.reason:undefined;}
