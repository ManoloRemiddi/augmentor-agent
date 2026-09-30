// Augmentor — Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

const key='augmentor-codex-pending-branch'
export async function prepareBranch(storage,desired){
  if(!Number.isSafeInteger(desired.messageSeq)||desired.messageSeq<1||!['reply','edit'].includes(desired.mode))throw Error('Select a committed message to branch.')
  const pending=(await storage.get(key))[key]
  if(pending){
    if(['sessionId','messageSeq','mode'].some(field=>pending[field]!==desired[field]))throw Error('A previous branch is not confirmed. Retry its original message action before creating another branch.')
    return pending
  }
  await storage.set({[key]:desired})
  return desired
}
export async function finishBranch(storage,request,records={}){
  const pending=(await storage.get(key))[key]
  if(pending?.newSessionId!==request.newSessionId)throw Error('The pending branch identity changed.')
  // Persist the selected child and removal of pending intent together.
  await storage.set({...records,[key]:null})
}
