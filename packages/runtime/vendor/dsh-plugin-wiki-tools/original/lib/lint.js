/**
 * Vault health checks: the mechanical half of the wiki-lint skill. Report
 * only — auto-fixing is a human decision, so every issue carries a suggestion
 * and the report lands in `wiki/meta/lint-report-YYYY-MM-DD.md`.
 *
 * @module dsh-plugin-wiki-tools/lib/lint
 */

import { mkdir, readFile, stat, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import {
  PAGE_STATUSES,
  buildAliasMap,
  collectMarkdown,
  isMachineryPage,
  resolveLinkTarget,
  splitFrontmatter,
  today,
} from './vault.js'

/** Frontmatter fields every content page must carry. */
const REQUIRED_FIELDS = ['type', 'status', 'created', 'updated', 'tags']

/**
 * Run every mechanical check over the vault.
 * @param {string} root - absolute vault root.
 * @returns {Promise<{ issues: Issue[], summary: { pagesScanned: number, issues: number, byCheck: Record<string, number> }, reportPath: string | undefined }>}
 */
export async function lintVault(root) {
  const pages = await collectMarkdown(join(root, 'wiki'))
  const issues = []
  const add = (check, severity, page, detail, suggestion) => {
    issues.push({ check, severity, page, detail, suggestion })
  }

  checkDuplicateFilenames(pages, add)
  const indexed = await checkStaleIndexEntries(root, pages, add)
  const inbound = checkDeadLinks(pages, add)
  checkOrphans(pages, inbound, indexed, add)
  checkFrontmatterGaps(pages, add)
  checkStatusVocabulary(pages, add)
  await checkStructurePages(root, add)
  checkEmptySections(pages, add)
  await checkHotCacheStaleness(root, pages, add)

  const byCheck = {}
  for (const issue of issues) byCheck[issue.check] = (byCheck[issue.check] ?? 0) + 1
  const reportPath = await writeReport(root, issues, pages.length)
  return {
    issues,
    summary: { pagesScanned: pages.length, issues: issues.length, byCheck },
    reportPath,
  }
}

/** @typedef {'error'|'warn'|'info'} Severity */
/** @typedef {{ check: string, severity: Severity, page: string, detail: string, suggestion: string }} Issue */
/** @typedef {(check: string, severity: Severity, page: string, detail: string, suggestion: string) => void} Add */

/**
 * Filenames must be unique vault-wide: wikilinks resolve by bare name.
 * @param {Pages} pages - collected pages.
 * @param {Add} add - issue recorder.
 */
function checkDuplicateFilenames(pages, add) {
  const seen = new Map()
  for (const page of pages) {
    if (isMachineryPage(page.name)) continue
    const key = page.name.toLowerCase()
    if (seen.has(key)) {
      add('duplicate-filename', 'error', page.name,
        `filename also exists at ${seen.get(key)}`,
        'Rename one page; wikilinks cannot address two files with one name')
    } else {
      seen.set(key, page.path)
    }
  }
}

/**
 * Index entries pointing at pages that do not exist.
 * @param {string} root - absolute vault root.
 * @param {Pages} pages - collected pages.
 * @param {Add} add - issue recorder.
 * @returns {Promise<Set<string>>} titles listed in the master index.
 */
async function checkStaleIndexEntries(root, pages, add) {
  const listed = new Set()
  const raw = await readFile(join(root, 'wiki', 'index.md'), 'utf8').catch(() => undefined)
  if (raw === undefined) return listed
  for (const match of raw.matchAll(/\[\[([^\]]+)\]\]/g)) {
    listed.add(match[1].split('|')[0].split('#')[0].trim())
  }
  const names = new Set(pages.map(page => page.name))
  for (const title of listed) {
    if (!names.has(title)) {
      add('stale-index-entry', 'warn', title,
        'listed in wiki/index.md but no page exists',
        'Remove the entry, or restore/rename the page to match')
    }
  }
  return listed
}

/**
 * Wikilinks targeting pages that do not exist.
 * @param {Pages} pages - collected pages.
 * @param {Add} add - issue recorder.
 * @returns {Map<string, string[]>} inbound links per page title.
 */
