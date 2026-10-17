/**
 * Vault-aware search: the wiki-query skill's read order (hot cache, master
 * index, then pages) as one tool-call, plus full-text search with the link
 * graph that makes wiki retrieval different from grep.
 *
 * @module dsh-plugin-wiki-tools/lib/search
 */

import { readFile } from 'node:fs/promises'
import { join } from 'node:path'
import { buildAliasMap, collectMarkdown, isMachineryPage, resolveLinkTarget } from './vault.js'
import { buildIndex, rank } from './bm25.js'

/**
 * Answer the quick mode: the hot cache and master index verbatim. The caller
 * (the model, following the wiki-query skill) reads these before any page.
 * @param {string} root - absolute vault root.
 * @returns {Promise<{ hot: string | undefined, index: string | undefined }>}
 */
export async function quickView(root) {
  const [hot, index] = await Promise.all([
    readFile(join(root, 'wiki', 'hot.md'), 'utf8').catch(() => undefined),
    readFile(join(root, 'wiki', 'index.md'), 'utf8').catch(() => undefined),
  ])
  return { hot, index }
}

/**
 * Full-text search over the wiki tree with link-graph context. BM25 ranks
 * term overlap (latin words; CJK unigram/bigram) at two granularities: whole
 * pages for the ranking core, and heading/paragraph chunks (the wiki-retrieve
 * design) so each hit's snippet is its best-matching passage. Substring
 * bonuses keep exact title/alias/tag phrases and partial words ahead, and a
 * substring-only hit still surfaces when tokenization misses it.
 * @param {string} root - absolute vault root.
 * @param {object} options - search options.
 * @param {string} options.query - the search text.
 * @param {number} [options.limit=10] - maximum results.
 * @returns {Promise<{ results: { name: string, path: string, score: number, snippets: string[], inbound: string[], outbound: number }[], totalMatches: number }>}
 */
export async function searchVault(root, { query, limit = 10 }) {
  const needle = query.trim().toLowerCase()
  if (needle.length === 0) throw new Error('wiki-tools: query must be a non-empty string')
  const pages = await collectMarkdown(join(root, 'wiki'))
  // The link graph covers every file, but results exclude vault machinery:
  // the index matches nearly every term by construction and is already the
  // quick-mode payload, and dated lint reports quote past wikilinks as records,
  // not graph edges — so they neither appear as hits nor count as inbound.
  const searchable = pages.filter(page => !isMachineryPage(page.name))
  const names = new Set(pages.map(page => page.name))
  const aliases = buildAliasMap(pages)
  const inbound = new Map(pages.map(page => [page.name, []]))
  for (const page of searchable) {
    // One inbound record per source page, however many times it links; alias
    // targets resolve to their owning page.
    for (const target of new Set(page.links)) {
      const resolved = resolveLinkTarget(target, names, aliases)
      if (resolved !== undefined) inbound.get(resolved)?.push(page.name)
    }
  }
  const documents = new Map(searchable.map(page => [
    page.name,
    `${page.name} ${(page.aliases ?? []).join(' ')} ${tagsOf(page)} ${page.content}`,
  ]))
  const bm25Scores = rank(buildIndex(documents), query)

  const chunksByPage = new Map(searchable.map(page => [page.name, chunkPage(page.content)]))
  const chunkDocs = new Map()
  for (const [name, chunks] of chunksByPage) {
    chunks.forEach((chunk, index) => chunkDocs.set(`${name}\u0000${index}`, chunk))
  }
  /** Best chunk (index + score) per page from chunk-level BM25. */
  const bestChunk = new Map()
  for (const [key, score] of rank(buildIndex(chunkDocs), query)) {
    const name = key.slice(0, key.indexOf('\u0000'))
    if (score > (bestChunk.get(name)?.score ?? 0)) {
      bestChunk.set(name, { score, index: Number(key.slice(key.indexOf('\u0000') + 1)) })
    }
  }

  const results = []
  let totalMatches = 0
  for (const page of searchable) {
    const bm25 = bm25Scores.get(page.name) ?? 0
    const chunk = bestChunk.get(page.name)
    const titleHit = page.name.toLowerCase().includes(needle)
      || (page.aliases ?? []).some(alias => alias.toLowerCase().includes(needle))
    const tagHit = tagsOf(page).includes(needle)
    const bodyHit = page.content.toLowerCase().includes(needle)
    if (bm25 === 0 && chunk === undefined && !titleHit && !tagHit && !bodyHit) continue
    totalMatches += 1
    const score = bm25 + (chunk?.score ?? 0) + (titleHit ? 5 : 0) + (tagHit ? 4 : 0) + (bodyHit ? 1 : 0)
    const chunks = chunksByPage.get(page.name) ?? []
    const snippetChunk = chunk !== undefined ? chunks[chunk.index] : undefined
    const snippets = snippetChunk !== undefined && snippetChunk.trim().length > 0
      ? [trimForSnippet(snippetChunk)]
      : matchLines(page.content, needle).slice(0, 2)
    results.push({
      name: page.name,
      path: page.path,
      score: Math.round(score * 100) / 100,
      snippets,
      inbound: inbound.get(page.name) ?? [],
      outbound: new Set(page.links).size,
    })
  }
  results.sort((left, right) => right.score - left.score || left.name.localeCompare(right.name))
  return { results: results.slice(0, limit), totalMatches: results.length }
}

/**
 * Split a page body into retrieval chunks: blocks separated by blank lines,
 * accumulated up to ~800 characters per chunk without splitting a block.
 * @param {string} content - page body.
 * @returns {string[]} non-empty chunks.
 */
function chunkPage(content) {
  const chunks = []
  let current = ''
  for (const block of content.split(/\n\s*\n/)) {
    const trimmed = block.trim()
    if (trimmed.length === 0) continue
    if (current.length === 0) {
      current = trimmed
    } else if (current.length + trimmed.length + 2 <= 800) {
      current += `\n\n${trimmed}`
    } else {
      chunks.push(current)
      current = trimmed
    }
  }
  if (current.length > 0) chunks.push(current)
  return chunks
}

/**
 * Trim one chunk for snippet display, cutting at a word boundary.
 * @param {string} chunk - the chunk text.
 * @returns {string} at most ~300 characters with an ellipsis marker.
 */
function trimForSnippet(chunk) {
  const text = chunk.replace(/\n+/g, ' ').trim()
  if (text.length <= 300) return text
  const cut = text.slice(0, 300)
  const lastSpace = cut.lastIndexOf(' ')
  return `${cut.slice(0, lastSpace > 200 ? lastSpace : 300)}...`
}

/**
 * Case-insensitive matching lines, trimmed for a result snippet.
 * @param {string} content - page body.
 * @param {string} needle - lowercased search text.
 * @returns {string[]} up to 4 matching lines trimmed to 160 characters.
 */
function matchLines(content, needle) {
  const lines = []
  for (const line of content.split('\n')) {
    if (line.toLowerCase().includes(needle)) {
      const trimmed = line.trim()
      lines.push(trimmed.length > 160 ? `${trimmed.slice(0, 157)}...` : trimmed)
      if (lines.length === 4) break
    }
  }
  return lines
}

/**
 * A page's tags as one lowercase string for matching.
 * @param {{ fields?: Record<string, unknown> }} page - collected page.
 * @returns {string} space-joined tags.
 */
function tagsOf(page) {
  return Array.isArray(page.fields?.tags) ? page.fields.tags.join(' ').toLowerCase() : ''
}
