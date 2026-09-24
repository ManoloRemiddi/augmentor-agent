// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Agent-scoped execution boundary, independent of model or role instructions.
import {applyBrowserPolicy} from '../dsh-desktop/browser-policy.mjs'
export const name='augmentor-browser-policy'
export const inject=['tools']
const allowed=new Set(['browser_tabs_list','browser_screenshot','browser_snapshot','browser_navigate','browser_click','browser_type','memory_recall','memory_source','home_read','home_status','home_request','home_result','home_cancel'])
export function apply(ctx){
  applyBrowserPolicy(ctx)
  ctx.tools.guard(exec=>allowed.has(exec.name)?undefined:'This Augmentor browser chat can only use browser tools, paired Home capabilities and shared memory recall.')
}