/**
 * Wikilinks targeting pages that do not exist. Targets resolve through page
 * titles first, then frontmatter `aliases` (Obsidian's order); only an
 * unresolved target is dead.
 * @param {Pages} pages - collected pages.
 * @param {Add} add - issue recorder.
 * @returns {Map<string, string[]>} inbound links per resolved page title.
 */
function checkDeadLinks(pages, add) {
  const names = new Set(pages.map(page => page.name))
  const aliases = buildAliasMap(pages)
  const inbound = new Map(pages.map(page => [page.name, []]))
  for (const page of pages) {
    if (isMachineryPage(page.name)) continue
    for (const target of page.links) {
      const resolved = resolveLinkTarget(target, names, aliases)
      if (resolved !== undefined) {
        inbound.get(resolved)?.push(page.name)
        continue
      }
      add('dead-link', 'error', page.name,
        `links to [[${target}]] which does not exist`,
        'Create a stub page, add the target to a page\u2019s aliases, or remove the link')
    }
  }
  return inbound
}

/**
 * Content pages with no inbound links and no index entry.
 * @param {Pages} pages - collected pages.
 * @param {Map<string, string[]>} inbound - inbound links per title.
 * @param {Set<string>} indexed - titles listed in the master index.
 * @param {Add} add - issue recorder.
 */
function checkOrphans(pages, inbound, indexed, add) {
  for (const page of pages) {
    const base = page.name.toLowerCase()
    if (isMachineryPage(page.name)) continue
    const links = inbound.get(page.name) ?? []
    const isIndexed = indexed.has(page.name)
    if (links.length === 0 && !isIndexed) {
      add('orphan-page', 'warn', page.name,
        'no inbound wikilinks and not in the master index',
        'Link it from a related page or the index, or delete it')
    }
  }
}

/**
 * Missing required frontmatter fields on content pages.
 * @param {Pages} pages - collected pages.
 * @param {Add} add - issue recorder.
 */
function checkFrontmatterGaps(pages, add) {
  for (const page of pages) {
    const base = page.name.toLowerCase()
    if (isMachineryPage(page.name)) continue
    const missing = REQUIRED_FIELDS.filter(field => page.fields?.[field] === undefined)
    if (missing.length > 0) {
      add('frontmatter-gap', 'warn', page.name,
        `missing fields: ${missing.join(', ')}`,
        'Complete the frontmatter (type, status, created, updated, tags)')
    }
  }
}

/**
 * Status values outside the lifecycle vocabulary (seed/developing/mature/
 * evergreen). A stray value silently breaks status-based queries and
 * promotion flows, so it is flagged even though links stay intact.
 * @param {Pages} pages - collected pages.
 * @param {Add} add - issue recorder.
 */
function checkStatusVocabulary(pages, add) {
  for (const page of pages) {
    if (isMachineryPage(page.name)) continue
    const status = page.fields?.status
    if (typeof status === 'string' && !PAGE_STATUSES.includes(status)) {
      add('status-vocabulary', 'warn', page.name,
        `status "${status}" is outside the lifecycle vocabulary (${PAGE_STATUSES.join('/')})`,
        `Set status to one of ${PAGE_STATUSES.join('/')}`)
    }
  }
}

/**
 * The narrative structure page every vault layout expects. `overview.md` is
 * human-maintained, so its absence is info — a nudge, not a defect.
 * @param {string} root - absolute vault root.
 * @param {Add} add - issue recorder.
 */
async function checkStructurePages(root, add) {
  const overview = join(root, 'wiki', 'overview.md')
  const exists = await stat(overview).then(() => true, () => false)
  if (!exists) {
    add('missing-structure', 'info', 'overview',
      'wiki/overview.md does not exist',
      'Run wiki_scaffold (generic) or write a ~200-word vault overview: what the vault is for, its areas, and where things go',
    )
  }
}

/**
 * Headings with no content before the next heading.
 * @param {Pages} pages - collected pages.
 * @param {Add} add - issue recorder.
 */
