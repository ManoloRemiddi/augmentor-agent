// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// An isolated research browser cannot verify actions in the user's Chromium.
export function applyBrowserPolicy(ctx) {
  const failed = new Set()
  const unreadable = new Set()
  const recovery = 'The page has not been observed. Confirm the intended tab and URL with browser_tabs_list. Use browser_screenshot if available, or an available consented desktop screenshot. Do not repeat identical empty reads, guess settings routes or layout, or click the body to extract text. If capture is unavailable, report the actual capability failure and ask only for the missing observation. Never say you can see the page without evidence.'
  const isolated = name => name.startsWith('mcp__playwright__browser_')
  const explanation = 'Playwright controls a separate browser, not the user\'s visible Chromium or its tabs. Its page content and screenshots are research evidence only. To open a page for the user, use browser_navigate and verify with browser_tabs_list/browser_snapshot. A shell launch alone does not confirm the visible page.'
  ctx.tools.guard(exec => {
    if (unreadable.has(exec.agent?.id) && ['browser_click', 'browser_type'].includes(exec.name)) return 'A fresh readable snapshot or screenshot is required before acting on an unobserved page. ' + recovery
    if (isolated(exec.name) && failed.has(exec.agent?.id)) return 'Real-browser navigation failed. Do not substitute an isolated Playwright browser for the requested Chromium action. Reconnect the Augmentor extension or report the connection failure. ' + explanation
  })
  ctx.on('tools/post-execute', async (exec, result, next) => {
    const decision = await next()
    if (decision.kind === 'block') return decision
    if (exec.name === 'browser_snapshot') {
      const text = (decision.content ?? result.content ?? []).filter(item => item.type === 'text').map(item => item.text).join('\n')
      const body = text.replace(/^Page:.*$/m, '').replace(/^URL:.*$/m, '').replace(/Observed controls[^\n]*:?\n?/g, '').trim()
      if (result.isError || result.value?.ok === false || !body || /\(no visible text\)|snapshot failed:|Observation is inconclusive|No document observation returned/.test(body)) {
        unreadable.add(exec.agent?.id)
        return {...decision, kind: 'accept', content: [...(decision.content ?? result.content ?? []), {type: 'text', text: recovery}]}
      }
      unreadable.delete(exec.agent?.id)
    }
    if (['browser_screenshot', 'linux_desktop_snapshot'].includes(exec.name) && !result.isError && (decision.content ?? result.content ?? []).some(item => item.type === 'image')) unreadable.delete(exec.agent?.id)
    if (exec.name === 'browser_navigate') {
      const text = result.content.filter(item => item.type === 'text').map(item => item.text).join('\n')
      if (result.isError || result.value?.ok === false || /(?:navigate|navigation) failed|no browser client connected/i.test(text)) {
        failed.add(exec.agent?.id)
        return {kind: 'block', feedback: [{type: 'text', text: text + '\nNo visible Chromium navigation was verified. ' + explanation}]}
      }
      failed.delete(exec.agent?.id)
    }
    if (isolated(exec.name)) return {kind: 'accept', content: [{type: 'text', text: explanation}, ...(decision.content ?? result.content)], ...(decision.additionalContexts ? {additionalContexts: decision.additionalContexts} : {})}
    return decision
  })
  ctx.on('agent/status', ({agent, status}) => { if (status === 'idle') { failed.delete(agent.id); unreadable.delete(agent.id) } })
  ctx.on('dispose', () => { failed.clear(); unreadable.clear() })
}
