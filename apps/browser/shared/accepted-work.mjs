// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Count accepted operations through response delivery. Closing admission never
// aborts them or turns an unknown result into permission to replay it.
export class AcceptedWork {
  constructor(){this.pending=new Set();this.closing=false}
  run(operation){
    if(this.closing)return Promise.reject(Error('The browser connection is closing. This request was not started.'))
    const task=Promise.resolve().then(operation).finally(()=>this.pending.delete(task))
    this.pending.add(task);return task
  }
  close(){this.closing=true}
  async drained(){while(this.pending.size)await Promise.allSettled([...this.pending])}
}
