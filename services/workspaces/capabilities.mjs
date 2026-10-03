// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {SDK_PROTOCOL, validatePolicy, voiceEnabled} from './policy.mjs'
import {PRODUCT_PROTOCOL} from '../../dist/contracts/src/index.js'
import {RELEASE} from '../../dist/contracts/src/release.js'
import {desktopCapabilities} from '../../dist/desktop/src/capabilities.js'
import {definitions} from '../../dist/desktop/src/index.js'

/** A workspace's integration/permission snapshot. Never starts a companion or probes audio. */
export function describeWorkspace(profile,{platform=process.platform,desktop=desktopCapabilities()}={}){
 validatePolicy(profile)
 const enabled=voiceEnabled(profile),granted=profile.policy.tools
 const desktopNames=new Set(definitions.map(tool=>tool.name))
 const computerTools=granted.filter(name=>desktopNames.has(name))
 const supported={state:'supported',scope:'workspace'}
 return {protocol:SDK_PROTOCOL,profile:profile.id,harness:profile.harness??'dsh',productProtocol:PRODUCT_PROTOCOL,
  productVersion:RELEASE.version,tools:granted,voice:{experimental:true,enabled},
  platform,capabilitySchema:1,readinessVerified:false,
  features:{
   embed:{...supported},'scoped-sessions':{...supported},'tool-policy':{...supported},
   'workspace-memory':{...supported},'background-client':{...supported},
   voice:{state:enabled?'supported':'disabled',scope:'workspace',experimental:true,providers:['resonant-voice']},
   'dictation-settings':{state:'denied',scope:'installation',managedIn:'standalone'},
   'shared-settings':{state:'denied',scope:'installation'},
   'computer-use':{state:!desktop.available?'unsupported':computerTools.length?'supported':'denied',
    scope:'workspace',tools:computerTools,experimental:true,requiresUserConsent:true,requiresImageModel:true}
  }}
}
