// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {preferences} from './profiles.mjs'
export const SDK_PROTOCOL='augmentor-app/1'
export function validatePolicy(profile){
 if(profile.sdkProtocol!==SDK_PROTOCOL)throw Error('Unsupported application SDK protocol')
 const p=profile.policy
 if(!p||!Array.isArray(p.tools)||p.tools.length>200||p.tools.some(n=>typeof n!=='string'||!/^[A-Za-z][A-Za-z0-9_]{0,127}$/.test(n))||typeof p.voice!=='boolean'||p.sharedSettings!==false)throw Error('SDK profiles require explicit tool, voice and shared-settings policy')
 return p
}
export function voiceEnabled(profile){return profile?.sdkProtocol===SDK_PROTOCOL?(preferences(profile)['experimental-voice-enabled']??profile.policy.voice)===true:true}
export function guardWorkspaceMethod(profile,method,params={}){
 if(profile?.sdkProtocol!==SDK_PROTOCOL)return
 validatePolicy(profile)
 if(['augmentor/dsh','augmentor/onboarding','augmentor/diagnostics','augmentor/home','augmentor/surface','updates/check','settings.mutate'].includes(method))throw Error('This application cannot administer the shared Augmentor installation')
 if(method==='augmentor/prompts'&&!['list','get','describe'].includes(params.action||'list'))throw Error('Shared prompt changes are unavailable in application workspaces')
 if(method.startsWith('augmentor/voice')&&!['augmentor/voice/preferences','augmentor/voice/control'].includes(method)&&!voiceEnabled(profile))throw Error('Experimental voice is disabled for this workspace')
 if(method==='augmentor/voice/preferences'&&params.action&&params.action!=='get')throw Error('Shared voice configuration is managed in standalone Augmentor')
}
