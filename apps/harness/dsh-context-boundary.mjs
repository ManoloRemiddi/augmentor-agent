// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// The copied presentation uses this read-only, page-local boundary instead of DSH's remote history or registries.
let snapshot=null;
export function bindContextSnapshot(value){snapshot=value;}
export function useHistoryFace(){return snapshot;}
export function makeHeaderFetcher(){const value=snapshot;return async seq=>value?.headerContent.get(seq)??null;}
export function makeContentFetcher(){const value=snapshot;return async seq=>value?.conversationNodes.find(n=>n.seq===seq)??null;}
export function useModelPrices(){return {book:null,failed:true};}
