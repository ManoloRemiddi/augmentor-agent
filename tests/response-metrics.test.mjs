// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {extractMetric} from '../adapters/dsh-response-metrics/index.mjs'
test('shared response metrics identify the measured response and require usable timing',()=>{
 const event={type:'assistant/message',seq:8,data:{turn:2,step:0,message:{content:[{type:'text',text:'Synthetic answer'}],source:{provider:'fixture',model:'fixture'}},usage:{outputTokens:100},stream:[{time:1000},{time:3000}]}}
 assert.deepEqual(extractMetric(event),{seq:8,turn:2,step:0,responsePreview:'Synthetic answer',outputTokens:100,streamDurationMs:2000,observedTokensPerSecond:50,provider:'fixture',model:'fixture'})
 for(const data of [{...event.data,stream:[]},{...event.data,usage:{}},{...event.data,message:{content:[]}}])assert.equal(extractMetric({...event,data}),null)
})
