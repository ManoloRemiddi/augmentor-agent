// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import Schema from '@deepseek-ai/schemastery';
import { constants, lstatSync, openSync, fstatSync, readFileSync, closeSync, realpathSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { TavilyResearch, ResearchError } from '../../dist/runtime/src/research.js';
export const name = 'augmentor-research';
export const inject = ['web'];
export const Config = Schema.object({ searchFile: Schema.string().description('Private AH Search settings file containing the Tavily key; never enter the key in this path.').volatile() });
const current = v => v && typeof v.get === 'function' ? v.get() : v;
/** A private, explicitly selected credential file; never follows a link or prints its contents. */
export function readKey(file) {
    const parent = dirname(file), dir = lstatSync(parent);
    if (!dir.isDirectory() || dir.uid !== process.getuid() || dir.mode & 0o077 || realpathSync(parent) !== resolve(parent))
        throw new ResearchError('WEB_AUTH_REQUIRED');
    const st = lstatSync(file);
    if (!st.isFile() || st.isSymbolicLink() || st.nlink !== 1 || st.uid !== process.getuid() || st.mode & 0o077 || st.size > 768 * 1024)
        throw new ResearchError('WEB_AUTH_REQUIRED');
    const fd = openSync(file, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
    try {
        const s = fstatSync(fd);
        if (!s.isFile() || s.ino !== st.ino || s.dev !== st.dev || s.size > 768 * 1024)
            throw new ResearchError('WEB_AUTH_REQUIRED');
        const j = JSON.parse(readFileSync(fd, 'utf8'));
        if (j.schema !== 'augmentor-free-search/1')
            throw new ResearchError('WEB_AUTH_REQUIRED');
        return typeof j.config?.tavilyApiKey === 'string' ? j.config.tavilyApiKey.split(/\r?\n/).map(x => x.trim()).find(Boolean) ?? '' : '';
    }
    finally {
        closeSync(fd);
    }
}
export function apply(ctx, config) {
    const key = () => { try {
        return readKey(current(config.searchFile));
    }
    catch {
        throw new ResearchError('WEB_AUTH_REQUIRED');
    } };
    const client = new TavilyResearch(key);
    const available = () => { try {
        return !!key();
    }
    catch {
        return false;
    } };
    const register = () => { const searchDispose = ctx.web.registerSearchProvider({ id: name, available, search: async (request, signal) => client.search(request.query, {}, signal) }); let fetchDispose; try {
        fetchDispose = ctx.web.registerFetchProvider({ id: name, available, fetch: async (request, signal) => {
            const result = await client.fetch(request.url, signal);
            // DSH's fetch seam requires a text body and a numeric status. This is
            // a successful extraction service response, not a measured origin status.
            return { url: result.url, statusCode: 200, body: { kind: 'text', content: 'Tavily extraction succeeded (service HTTP 200; origin HTTP status is not reported).\n\n' + result.content }, truncated: result.truncated };
        } });
    }
    catch (e) {
        searchDispose?.();
        throw e;
    } return () => { fetchDispose?.(); searchDispose?.(); }; };
    ctx.effect ? ctx.effect(register) : register();
}
