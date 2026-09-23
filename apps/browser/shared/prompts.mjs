// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

import {promptCall} from '../../../dist/prompt-library/src/client.js'

export async function promptLibrary(request = {}, call = promptCall) {
  const action=request.action??'list'
  if(!['list','save','delete','improvement.save'].includes(action))return {ok:false,error:'Unsupported prompt action'}
  try {
    const {action:_,...params}=request
    return {ok:true,library:await call('prompts.'+action,params)}
  } catch(error) {return {ok:false,error:error.message}}
}
