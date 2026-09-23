// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Product identities and optional adapter contracts; engine protocols stay versioned separately. */
export const PRODUCT_PROTOCOL='augmentor/1' as const;
export type HarnessId='pi'|'dsh';
export type SurfaceId='linux'|'browser';
export interface SessionRef {harness:HarnessId;nativeSessionId:string;surface:SurfaceId}
export interface Capabilities {branch:boolean;edit:boolean;memory:boolean}
export const HARNESS_CAPABILITIES:Record<HarnessId,Capabilities>={
  pi:{branch:true,edit:true,memory:true},dsh:{branch:true,edit:true,memory:true},
};
export type MemoryScope='user'|'project';
export interface MemoryRecord {id:string;text:string;type:string;context?:string;document_id?:string}
export interface MemoryOperation {id:string;scope:MemoryScope;document:string;status:'unknown'|'pending'|'processing'|'completed'|'failed'|'cancelled'|'deleted';created:number}
/** Async retention is an operation, not a synchronous fact update or revision CAS. */
export interface MemoryProvider {
  protocol:'augmentor-memory/1';id:string;
  recall(query:string,signal?:AbortSignal):Promise<{enabled:boolean;scope?:MemoryScope;results:MemoryRecord[];unavailable?:boolean}>;
  retain(scope:MemoryScope,content:string,requestId:string,provenance:Record<string,string>):Promise<MemoryOperation>;
  operation(scope:MemoryScope,id:string):Promise<MemoryOperation>;
  deleteDocument(scope:MemoryScope,id:string):Promise<unknown>;
  exportPage(scope:MemoryScope,offset:number):Promise<{items:MemoryRecord[];total:number;offset:number}>;
}
