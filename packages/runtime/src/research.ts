// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import { isNonPublicIpLiteral } from '../vendor/dsh-keyless-fetch/network.js';
export interface ResearchOptions {
    depth?: 'basic' | 'advanced';
    max_results?: number;
    include_domains?: string[];
    exclude_domains?: string[];
    time_range?: 'day' | 'week' | 'month' | 'year';
    topic?: 'general' | 'news';
}
const messages: Record<string, string> = { WEB_AUTH_REQUIRED: 'Tavily needs a valid API key in private Search settings.', WEB_QUOTA: 'Tavily usage limit reached. Check the free-credit balance; no paid plan was activated.', WEB_RATE_LIMIT: 'Tavily is rate limited. Wait before trying again.', WEB_NO_RESULTS: 'No usable sources returned. Rephrase the query or choose another configured provider.', WEB_EXTRACTION_EMPTY: 'The page could not be extracted. It has not been read.', WEB_TIMEOUT: 'Research request timed out.', WEB_INVALID_RESPONSE: 'Invalid research provider response.', WEB_BLOCKED_URL: 'Research requires a public HTTP(S) URL without credentials.', WEB_PROVIDER_ERROR: 'Research provider unavailable. Try again later.', WEB_RESPONSE_LIMIT: 'Research response exceeded its size limit.', WEB_FETCH_DISABLED: 'Page fetching is disabled.' };
export class ResearchError extends Error {
    constructor(readonly code: string, readonly status?: number) { super(messages[code] ?? messages.WEB_PROVIDER_ERROR); }
}
export function researchUrl(value: string) { let u: URL; try {
    u = new URL(value);
}
catch {
    throw new ResearchError('WEB_BLOCKED_URL');
} const h = u.hostname.toLowerCase().replace(/^\[|\]$/g, '').replace(/\.$/, ''); if (!['http:', 'https:'].includes(u.protocol) || u.username || u.password || h === 'localhost' || ['.localhost', '.local', '.internal', '.home.arpa'].some(s => h.endsWith(s)) || isNonPublicIpLiteral(h))
    throw new ResearchError('WEB_BLOCKED_URL'); return u.href; }
const domains = (v: unknown): string[] => { if (v === undefined)
    return []; if (!Array.isArray(v) || v.length > 30 || v.some(x => typeof x !== 'string' || x.length > 253 || !/^([a-z0-9](?:[a-z0-9.-]*[a-z0-9])?)$/i.test(x) || x.includes('..')))
    throw Error('Use up to 30 domain names without URL paths.'); return [...new Set(v.map(x => x.toLowerCase()))]; };
export function researchOptions(v: ResearchOptions = {}): ResearchOptions { if (Object.keys(v).some(k => !['depth', 'max_results', 'include_domains', 'exclude_domains', 'time_range', 'topic'].includes(k)) || v.depth !== undefined && !['basic', 'advanced'].includes(v.depth) || v.topic !== undefined && !['general', 'news'].includes(v.topic) || v.time_range !== undefined && !['day', 'week', 'month', 'year'].includes(v.time_range) || v.max_results !== undefined && (!Number.isInteger(v.max_results) || v.max_results < 1 || v.max_results > 10))
    throw Error('Invalid research controls.'); return { ...v, depth: v.depth ?? 'basic', max_results: v.max_results ?? 5, include_domains: domains(v.include_domains), exclude_domains: domains(v.exclude_domains) }; }
