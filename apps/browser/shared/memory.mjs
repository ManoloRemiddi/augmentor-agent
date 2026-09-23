// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import {promptCall} from '../../../dist/prompt-library/src/client.js'
const actions=new Set(['dual.describe','dual.configure','dual.recall','describe','check','configure','disable','recall','retain','operations','operation','documents','document','delete','exportPage'])
export async function memoryRequest(request={}){
  const {action='describe',requestId,...params}=request
  if(!actions.has(action))throw new Error('Unsupported memory action')
  return promptCall('memory.'+action,params,requestId)
}