function checkEmptySections(pages, add) {
  for (const page of pages) {
    if (isMachineryPage(page.name)) continue
    // Fence-aware scan: lines inside code fences are content (a section whose
    // body is only code is not empty) and heading-like comment lines inside
    // fences never open sections.
    const lines = [...page.content.split('\n'), '# __eof__ sentinel']
    let heading
    let headingLevel = 0
    let hasContent = false
    let inFence = false
    for (const line of lines) {
      if (line.startsWith('```')) {
        inFence = !inFence
        hasContent = true
        continue
      }
      if (inFence) {
        hasContent = true
        continue
      }
      const match = /^(#{1,6}) (.+)$/.exec(line)
      if (match !== null) {
        const nextLevel = match[1].length
        // A heading followed directly by a deeper heading is a container, not
        // an empty section; only same-or-shallow succession or EOF is empty.
        if (heading !== undefined && !hasContent && nextLevel <= headingLevel) {
          add('empty-section', 'info', page.name,
            `section "${heading}" has no content`,
            'Fill it, or remove the heading')
        }
        heading = match[2]
        headingLevel = nextLevel
        hasContent = false
      } else if (line.trim().length > 0) {
        hasContent = true
      }
    }
  }
}

/**
 * The hot cache lagging behind every page's last update.
 * @param {string} root - absolute vault root.
 * @param {Pages} pages - collected pages.
 * @param {Add} add - issue recorder.
 */
async function checkHotCacheStaleness(root, pages, add) {
  const raw = await readFile(join(root, 'wiki', 'hot.md'), 'utf8').catch(() => undefined)
  if (raw === undefined) return
  const { fields } = splitFrontmatter(raw, 'wiki/hot.md')
  const hotUpdated = typeof fields?.updated === 'string' ? fields.updated : undefined
  if (hotUpdated === undefined) return
  const newest = pages
    .map(page => (typeof page.fields?.updated === 'string' ? page.fields.updated : ''))
    .sort()
    .at(-1)
  if (newest !== undefined && newest > hotUpdated) {
    add('stale-hot-cache', 'warn', 'hot.md',
      `hot cache updated ${hotUpdated}, newest page update ${newest}`,
      'Refresh wiki/hot.md to reflect recent changes')
  }
}

/**
 * Write the lint report page in the suite's canonical format.
 * @param {string} root - absolute vault root.
 * @param {Issue[]} issues - every found issue.
 * @param {number} pagesScanned - pages covered by the run.
 * @returns {Promise<string | undefined>} the report path, or undefined when writing failed.
 */
async function writeReport(root, issues, pagesScanned) {
  const date = today()
  const path = join(root, 'wiki', 'meta', `lint-report-${date}.md`)
  const sections = new Map()
  for (const issue of issues) {
    if (!sections.has(issue.check)) sections.set(issue.check, [])
    sections.get(issue.check).push(issue)
  }
  const lines = [
    '---',
    'type: meta',
    `title: "Lint Report ${date}"`,
    `created: ${date}`,
    `updated: ${date}`,
    'tags: [meta, lint]',
    'status: developing',
    '---',
    '',
    `# Lint Report: ${date}`,
    '',
    '## Summary',
    `- Pages scanned: ${pagesScanned}`,
    `- Issues found: ${issues.length}`,
    '',
  ]
  for (const [check, grouped] of sections) {
    lines.push(`## ${check.replace(/(^|-)(\w)/g, (_, prefix, char) => (prefix === '-' ? ' ' : '') + char.toUpperCase())}`)
    for (const issue of grouped) {
      lines.push(`- [[${issue.page}]] (${issue.severity}): ${issue.detail}. Suggest: ${issue.suggestion}.`)
    }
    lines.push('')
  }
  try {
    await mkdir(join(root, 'wiki', 'meta'), { recursive: true })
    await writeFile(path, `${lines.join('\n')}\n`, 'utf8')
    return path
  } catch {
    return undefined
  }
}

/** @typedef {{ name: string, path: string, rel: string, fields: Record<string, unknown> | undefined, content: string, links: string[] }[]} Pages */
