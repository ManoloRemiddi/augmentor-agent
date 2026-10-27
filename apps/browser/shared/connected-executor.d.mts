// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
export function connectedBrowser(owner:string,params:Record<string,unknown>,signal?:AbortSignal):Promise<any>;
export function registerConnectedBrowserHost(send:(frame:unknown)=>void,options?:{busy?:()=>boolean}):{receive(frame:any):boolean;close():void;readonly active:number};
