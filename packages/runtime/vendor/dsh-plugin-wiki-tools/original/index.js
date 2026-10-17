/**
 * Wiki Tools — native DeepSeek Harness tools over an Obsidian wiki vault.
 *
 * Registers `wiki_query`, `wiki_write`, and `wiki_lint` on `ctx.tools`,
 * implementing the mechanical core of the wiki skill suite (path routing,
 * frontmatter completion, index/log bookkeeping, source delta tracking, and
 * health checks) so the model spends its turns on synthesis instead of
 * filesystem chores. Vault design follows the LLM Wiki pattern; see
 * dsh-plugin-wiki-skills for the skill half.
 *
 * @module dsh-plugin-wiki-tools
 */

import { existsSync } from 'node:fs'
import { join } from 'node:path'
import { defineTool } from '@deepseek-ai/dsh-tools'
import z from '@deepseek-ai/schemastery'
import { Vault } from './lib/vault.js'
import { quickView, searchVault } from './lib/search.js'
import { lintVault } from './lib/lint.js'
import { scaffoldVault, SCAFFOLD_MODES } from './lib/scaffold.js'

export const name = 'wiki-tools'
export const inject = ['tools']

/** Tool-plugin configuration. */
export const Config = z.object({
  /** Absolute path to the vault root: the directory holding `wiki/` and `.raw/`. */
  vaultPath: z.string().required(),
  /** Maximum pages returned by one wiki_query standard-mode call. */
  maxQueryResults: z.number().default(10),
  /** Commit each vault mutation when the vault is a git repository. */
  gitAutoCommit: z.boolean().default(false),
  /** Age in seconds at which a held cross-process lock is treated as crashed. */
  lockStaleSeconds: z.number().default(60),
  /** Per-type folder overrides over the default routing, e.g. `{ domain: "wiki/areas" }`. */
  typeFolders: z.object({
    source: z.string(),
    entity: z.string(),
    concept: z.string(),
    domain: z.string(),
    question: z.string(),
    comparison: z.string(),
    meta: z.string(),
  }).default({}),
})

const PAGE_TYPES = ['source', 'entity', 'concept', 'domain', 'question', 'synthesis', 'comparison', 'decision', 'session', 'meta']
const STATUSES = ['seed', 'developing', 'mature', 'evergreen']

/**
 * Build the three wiki tool definitions over one vault. Exported for tests.
 * @param {Vault} vault - the configured vault.
 * @param {{ maxQueryResults?: number }} [options] - tool options.
 * @returns {import('@deepseek-ai/dsh-tools').ToolDefinition[]}
 */
