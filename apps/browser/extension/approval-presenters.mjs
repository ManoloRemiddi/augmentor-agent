// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

/** The native bridge is one host presenter; only one live Browser document may show its request. */
export class ApprovalPresenters {
  documents=new Map()
  claims=new Map()
  connect(port){
    const sender=port.sender
    if(port.name!=='augmentor-approval-presenter'||!sender?.documentId||!sender.url?.startsWith(chrome.runtime.getURL(''))){port.disconnect();return}
    const documentId=sender.documentId
    if(this.documents.has(documentId)){port.disconnect();return}
    this.documents.set(documentId,port)
    port.onDisconnect.addListener(()=>{
      if(this.documents.get(documentId)!==port)return
      this.documents.delete(documentId)
      for(const [id,owner] of this.claims)if(owner===documentId)this.claims.delete(id)
    })
  }
  claim(id,sender){
    const owner=sender?.documentId
    if(!owner||!this.documents.has(owner))return false
    if(this.claims.has(id))return this.claims.get(id)===owner
    if(this.claims.size>=128)return false
    this.claims.set(id,owner);return true
  }
  owns(id,sender){return !!sender?.documentId&&this.documents.has(sender.documentId)&&this.claims.get(id)===sender.documentId}
  resolve(id){this.claims.delete(id)}
  clear(){this.claims.clear()}
}
export const approvalPresenters=new ApprovalPresenters()
