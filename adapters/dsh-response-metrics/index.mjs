// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: MIT
import { readFileSync, mkdirSync, writeFileSync, renameSync } from 'node:fs'
import { join } from 'node:path'
import { homedir } from 'node:os'
import { createHash } from 'node:crypto'
export function extractMetric(event) {
  if (event.type !== 'assistant/message') return null
  const d = event.data
  if (!d?.message?.content?.some(b => b.type === 'text' && b.text?.trim())) return null
  const times = (d.stream ?? []).map(x => x.time ?? x.time0).filter(Number.isFinite)
  const tokens = d.usage?.outputTokens
  if (!Number.isFinite(tokens) || tokens < 0 || times.length < 2) return null
  const milliseconds = Math.max(...times) - Math.min(...times)
  if (milliseconds <= 0) return null
  return {responsePreview:d.message.content.filter(b=>b.type==='text').map(b=>b.text).join(' ').slice(0,160), seq:event.seq, turn:d.turn, step:d.step, outputTokens:tokens, streamDurationMs:milliseconds,
    observedTokensPerSecond:Math.round(tokens*100000/milliseconds)/100,
    provider:d.message.source?.provider, model:d.message.source?.model}
}
export function registerMetrics(ctx) {
  const folder = join(process.env.DSH_HOME || join(homedir(), '.dsh'), 'local', 'response-metrics')
  const path = session => join(folder, createHash('sha256').update(session.id).digest('hex')+'.json')
  const read = session => { try { return JSON.parse(readFileSync(path(session), 'utf8')) } catch { return [] } }
  ctx.on('session/event', (session, event) => {
    const metric = extractMetric(event)
    if (!metric || !session.id) return
    try {
    const records = read(session).filter(x=>x.seq!==metric.seq)
    records.push(metric)
    mkdirSync(folder,{recursive:true,mode:0o700})
    const dest=path(session), temp=dest+'.tmp'
    writeFileSync(temp,JSON.stringify(records.slice(-20)),{mode:0o600});renameSync(temp,dest)
    } catch { /* Optional timing data must not terminate a conversation. */ }
  })
  ctx.tools.register({name:'response_metrics',
    description:'Read recorded timing and output-token counts for up to 20 recent text responses in THIS session. Use for questions about your own TPS. A short response excerpt identifies the measured reply; stream rate is an observed estimate, not server-only decode TPS. Missing records mean unavailable, not never recorded elsewhere.',
    parameters:{type:'object',additionalProperties:false,properties:{}},
    output:{schema:{type:'string'},render:(_args,value)=>[{type:'text',text:value}]},
    execute(_args,exec){return JSON.stringify({source:'DSH saved response stream timestamps',measurement:'output tokens divided by first-stream-event to finish duration; includes tool-call tokens in mixed replies; not server-only decode timing',responses:read(exec.agent.session)})}
  })
}

export const name = "augmentor-response-metrics"
export const inject = ["tools"]
export const apply = registerMetrics