export function createTools(vault, options = {}) {
  const limit = options.maxQueryResults ?? 10

  const wikiQuery = defineTool({
    name: 'wiki_query',
    description:
      'Search the knowledge vault. Quick mode returns the hot cache and master index verbatim — '
      + 'read those before opening any page. Standard mode runs full-text search over every wiki page '
      + 'and returns ranked matches with snippets, inbound links, and outbound link counts. '
      + 'Use standard mode when quick context is not enough.',
    parameters: {
      query: {
        type: 'string',
        required: true,
        description: 'The search text or question topic.',
      },
      mode: {
        type: 'string',
        enum: ['quick', 'standard'],
        description: 'quick returns hot.md + index.md only (~1500 tokens); standard searches all pages. Defaults to standard.',
      },
    },
    output: {
      schema: {
        type: 'object',
        additionalProperties: true,
      },
      render: (_args, value) => [{
        type: 'text',
        text: `${renderVaultRoot(vault.root)}\n\n${renderQueryResult(value)}`,
      }],
    },
    async execute(args) {
      if (args.mode === 'quick') {
        const view = await quickView(vault.root)
        return { mode: 'quick', ...view }
      }
      const { results, totalMatches } = await searchVault(vault.root, { query: args.query, limit })
      return { mode: 'standard', query: args.query, results, totalMatches }
    },
    presentCall: args => ({ card: 'generic', title: `Query wiki: ${args.query}`, kind: 'read', rawInput: args.query }),
  })

  const wikiWrite = defineTool({
    name: 'wiki_write',
    description:
      'Write or update one wiki page with full bookkeeping: routes the page to its type folder, '
      + 'completes YAML frontmatter (type, title, status, created, updated, tags), guards filename '
      + 'uniqueness, updates the master index entry, and prepends a log entry. Writes go to the '
      + 'CONFIGURED VAULT (run wiki_query to see its absolute root), not the session workspace. '
      + 'The content is the '
      + 'markdown body only — frontmatter is managed. With source_path, records the source hash in '
      + 'the ingest manifest and reports already_ingested for unchanged content unless force is set. '
      + 'The result lists unresolved wikilinks in the written page (targets that match no page or alias) '
      + 'so dead links are fixed at write time, not at the next lint.',
    parameters: {
      title: {
        type: 'string',
        required: true,
        description: 'Page title; also the filename and [[wikilink]] target. Title Case with spaces.',
      },
      type: {
        type: 'string',
        required: true,
        enum: PAGE_TYPES,
        description: 'Page type, which selects the folder: sources, entities, concepts, domains, questions, comparisons, or meta.',
      },
      content: {
        type: 'string',
        required: true,
        description: 'The markdown body after frontmatter.',
      },
      tags: {
        type: 'array',
        items: { type: 'string' },
        description: 'Frontmatter tags; defaults to [type].',
      },
      status: {
        type: 'string',
        enum: STATUSES,
        description: 'Frontmatter status (seed | developing | mature | evergreen); defaults to developing (kept on update).',
      },
      summary: {
        type: 'string',
        description: 'One-line master-index entry; defaults to the first content line.',
      },
      extra_frontmatter: {
        type: 'object',
        additionalProperties: true,
        description:
          'Flat schema fields to merge into frontmatter, e.g. related, sources, question, answer_quality '
          + '(question/synthesis), entity_type/role (entity), complexity/domain/aliases (concept), '
          + 'source_type/author/url/key_claims (source), subjects/dimensions/verdict (comparison), '
          + 'decision_date (decision). Values are scalars or scalar lists; nesting is forbidden; '
          + 'managed fields (type/title/status/created/updated/tags) are rejected.',
      },
      source_path: {
        type: 'string',
        description: 'Vault-relative .raw/ source this page derives from, for delta tracking.',
      },
      force: {
        type: 'boolean',
        description: 'Write even when the source hash is unchanged. Defaults to false.',
      },
    },
    output: {
      schema: {
        type: 'object',
        additionalProperties: true,
      },
      render: (args, value) => [{
        type: 'text',
        text: typeof value === 'object' && value !== null && value.alreadyIngested === true
          ? `wiki_write: skipped ${args.title} — source hash unchanged (pass force: true to re-ingest)`
          : typeof value === 'object' && value !== null && 'path' in value
            ? `wiki_write: ${value.created ? 'created' : 'updated'} ${value.path}`
              + (Array.isArray(value.unresolvedLinks) && value.unresolvedLinks.length > 0
                ? `\nwiki_write: note — ${value.unresolvedLinks.length} unresolved wikilink(s) in this page: ${value.unresolvedLinks.slice(0, 8).join(', ')}${value.unresolvedLinks.length > 8 ? ', …' : ''}. Create those pages or fix the targets; until then lint reports them as dead links.`
                : '')
            : `wiki_write: skipped ${args.title} (source unchanged)`,
      }],
    },
    async execute(args) {
      const { extra_frontmatter: extraFrontmatter, source_path: sourcePath, ...rest } = args
      return await vault.writePage({ ...rest, extraFrontmatter, sourcePath })
    },
    presentCall: args => ({ card: 'generic', title: `Write wiki page: ${args.title}`, kind: 'other', rawInput: { title: args.title, type: args.type } }),
  })

  const wikiRename = defineTool({
    name: 'wiki_rename',
    description:
      'Rename one wiki page and rewrite every [[wikilink]] to it across the vault (aliases and heading '
      + 'anchors preserved), move the file to the new title, retitle its frontmatter, swap its master-index '
      + 'and folder _index entries, and log the rename. The append-only log and dated lint reports keep the '
      + 'old name as history. Use this instead of manual file renames, which strand every inbound link.',
    parameters: {
      title: {
        type: 'string',
        required: true,
        description: 'Exact current page title.',
      },
      new_title: {
        type: 'string',
        required: true,
        description: 'New title; also the new filename and [[wikilink]] target. Title Case with spaces.',
      },
    },
    output: {
      schema: {
        type: 'object',
        additionalProperties: true,
      },
      render: (_args, value) => [{
        type: 'text',
        text: typeof value === 'object' && value !== null && 'to' in value
          ? `wiki_rename: [[${value.from}]] → [[${value.to}]]; rewrote links in ${value.linksRewritten} files; page at ${value.path}`
          : 'wiki_rename: failed',
      }],
    },
    async execute(args) {
      return await vault.renamePage({ title: args.title, newTitle: args.new_title })
    },
    presentCall: args => ({ card: 'generic', title: `Rename wiki page: ${args.title} → ${args.new_title}`, kind: 'other', rawInput: { from: args.title, to: args.new_title } }),
  })

  const wikiScaffold = defineTool({
    name: 'wiki_scaffold',
    description:
      'Scaffold a wiki vault in one call: the chosen mode\u2019s folder structure with per-folder _index.md, '
      + 'the core files (wiki/index.md, log.md, hot.md, overview.md), the mode\u2019s key seed pages, a raw-source '
      + 'manifest, and the vault AGENTS.md conventions file. Idempotent — existing files are kept. Modes: '
      + 'generic (matches wiki_write routing), sitemap, repository, business, personal, research, book. '
      + 'The result carries a suggested typeFolders config for non-generic modes to paste into the profile.',
    parameters: {
      mode: {
        type: 'string',
        required: true,
        enum: Object.keys(SCAFFOLD_MODES),
        description: 'Scaffold mode; pick by what the vault is for (generic for a general knowledge base).',
      },
      purpose: {
        type: 'string',
        description: 'One-line vault purpose, written into overview.md and AGENTS.md.',
      },
    },
    output: {
      schema: {
        type: 'object',
        additionalProperties: true,
      },
      render: (_args, value) => [{
        type: 'text',
        text: typeof value === 'object' && value !== null && 'created' in value
          ? `wiki_scaffold (${value.mode}): created ${value.created.length} files, skipped ${value.skipped.length} existing`
            + (Object.keys(value.suggestedTypeFolders ?? {}).length > 0
              ? `; suggested typeFolders: ${JSON.stringify(value.suggestedTypeFolders)}`
              : '')
          : 'wiki_scaffold: failed',
      }],
    },
    async execute(args) {
      return await scaffoldVault(vault.root, args)
    },
    presentCall: args => ({ card: 'generic', title: `Scaffold wiki vault (${args.mode})`, kind: 'other', rawInput: { mode: args.mode } }),
  })

  const wikiArchive = defineTool({
    name: 'wiki_archive',
    description:
      'Archive one cold raw source: move it from .raw/ to .archive/ (same subpath, file kept on disk) '
      + 'and drop its manifest entry so future ingests treat it as new. Use when a source is no longer '
      + 'active but should not be deleted. Pages derived from it are untouched.',
    parameters: {
      source_path: {
        type: 'string',
        required: true,
        description: 'Vault-relative .raw/ source path, e.g. .raw/articles/note.md.',
      },
    },
    output: {
      schema: {
        type: 'object',
        additionalProperties: true,
      },
      render: (_args, value) => [{
        type: 'text',
        text: typeof value === 'object' && value !== null && 'archivedTo' in value
          ? 'wiki_archive: ' + value.archivedFrom + ' → ' + value.archivedTo + ' (manifest entry dropped)'
          : 'wiki_archive: failed',
      }],
    },
    async execute(args) {
      return await vault.archiveSource({ sourcePath: args.source_path })
    },
    presentCall: args => ({ card: 'generic', title: 'Archive source: ' + args.source_path, kind: 'other', rawInput: { source: args.source_path } }),
  })

  const wikiLint = defineTool({
    name: 'wiki_lint',
    description:
      'Health-check the knowledge vault: duplicate filenames, dead wikilinks, orphan pages, '
      + 'frontmatter gaps, empty sections, stale index entries, and a stale hot cache. '
      + 'Report only — every issue carries a suggestion. Writes the dated report to wiki/meta/.',
    parameters: {},
    output: {
      schema: {
        type: 'object',
        additionalProperties: true,
      },
      render: (_args, value) => [{
        type: 'text',
        text: renderLintResult(value),
      }],
    },
    async execute() {
      return await lintVault(vault.root)
    },
    presentCall: () => ({ card: 'generic', title: 'Lint wiki vault', kind: 'other' }),
  })

  return [wikiQuery, wikiWrite, wikiRename, wikiScaffold, wikiArchive, wikiLint]
}

