// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** UI-only bridge for the original plugin dialog. Never dispatches a Host action. */
export class DshContextModalBinding {
  constructor({current,storeOf,setPending,takePending}){Object.assign(this,{current,storeOf,setPending,takePending});this.pending=null;}
  valid(scope){const now=this.current();return now.phase==='ready'&&!now.readOnly&&!now.unconfirmed&&!now.interactions?.length&&typeof scope?.sessionId==='string'&&scope.sessionId!==''&&scope.sessionId===now.sessionId&&scope.epoch===now.epoch;}
  open(scope,segment,consume){
    if(!this.valid(scope))return false;
    this.invalidate();
    const guard=segment.via==='enter'?{kind:'bare-token',token:segment.token}:{kind:'span',span:segment.span};
    this.pending={scope:{...scope},guard,consume};this.setPending(scope.sessionId,guard);this.storeOf(scope.sessionId).set(true);return true;
  }
  invalidate(){const pending=this.pending;if(!pending)return;this.pending=null;this.takePending(pending.scope.sessionId);this.storeOf(pending.scope.sessionId).set(false);}
  sync(){if(this.pending&&!this.valid(this.pending.scope))this.invalidate();}
  /** The supplier close path receives only this local, fenced token-consume seat. */
  scope(sessionId){
    const pending=this.pending;if(!pending||pending.scope.sessionId!==sessionId||!this.valid(pending.scope))return undefined;
    const scope={bail:(seat,event,data)=>{
      if(seat!==scope||event!=='slash/input-consume-token'||data?.guard!==pending.guard||this.pending!==pending||!this.valid(pending.scope))return false;
      this.pending=null;return pending.consume();
    }};return scope;
  }
}