const matches = (h: string, list: string[]) => list.some(d => h === d || h.endsWith('.' + d));
/** Official API, bounded reads, no external answer generation or implicit paid fallback. */
export class TavilyResearch {
    constructor(private key: () => string, private transport: typeof globalThis.fetch = globalThis.fetch) { }
    private async request(endpoint: 'search' | 'extract', body: unknown, signal?: AbortSignal): Promise<any> {
        const key = this.key().trim();
        if (!key)
            throw new ResearchError('WEB_AUTH_REQUIRED');
        const joined = AbortSignal.any([...(signal ? [signal] : []), AbortSignal.timeout(20000)]);
        try {
            const r = await this.transport('https://api.tavily.com/' + endpoint, { method: 'POST', headers: { 'content-type': 'application/json', authorization: 'Bearer ' + key }, body: JSON.stringify(body), signal: joined, redirect: 'error' });
            if (!r.ok) {
                await r.body?.cancel();
                throw new ResearchError([401, 403].includes(r.status) ? 'WEB_AUTH_REQUIRED' : r.status === 429 ? 'WEB_RATE_LIMIT' : [402, 432, 433].includes(r.status) ? 'WEB_QUOTA' : 'WEB_PROVIDER_ERROR', r.status);
            }
            const reader = r.body?.getReader(), chunks: Uint8Array[] = [];
            let size = 0;
            try {
                if (reader)
                    for (;;) {
                        joined.throwIfAborted();
                        const n = await reader.read();
                        if (n.done)
                            break;
                        size += n.value.byteLength;
                        if (size > 8 * 1024 * 1024)
                            throw new ResearchError('WEB_RESPONSE_LIMIT');
                        chunks.push(n.value);
                    }
            }
            finally {
                await reader?.cancel().catch(() => { });
            }
            let data;
            try {
                data = JSON.parse(Buffer.concat(chunks, size).toString('utf8'));
            }
            catch {
                throw new ResearchError('WEB_INVALID_RESPONSE');
            }
            if (!data || typeof data !== 'object' || Array.isArray(data))
                throw new ResearchError('WEB_INVALID_RESPONSE');
            return data;
        }
        catch (e) {
            if (signal?.aborted)
                throw signal.reason;
            if (e instanceof ResearchError)
                throw e;
            throw new ResearchError(joined.aborted ? 'WEB_TIMEOUT' : 'WEB_PROVIDER_ERROR');
        }
    }
    async search(query: string, options: ResearchOptions = {}, signal?: AbortSignal) { const o = researchOptions(options), data = await this.request('search', { query, search_depth: o.depth, max_results: o.max_results, include_domains: o.include_domains, exclude_domains: o.exclude_domains, ...(o.time_range ? { time_range: o.time_range } : {}), topic: o.topic ?? 'general', include_answer: false, include_raw_content: false, include_usage: true }, signal), seen = new Set<string>(); const sources = (Array.isArray(data.results) ? data.results : []).flatMap((r: any) => { try {
        const url = researchUrl(r.url), host = new URL(url).hostname.toLowerCase();
        if (seen.has(url) || o.include_domains!.length && !matches(host, o.include_domains!) || matches(host, o.exclude_domains!))
            return [];
        seen.add(url);
        return [{ url, title: typeof r.title === 'string' ? r.title : '', snippet: typeof r.content === 'string' ? r.content : '', ...(typeof r.published_date === 'string' ? { publishedAt: r.published_date } : {}) }];
    }
    catch {
        return [];
    } }).slice(0, o.max_results); if (!sources.length)
        throw new ResearchError('WEB_NO_RESULTS'); return { query, sources, truncated: false, provider: 'tavily', controls: o, ...(typeof data.usage?.credits === 'number' ? { credits: data.usage.credits } : {}) }; }
    async fetch(url: string, signal?: AbortSignal) { const requested = researchUrl(url), data = await this.request('extract', { urls: [requested], extract_depth: 'basic', format: 'markdown', include_images: false, include_usage: true }, signal); const r = Array.isArray(data.results) ? data.results.find((r: any) => { try {
        return researchUrl(r.url) === requested;
    }
    catch {
        return false;
    } }) : undefined; if (!r || typeof r.raw_content !== 'string' || !r.raw_content.trim() || /^\s*(?:no (?:content|results) found\.?|access denied|forbidden)\s*$/i.test(r.raw_content))
        throw new ResearchError('WEB_EXTRACTION_EMPTY'); return { url: requested, content: r.raw_content.slice(0, 100000), truncated: r.raw_content.length > 100000, provider: 'tavily', format: 'markdown', ...(typeof data.usage?.credits === 'number' ? { credits: data.usage.credits } : {}) }; }
}