/**
 * Render a compact byline disclosing the vault root. Without it, a model whose
 * session workspace differs from the vault resolves `.raw/…` against the
 * workspace and concludes the tools point somewhere else.
 * @param {string} root - absolute vault root.
 * @returns {string} the byline.
 */
function renderVaultRoot(root) {
  return `wiki vault: ${root} — every wiki tool (query, write, lint) operates on this configured vault, not the session workspace. Resolve vault-relative paths like .raw/… and wiki/… against this root.`
}

/**
 * Render a wiki_query result as the model-facing text. The render output is the
 * ONLY content the model sees, so it carries the full payload — hot cache and
 * index verbatim in quick mode, every result with path, snippets, and link
 * context in standard mode — not a summary line.
 * @param {unknown} value - the execute return value.
 * @returns {string} the model-facing result text.
 */
function renderQueryResult(value) {
  if (typeof value !== 'object' || value === null) return 'wiki_query: no result'
  const result = value
  if (result.mode === 'quick') {
    const parts = []
    if (typeof result.hot === 'string' && result.hot.length > 0) {
      parts.push(`--- wiki/hot.md (recent context cache) ---\n${capText(result.hot, 6000)}`)
    }
    if (typeof result.index === 'string' && result.index.length > 0) {
      parts.push(`--- wiki/index.md (master catalog) ---\n${capText(result.index, 8000)}`)
    }
    if (parts.length === 0) return 'wiki_query (quick): the vault has no hot.md or index.md yet'
    return `wiki_query (quick): hot cache and master index follow. Read these before any page.\n\n${parts.join('\n\n')}`
  }
  if (!Array.isArray(result.results)) return 'wiki_query: no result'
  const lines = [`wiki_query: ${result.results.length} of ${result.totalMatches} matching pages. Open a page with the fs read tool for full content.`]
  for (const hit of result.results) {
    lines.push(`\n### ${hit.name}`)
    lines.push(`path: ${hit.path} · score ${hit.score} · inbound ${hit.inbound.length}${hit.inbound.length > 0 ? ` (${hit.inbound.slice(0, 5).join(', ')})` : ''} · outbound ${hit.outbound}`)
    for (const snippet of hit.snippets) lines.push(`> ${snippet}`)
  }
  return capText(lines.join('\n'), 12000)
}

