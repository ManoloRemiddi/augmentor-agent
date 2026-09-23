// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Carried forward from the working native Linux integration.
import {spawn} from "node:child_process"
import {fileURLToPath} from "node:url"
const backend=fileURLToPath(new URL("../../services/desktop/linux-support/desktop.py",import.meta.url))
export function runDesktop(request, signal) {
  return new Promise((resolve, reject) => {
    const child = spawn('/usr/bin/python3', [backend], {stdio: ['pipe', 'pipe', 'pipe'], signal})
    let out = '', error = '', settled = false
    const finish = (err, value) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      err ? reject(err) : resolve(value)
    }
    const timer = setTimeout(() => { child.kill(); finish(new Error('Desktop operation timed out')) }, 12000)
    child.stdout.on('data', data => { out += data; if (out.length > 256000) {child.kill(); finish(new Error('Desktop result exceeded limit'))} })
    child.stderr.on('data', data => { error = (error + data).slice(-1000) })
    child.on('error', err => finish(err))
    child.on('close', code => {
      if (code !== 0) return finish(new Error('Desktop backend failed'))
      try { finish(null, JSON.parse(out)) } catch { finish(new Error('Invalid desktop response')) }
    })
    child.stdin.on('error', () => {})
    child.stdin.end(JSON.stringify(request))
  })
}

export function applyLinuxSupport(ctx){
  if(process.platform!=="linux")return
  ctx.tools.register({
    name: 'linux_system_profile',
    description: 'Inspect the actual MX/Linux distribution, desktop, session and tool availability. Read-only; does not inspect app contents.',
    parameters: {type: 'object', properties: {}, additionalProperties: false},
    output: {schema: {type: 'string'}, render: (_args, value) => [{type: 'text', text: value}]},
    async execute(_args, exec) { return JSON.stringify(await runDesktop({action: 'profile'}, exec.signal)) },
  })
  ctx.tools.register({
    name: 'linux_browser_open',
    description: 'Open an HTTP(S) URL in a NEW visible tab of the installed Chromium, using the user\'s existing desktop and browser profile. Use this when the user asks to use Chromium or open a new tab; a site search URL such as https://www.amazon.it/s?k=RTX+5090 performs the search visibly. Independent of the browser extension. Never uses headless Playwright. Returns dispatch status, not proof of page loading: verify the URL/title with browser_tabs_list or inspect Chromium with linux_desktop_observe. Do not repeat an accepted launch just because verification is unavailable.',
    parameters: {type: 'object', properties: {url: {type: 'string', description: 'Full HTTP(S) URL to open in a new Chromium tab.'}}, required: ['url'], additionalProperties: false},
    output: {schema: {type: 'string'}, render: (_args, value) => [{type: 'text', text: value}]},
    async execute(args, exec) {
      if (exec.signal.aborted) throw new Error('cancelled')
      if (!args || typeof args.url !== 'string' || Object.keys(args).some(key => key !== 'url')) throw new Error('linux_browser_open requires {url: "https://..."}')
      return JSON.stringify(await runDesktop({action: 'browser_open', url: args.url}, exec.signal))
    },
  })
  ctx.tools.register({
    name: 'linux_desktop_observe',
    description: 'List accessible Linux applications. Pass an application PID from that list to inspect a bounded tree of its controls. Read-only. Accessibility coverage varies by app.',
    parameters: {type: 'object', properties: {appPid: {type: 'integer', minimum: 1, description: 'PID from the application list; omit to list applications.'}}, additionalProperties: false},
    output: {schema: {type: 'string'}, render: (_args, value) => [{type: 'text', text: value}]},
    async execute(args, exec) {
      if (!args || Object.keys(args).some(key => key !== 'appPid')) throw new Error('Use appPid (camelCase), or omit it to list applications.')
      return JSON.stringify(await runDesktop({action: 'observe', appPid: args.appPid}, exec.signal))
    },
  })
}