/**
 * Render a wiki_lint result: every issue with page, severity, and suggestion.
 * @param {unknown} value - the execute return value.
 * @returns {string} the model-facing result text.
 */
function renderLintResult(value) {
  if (typeof value !== 'object' || value === null || !('summary' in value)) return 'wiki_lint: failed'
  const result = value
  const lines = [
    `wiki_lint: ${result.summary.issues} issues across ${result.summary.pagesScanned} pages.`,
    `checks: ${Object.entries(result.summary.byCheck ?? {}).map(([check, count]) => `${check}×${count}`).join(', ') || 'none'}`,
    `full report: ${typeof result.reportPath === 'string' ? result.reportPath : '(not written)'}`,
  ]
  for (const issue of (result.issues ?? []).slice(0, 60)) {
    lines.push(`- [${issue.severity}] ${issue.check} · ${issue.page}: ${issue.detail} → ${issue.suggestion}`)
  }
  if ((result.issues ?? []).length > 60) lines.push(`… and ${result.issues.length - 60} more (see the report file)`)
  return lines.join('\n')
}

/**
 * Cap one text block, marking the cut.
 * @param {string} text - full text.
 * @param {number} max - maximum characters kept.
 * @returns {string} the capped text.
 */
function capText(text, max) {
  return text.length <= max ? text : `${text.slice(0, max)}\n… (truncated at ${max} characters)`
}

/**
 * Validate the deployment config and register the three wiki tools.
 * @param {import('@deepseek-ai/cordis').Context} ctx - registrant context carrying the tool registry.
 * @param {import('@deepseek-ai/schemastery').Extract<typeof Config>} config - deployment config with the vault root.
 * @returns {Promise<void>}
 */
export async function apply(ctx, config) {
  if (typeof config.vaultPath !== 'string' || config.vaultPath.length === 0) {
    throw new Error(
      'wiki-tools: config vaultPath is required. Set it on the wiki-tools row from your profile cordis.patch.yml, e.g.\n'
      + '  - id: wiki-tools\n'
      + '    config:\n'
      + '      vaultPath: /absolute/path/to/vault\n'
      + 'The vault is the directory holding wiki/ and .raw/ (scaffold it with the wiki skill first).',
    )
  }
  if (config.gitAutoCommit === true && !existsSync(join(config.vaultPath, '.git'))) {
    throw new Error(
      'wiki-tools: gitAutoCommit is enabled but the vault is not a git repository; run git init in it first',
    )
  }
  const vault = new Vault(config.vaultPath, {
    typeFolders: config.typeFolders ?? {},
    gitAutoCommit: config.gitAutoCommit ?? false,
    lockStaleSeconds: config.lockStaleSeconds ?? 60,
  })
  await vault.assertRoot()
  for (const tool of createTools(vault, config)) {
    ctx.tools.register(tool)
  }
}
