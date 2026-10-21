/**
 * Vault bookkeeping: path routing, frontmatter completion, index/log updates,
 * and source delta tracking for an Obsidian wiki vault following the LLM Wiki
 * layout (`.raw/` sources, `wiki/` knowledge tree).
 *
 * The vault is host-local user data addressed by an explicitly configured
 * absolute root; reads and writes go through node:fs directly, not a dsh
 * filesystem seam, because the vault lives outside any session workspace by
 * design (cross-project referencing is the point).
 *
 * @module dsh-plugin-wiki-tools/lib/vault
 */

import { createHash } from 'node:crypto'
import { spawnSync } from 'node:child_process'
import { appendFileSync, readFileSync } from 'node:fs'
import { mkdir, open, readFile, readdir, rm, stat, writeFile } from 'node:fs/promises'
import { basename, dirname, isAbsolute, join, relative, sep } from 'node:path'
import { parse as parseYaml, stringify as stringifyYaml } from 'yaml'

/** Page-type to vault folder routing (the suite's generic mode). */
export const TYPE_FOLDERS = {
  source: 'wiki/sources',
  entity: 'wiki/entities',
  concept: 'wiki/concepts',
  domain: 'wiki/domains',
  question: 'wiki/questions',
  comparison: 'wiki/comparisons',
  synthesis: 'wiki/questions',
  decision: 'wiki/meta',
  session: 'wiki/meta',
  meta: 'wiki/meta',
}

/** Lifecycle status vocabulary; writePage rejects anything else and lint flags it. */
export const PAGE_STATUSES = ['seed', 'developing', 'mature', 'evergreen']

/** Master-index section headings follow the mapped folder basename, computed per vault. */

/**
 * Capitalize a folder basename for an index section heading.
 * @param {string} value - lowercase folder basename.
 * @returns {string} the capitalized heading title.
 */
function capitalize(value) {
  return value.length === 0 ? value : value[0].toUpperCase() + value.slice(1)
}

/** Pages that are vault machinery, never linted as content (basenames, no extension). */
export const META_FILENAMES = new Set(['index', '_index', 'log', 'hot', 'overview'])

/**
 * Split one Markdown file into frontmatter fields and body. A file without a
 * frontmatter fence returns no fields; a broken fence throws.
 * @param {string} raw - the complete file text.
 * @param {string} source - path shown in error messages.
 * @returns {{ fields: Record<string, unknown> | undefined, content: string }}
 */
export function splitFrontmatter(raw, source) {
  if (!raw.startsWith('---\n') && !raw.startsWith('---\r\n')) return { fields: undefined, content: raw }
  const firstLineEnd = raw.indexOf('\n')
  const rest = raw.slice(firstLineEnd + 1)
  const closing = rest.search(/^---(?:\r?\n|$)/m)
  if (closing < 0) throw new Error(`${source}: frontmatter has no closing --- fence`)
  const frontmatterText = rest.slice(0, closing)
  const content = rest.slice(closing).replace(/^---\r?\n?/, '')
  const fields = parseYaml(frontmatterText)
  if (fields !== null && typeof fields !== 'object' && !Array.isArray(fields)) {
    throw new Error(`${source}: frontmatter must be a YAML mapping`)
  }
  return { fields: fields === null ? undefined : fields, content }
}

/** Today as the vault's canonical YYYY-MM-DD stamp. */
export function today() {
  return new Date().toISOString().slice(0, 10)
}

/**
 * Compare a stored manifest key against a normalized vault-relative path.
 * Hand-written entries (the wiki-ingest skill era) may carry the platform's
 * backslash separators; matching must not depend on them.
 * @param {string} storedKey - key as written in `.raw/.manifest.json`.
 * @param {string} rel - normalized `.raw/…` path.
 * @returns {boolean}
 */
function sameSourceKey(storedKey, rel) {
  return storedKey === rel || storedKey.replace(/\\/g, '/') === rel
}

/**
 * One vault root. All bookkeeping mutations go through {@link Vault.writePage},
 * which completes frontmatter, updates the master index, and prepends a log
 * entry in one serialized write per file, guarded by a cross-process advisory
 * lock (the wiki-lock contract) and optionally followed by a git commit.
 */
export class Vault {
  /**
   * @param {string} root - absolute path to the vault root (the directory holding `wiki/` and `.raw/`).
   * @param {object} [options] - vault options.
   * @param {Record<string, string>} [options.typeFolders] - per-type folder overrides over
   *   {@link TYPE_FOLDERS} (e.g. `{ domain: 'wiki/areas' }` for a vault whose topics live in `areas/`).
   * @param {boolean} [options.gitAutoCommit] - commit each mutation when the vault is a git repository.
   * @param {number} [options.lockStaleSeconds] - age at which a held advisory lock is considered
   *   crashed and may be broken; default 60.
   */
  constructor(root, { typeFolders = {}, gitAutoCommit = false, lockStaleSeconds = 60 } = {}) {
    if (typeof root !== 'string' || root.length === 0 || !isAbsolute(root)) {
      throw new Error(`wiki-tools: vaultPath must be an absolute directory path (got ${JSON.stringify(root)})`)
    }
    for (const key of Object.keys(arguments[1] ?? {})) {
      if (!['typeFolders', 'gitAutoCommit', 'lockStaleSeconds'].includes(key)) {
        throw new Error(`wiki-tools: unknown Vault option "${key}"`)
      }
    }
    this.root = root
    this.gitAutoCommit = gitAutoCommit
    this.lockStaleMs = lockStaleSeconds * 1000
    this.typeFolders = { ...TYPE_FOLDERS }
    for (const [type, folder] of Object.entries(typeFolders)) {
      if (!(type in this.typeFolders)) {
        throw new Error(`wiki-tools: typeFolders config names unknown type "${type}"`)
      }
      if (typeof folder !== 'string' || folder.length === 0 || folder.includes('..')) {
        throw new Error(`wiki-tools: typeFolders.${type} must be a non-empty vault-relative folder path`)
      }
      this.typeFolders[type] = folder
    }
    /** Index section heading per type, following the effective folder layout. */
    this.indexSections = Object.fromEntries(
      Object.keys(TYPE_FOLDERS).map(type => [type, `## ${capitalize(basename(this.typeFolders[type]))}`]),
    )
    /** Per-file write chains so concurrent tool calls serialize per target. */
    this.writeChains = new Map()
  }

  /** Absolute path of one routed page. @param {string} type - page type. @param {string} title - page title (also the filename). */
  pagePath(type, title) {
    const folder = this.typeFolders[type]
    if (folder === undefined) throw new Error(`wiki-tools: unknown page type "${type}"`)
    if (!/^[^/\\]+(\.md)?$/.test(title) || title.includes('\n')) {
      throw new Error(`wiki-tools: title must be a plain filename without path separators (got ${JSON.stringify(title)})`)
    }
    const filename = title.endsWith('.md') ? title : `${title}.md`
    return join(this.root, folder, filename)
  }

  /**
   * Verify the vault root exists and is a directory.
   * @returns {Promise<void>} rejects with a setup hint when the root is missing.
   */
  async assertRoot() {
    const info = await stat(this.root).catch(error => {
      if (error.code === 'ENOENT') {
        throw new Error(`wiki-tools: vault root ${this.root} does not exist; scaffold it first (the wiki skill's SCAFFOLD operation), then point vaultPath at it`)
      }
      throw error
    })
    if (!info.isDirectory()) throw new Error(`wiki-tools: vault root ${this.root} is not a directory`)
  }

  /**
   * Read one page's frontmatter and body.
   * @param {string} path - absolute page path.
   * @returns {Promise<{ fields: Record<string, unknown> | undefined, content: string } | undefined>} undefined when missing.
   */
  async readPage(path) {
    let raw
    try {
      raw = await readFile(path, 'utf8')
    } catch (error) {
      if (error.code === 'ENOENT') return undefined
      throw error
    }
    return splitFrontmatter(raw, path)
  }

  /**
   * Serialize one mutating operation per target path.
   * @param {string} path - absolute target path.
   * @param {() => Promise<T>} operation - the mutation, run after the previous one settles.
   * @returns {Promise<T>}
   */
  enqueue(path, operation) {
    const previous = this.writeChains.get(path) ?? Promise.resolve()
    const next = previous.then(operation, operation)
    this.writeChains.set(path, next.then(() => {}, () => {}))
    return next
  }

  /**
   * Run one mutation under a cross-process advisory lock (the wiki-lock
   * contract): writers in other processes or sessions serialize on the same
   * lock file under `.vault-meta/locks/`. A held lock is retried once after
   * 2s and then reported; a lock older than lockStaleSeconds is treated as
   * crashed and broken.
   * @param {string} key - lock key; vault-relative page path, or `__vault__`
   *   for vault-wide mutations (rename, archive) and `__manifest__` for the
   *   ingest manifest.
   * @param {() => Promise<T>} operation - the mutation to guard.
   * @returns {Promise<T>}
   * @template T
   */
  async withFileLock(key, operation) {
    const locksDir = join(this.root, '.vault-meta', 'locks')
    await mkdir(locksDir, { recursive: true })
    const lockPath = join(locksDir, `${createHash('sha1').update(key).digest('hex')}.lock`)
    const acquire = async () => {
      try {
        const handle = await open(lockPath, 'wx')
        await handle.writeFile(`${JSON.stringify({ key, at: Date.now() })}\n`)
        await handle.close()
        return true
      } catch (error) {
        if (error.code !== 'EEXIST') throw error
        const info = await stat(lockPath).catch(() => undefined)
        if (info !== undefined && Date.now() - info.mtimeMs > this.lockStaleMs) {
          await rm(lockPath, { force: true })
          return await acquire()
        }
        return false
      }
    }
    if (!(await acquire())) {
      await new Promise(resolve => setTimeout(resolve, 2000))
      if (!(await acquire())) {
        throw new Error(`wiki-tools: ${key} is locked by another writer; skipped (retry once it releases)`)
      }
    }
    try {
      return await operation()
    } finally {
      await rm(lockPath, { force: true })
    }
  }

  /**
   * Stage and commit vault changes when git auto-commit is enabled (the
   * upstream PostToolUse behavior). Commits only when something is staged.
   * @param {string} message - the conventional commit message.
   * @returns {void} throws with git's stderr when git itself fails.
   */
  gitCommit(message) {
    if (!this.gitAutoCommit) return
    const run = args => spawnSync('git', ['-C', this.root, ...args], { encoding: 'utf8' })
    this.ignoreLockFiles()
    const add = run(['add', '-A'])
    if (add.status !== 0) throw new Error(`wiki-tools: git add failed in the vault: ${String(add.stderr).trim()}`)
    const pending = run(['diff', '--cached', '--quiet'])
    if (pending.status === 1) {
      const commit = run(['commit', '-m', message])
      if (commit.status !== 0) throw new Error(`wiki-tools: git commit failed in the vault: ${String(commit.stderr).trim()}`)
    }
  }

  /**
   * Keep advisory lock files out of vault history: cross-process locks under
   * `.vault-meta/locks/` are pure runtime coordination, never vault state.
   * Idempotent; creates or appends the vault's `.gitignore` as needed.
   * @returns {void}
   */
  ignoreLockFiles() {
    const marker = '.vault-meta/locks/'
    const gitignore = join(this.root, '.gitignore')
    let current = ''
    try {
      current = readFileSync(gitignore, 'utf8')
    } catch (error) {
      if (error.code !== 'ENOENT') throw error
    }
    if (!current.split('\n').some(line => line.trim() === marker)) {
      const prefix = current.length === 0 || current.endsWith('\n') ? '' : '\n'
      appendFileSync(gitignore, `${prefix}# wiki-tools runtime locks\n${marker}\n`, 'utf8')
    }
  }

  /**
   * Write one wiki page with complete bookkeeping: frontmatter completion,
   * filename-uniqueness guard, master-index entry, folder `_index.md` entry,
   * and a log entry. Existing pages keep `created` and any unknown frontmatter
   * fields; `updated` moves to today.
   * @param {object} input - the write request.
   * @param {string} input.type - page type (routed to a folder).
   * @param {string} input.title - page title; also the filename and wikilink target.
   * @param {string} input.content - markdown body after frontmatter.
   * @param {string[]} [input.tags] - frontmatter tags; defaults to `[type]`.
   * @param {string} [input.status] - frontmatter status; one of seed/developing/mature/evergreen.
   * @param {string} [input.summary] - one-line index entry; defaults to the first content line.
   * @param {Record<string, unknown>} [input.extraFrontmatter] - flat schema fields to merge
   *   (related, sources, question, answer_quality, entity_type, aliases, …); must stay flat and
   *   cannot override the managed fields.
   * @param {string} [input.sourcePath] - vault-relative `.raw/` source this page derives from;
   *   registers/refreshes the manifest entry (sha256 delta tracking) and returns `alreadyIngested`
   *   without writing when the hash is unchanged.
   * @param {boolean} [input.force] - with sourcePath, write even when the source hash is unchanged.
   * @returns {Promise<{ path: string, created: boolean, title: string } | { alreadyIngested: true, title: string, sourceHash: string, detail: string }>}
   */
  async writePage({ type, title, content, tags, status, summary, extraFrontmatter, sourcePath, force }) {
    const path = this.pagePath(type, title)
    return await this.enqueue(path, async () => await this.withFileLock(relative(this.root, path).split(sep).join('/'), async () => {
      await this.assertRoot()
      const cleanTitle = title.endsWith('.md') ? title.slice(0, -3) : title
      const existing = await this.readPage(path)
      await this.assertUniqueFilename(cleanTitle, path)
      validateExtraFrontmatter(extraFrontmatter)
      if (status !== undefined && !PAGE_STATUSES.includes(status)) {
        throw new Error(`wiki-tools: status must be one of ${PAGE_STATUSES.join('/')} (got ${JSON.stringify(status)})`)
      }
      // Source registration is mechanical bookkeeping, not model work: when the
      // page summarizes a `.raw/` source, the manifest entry (sha256 delta
      // tracking) is written by this tool, and an unchanged hash is rejected
      // unless the caller forces a re-ingest.
      if (sourcePath !== undefined) {
        const { hash, alreadyIngested } = await this.inspectSource(sourcePath)
        if (alreadyIngested && force !== true) {
          return {
            alreadyIngested: true, title: cleanTitle, sourceHash: hash,
            detail: 'source hash unchanged; pass force: true to re-ingest, or omit source_path for a plain page write',
          }
        }
      }
      const date = today()
      const fields = {
        ...(existing?.fields ?? {}),
        type,
        title: cleanTitle,
        status: status ?? existing?.fields?.status ?? 'developing',
        created: existing?.fields?.created ?? date,
        updated: date,
        tags: tags ?? existing?.fields?.tags ?? [type],
        ...(extraFrontmatter ?? {}),
      }
      const file = `---\n${stringifyYaml(fields).trimEnd()}\n---\n\n${content.replace(/^\s*\n/, '')}\n`
      await mkdir(join(path, '..'), { recursive: true })
      await writeFile(path, file, 'utf8')
      await this.updateIndex(type, cleanTitle, summary ?? firstContentLine(content))
      await this.updateFolderIndex(type, cleanTitle, summary ?? firstContentLine(content))
      await this.prependLog(`## [${date}] ${existing === undefined ? 'create' : 'update'} | ${cleanTitle}`, [
        `- ${existing === undefined ? 'Created' : 'Updated'}: [[${cleanTitle}]]`,
      ])
      this.gitCommit(`wiki: ${existing === undefined ? 'create' : 'update'} ${cleanTitle}`)
      if (sourcePath !== undefined) {
        await this.trackSource({
          sourcePath,
          pagesCreated: existing === undefined ? [cleanTitle] : [],
          pagesUpdated: existing === undefined ? [] : [cleanTitle],
        })
      }
      // Surface dead-on-arrival wikilinks now, not at the next lint: forward
      // links to pages about to be created are legitimate, so this is a note,
      // never a rejection.
      const pagesNow = await collectMarkdown(join(this.root, 'wiki'))
      const names = new Set(pagesNow.map(page => page.name))
      const aliases = buildAliasMap(pagesNow)
      const unresolvedLinks = [...new Set(extractWikilinks(content))]
        .filter(target => resolveLinkTarget(target, names, aliases) === undefined)
      return {
        path, created: existing === undefined, title: cleanTitle,
        ...(unresolvedLinks.length > 0 ? { unresolvedLinks } : {}),
      }
    }))
  }

  /**
   * Add or refresh one entry in the owning folder's `_index.md` sub-index, the
   * wiki-ingest contract's per-folder catalog. Missing files are created with
   * a single `## <Type>` section; existing entries are replaced in place in
   * the section's dominant separator style.
   * @param {string} type - page type selecting folder and section label.
   * @param {string} title - page title.
   * @param {string} summary - one-line description.
   */
  async updateFolderIndex(type, title, summary) {
    const folder = this.typeFolders[type]
    const indexPath = join(this.root, folder, '_index.md')
    const entryPattern = new RegExp(`^\\s*-?\\s*\\[\\[${escapeRegExp(title)}\\]\\]`)
    let raw = await readFile(indexPath, 'utf8').catch(() => undefined)
    if (raw === undefined) {
      const heading = `## ${capitalize(type)}s`
      const file = `---\ntype: meta\ntitle: "${capitalize(basename(folder))} Index"\nupdated: ${today()}\n---\n\n${heading}\n\n- [[${title}]]: ${summary.replace(/\n/g, ' ')}\n`
      await writeFile(indexPath, file, 'utf8')
      return
    }
    const lines = raw.split('\n')
    const at = lines.findIndex(line => entryPattern.test(line))
    const entry = `- [[${title}]]: ${summary.replace(/\n/g, ' ')}`
    if (at >= 0) {
      lines[at] = entry
    } else {
      let insert = lines.length
      while (insert > 0 && lines[insert - 1].trim() === '') insert -= 1
      lines.splice(insert, 0, entry)
    }
    const updatedLine = lines.findIndex(line => /^updated: /.test(line))
    if (updatedLine >= 0) lines[updatedLine] = `updated: ${today()}`
    await writeFile(indexPath, `${lines.join('\n')}\n`, 'utf8')
  }

  /**
   * Rename one page and rewrite every wikilink to it across the vault:
   * `[[Old]]` → `[[New]]`, preserving aliases (`[[Old|x]]` → `[[New|x]]`) and
   * heading anchors. The append-only log and dated lint reports are historical
   * records and keep the old name; frontmatter aliases keep resolving.
   * @param {object} input - the rename request.
   * @param {string} input.title - exact current page title.
   * @param {string} input.newTitle - the new title and filename.
   * @returns {Promise<{ from: string, to: string, path: string, linksRewritten: number, filesRewritten: string[] }>}
   */
  async renamePage({ title, newTitle }) {
    return await this.enqueue(join(this.root, 'wiki'), async () => await this.withFileLock('__vault__', async () => {
      await this.assertRoot()
      const cleanNew = newTitle.endsWith('.md') ? newTitle.slice(0, -3) : newTitle
      if (!/^[^/\\]+(\.md)?$/.test(newTitle) || newTitle.includes('\n')) {
        throw new Error(`wiki-tools: newTitle must be a plain filename without path separators (got ${JSON.stringify(newTitle)})`)
      }
      if (cleanNew === title) throw new Error('wiki-tools: newTitle equals the current title')
      const pages = await collectMarkdown(join(this.root, 'wiki'))
      const target = pages.find(page => page.name === title)
      if (target === undefined) throw new Error(`wiki-tools: no page named "${title}" exists in the vault`)
      if (isMachineryPage(title)) {
        throw new Error(`wiki-tools: "${title}" is vault machinery (index, log, hot cache, overview, sub-index, or lint report); renames would break conventions — fix the pages linking to it instead`)
      }
      if (pages.some(page => page.name !== title && page.name.toLowerCase() === cleanNew.toLowerCase())) {
        throw new Error(`wiki-tools: filename "${cleanNew}.md" already exists; wikilinks need unique filenames`)
      }
      const type = typeof target.fields?.type === 'string' && target.fields.type in this.typeFolders
        ? target.fields.type
        : 'meta'

      // 1. Rewrite links everywhere except immutable records.
      const rewritten = []
      for (const page of pages) {
        if (page.name === title || page.name.toLowerCase() === 'log' || /^lint-report-/.test(page.name)) continue
        const raw = await readFile(page.path, 'utf8').catch(() => undefined)
        if (raw === undefined) continue
        // Exact-target boundary: the title must end the link target (`]]`),
        // start an alias (`|`), or start an anchor (`#`). Escapes are doubled
        // because this is a string-built RegExp, not a regex literal: single
        // `\]` / `\|` would be eaten by the template literal and leave an
        // empty alternation branch matching every `[[title` prefix.
        const pattern = new RegExp(`\\[\\[${escapeRegExp(title)}(\\]\\]|\\||#)`, 'g')
        let updated = raw.replace(pattern, `[[${cleanNew}$1`)
        // A page whose links changed today is not "current" as of yesterday.
        if (updated !== raw) updated = updated.replace(/^(updated:\s*).+$/m, `$1${today()}`)
        if (updated !== raw) {
          await writeFile(page.path, updated, 'utf8')
          rewritten.push(page.name)
        }
      }

      // 2. Move the page and retitle its frontmatter.
      const newPath = this.pagePath(type, cleanNew)
      const oldRaw = await readFile(target.path, 'utf8')
      const retitled = oldRaw.replace(/^(title:.*)$/m, `title: ${cleanNew}`)
      await mkdir(dirname(newPath), { recursive: true })
      await writeFile(newPath, retitled, 'utf8')
      if (newPath !== target.path) await rm(target.path)

      // 3. Swap index entries: drop the old lines, add the new.
      await this.removeIndexEntries(title)
      const summary = firstContentLine(splitFrontmatter(retitled, newPath).content)
      await this.updateIndex(type, cleanNew, summary)
      await this.updateFolderIndex(type, cleanNew, summary)
      await this.prependLog(`## [${today()}] rename | ${title}`, [
        `- Renamed: [[${title}]] → [[${cleanNew}]] (${rewritten.length} files' links rewritten)`,
      ])
      this.gitCommit(`wiki: rename ${title} -> ${cleanNew}`)
      return { from: title, to: cleanNew, path: newPath, linksRewritten: rewritten.length, filesRewritten: rewritten }
    }))
  }

  /**
   * Archive one raw source: move it from `.raw/` to `.archive/` (same
   * subpath) and drop its manifest entry, the wiki skill's cold-source
   * hygiene rule. Archived files leave the ingest set but stay on disk.
   * @param {object} input - the archive request.
   * @param {string} input.sourcePath - vault-relative `.raw/` path.
   * @returns {Promise<{ archivedFrom: string, archivedTo: string }>}
   */
  async archiveSource({ sourcePath }) {
    return await this.enqueue(join(this.root, '.archive'), async () => await this.withFileLock('__vault__', async () => {
      await this.assertRoot()
      const absolute = isAbsolute(sourcePath) ? sourcePath : join(this.root, sourcePath)
      const rel = relative(this.root, absolute).split(sep).join('/')
      if (!rel.startsWith('.raw/')) {
        throw new Error('wiki-tools: wiki_archive moves .raw/ sources only')
      }
      const raw = await readFile(absolute).catch(error => {
        if (error.code === 'ENOENT') throw new Error(`wiki-tools: source ${sourcePath} not found under the vault`)
        throw error
      })
      const destination = join(this.root, '.archive', rel.slice('.raw/'.length))
      await mkdir(join(destination, '..'), { recursive: true })
      await writeFile(destination, raw)
      await rm(absolute)
      const manifestPath = join(this.root, '.raw', '.manifest.json')
      const manifest = await readJson(manifestPath, { sources: {} })
      for (const key of Object.keys(manifest.sources)) {
        if (sameSourceKey(key, rel)) delete manifest.sources[key]
      }
      await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8')
      await this.prependLog(`## [${today()}] archive | ${rel}`, [
        `- Archived: \`${rel}\` → \`.archive/${rel.slice('.raw/'.length)}\``,
      ])
      this.gitCommit(`wiki: archive ${rel}`)
      return { archivedFrom: rel, archivedTo: `.archive/${rel.slice('.raw/'.length)}` }
    }))
  }

  /**
   * Remove one page's entry lines from the master index and its folder
   * `_index.md`, used when a rename replaces rather than refreshes.
   * @param {string} title - page title whose entries are removed.
   */
  async removeIndexEntries(title) {
    const pattern = new RegExp(`^\\s*-?\\s*\\[\\[${escapeRegExp(title)}\\]\\]`)
    for (const indexPath of [join(this.root, 'wiki', 'index.md'), ...Object.values(this.typeFolders).map(folder => join(this.root, folder, '_index.md'))]) {
      const raw = await readFile(indexPath, 'utf8').catch(() => undefined)
      if (raw === undefined) continue
      const lines = raw.split('\n')
      const filtered = lines.filter(line => !pattern.test(line))
      if (filtered.length !== lines.length) await writeFile(indexPath, `${filtered.join('\n')}\n`, 'utf8')
    }
  }

  /**
   * Reject a title whose filename already exists elsewhere in the tree:
   * wikilinks address pages by bare filename, so duplicates break resolution.
   * @param {string} title - page title being written.
   * @param {string} path - the routed destination path.
   */
  async assertUniqueFilename(title, path) {
    const pages = await collectMarkdown(join(this.root, 'wiki'))
    for (const page of pages) {
      if (page.name.toLowerCase() === title.toLowerCase() && page.path !== path) {
        throw new Error(`wiki-tools: filename "${title}.md" already exists at ${page.path}; wikilinks need unique filenames`)
      }
    }
  }

  /**
   * Add or refresh one `[[Title]]` entry in the master index. Missing sections
   * and files are created on first use. Existing entries are matched regardless
   * of separator (`: ` or ` — `) and rewritten in the section's dominant style,
   * so vaults using em-dash indexes stay consistent.
   * @param {string} type - page type selecting the index section.
   * @param {string} title - page title.
   * @param {string} summary - one-line description.
   */
  async updateIndex(type, title, summary) {
    const heading = this.indexSections[type]
    if (heading === undefined) return
    const indexPath = join(this.root, 'wiki', 'index.md')
    let raw = await readFile(indexPath, 'utf8').catch(() => undefined)
    if (raw === undefined) {
      raw = '# Wiki Index\n\n'
      for (const section of Object.values(this.indexSections)) raw += `${section}\n\n`
      await mkdir(join(indexPath, '..'), { recursive: true })
    }
    const lines = raw.split('\n')
    let headingLine = lines.findIndex(line => line === heading)
    if (headingLine < 0) {
      lines.push('', heading, `- [[${title}]]: ${summary.replace(/\n/g, ' ')}`)
      await writeFile(indexPath, `${lines.join('\n')}\n`, 'utf8')
      return
    }
    let end = headingLine + 1
    while (end < lines.length && lines[end] !== '' && !lines[end].startsWith('## ')) end += 1
    const section = lines.slice(headingLine + 1, end)
    const entryPattern = new RegExp(`^\\s*-?\\s*\\[\\[${escapeRegExp(title)}\\]\\]`)
    const at = section.findIndex(line => entryPattern.test(line))
    const separator = indexSeparator(section, at >= 0 ? section[at] : undefined)
    const entry = `- [[${title}]]${separator} ${summary.replace(/\n/g, ' ')}`
    if (at >= 0) {
      lines[headingLine + 1 + at] = entry
    } else {
      lines.splice(end, 0, entry)
    }
    await writeFile(indexPath, `${lines.join('\n')}\n`, 'utf8')
  }

  /**
   * Prepend one dated entry to the append-only operation log.
   * @param {string} header - the `## [date] op | title` heading line.
   * @param {string[]} bullets - detail lines under the heading.
   */
  async prependLog(header, bullets) {
    const logPath = join(this.root, 'wiki', 'log.md')
    const raw = await readFile(logPath, 'utf8').catch(() => '# Wiki Log\n')
    const stripped = raw.replace(/^# Wiki Log\r?\n?/, '')
    const entry = `${header}\n${bullets.join('\n')}\n\n`
    await mkdir(join(logPath, '..'), { recursive: true })
    await writeFile(logPath, `# Wiki Log\n\n${entry}${stripped.replace(/^\s*/, '')}`, 'utf8')
  }

  /**
   * Delta-track one raw source: report whether its content hash is unchanged
   * since the last ingest, then record the new hash and touched pages.
   * @param {object} input - the tracking request.
   * @param {string} input.sourcePath - vault-relative or absolute `.raw/` source path.
   * @param {string[]} [input.pagesCreated] - pages this ingest created.
   * @param {string[]} [input.pagesUpdated] - pages this ingest updated.
   * @returns {Promise<{ hash: string, alreadyIngested: boolean }>}
   */
  async trackSource({ sourcePath, pagesCreated = [], pagesUpdated = [] }) {
    return await this.withFileLock('__manifest__', async () => {
    const absolute = isAbsolute(sourcePath) ? sourcePath : join(this.root, sourcePath)
    const rel = relative(this.root, absolute).split(sep).join('/')
    const raw = await readFile(absolute).catch(error => {
      if (error.code === 'ENOENT') throw new Error(`wiki-tools: source ${sourcePath} not found under the vault`)
      throw error
    })
    const hash = createHash('sha256').update(raw).digest('hex')
    const manifestPath = join(this.root, '.raw', '.manifest.json')
    const manifest = await readJson(manifestPath, { sources: {} })
    let previous
    let twinKey
    for (const [key, entry] of Object.entries(manifest.sources)) {
      if (sameSourceKey(key, rel)) { previous = entry; twinKey = key; break }
    }
    const alreadyIngested = previous !== undefined && previous.hash === hash
    if (twinKey !== undefined && twinKey !== rel) delete manifest.sources[twinKey]
    manifest.sources[rel] = {
      hash,
      ingested_at: today(),
      pages_created: pagesCreated,
      pages_updated: pagesUpdated,
    }
    await mkdir(join(manifestPath, '..'), { recursive: true })
    await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8')
    return { hash, alreadyIngested }
    })
  }

  /**
   * Hash one raw source and report whether the manifest already carries this
   * exact hash — the wiki-ingest delta check's mechanical half.
   * @param {string} sourcePath - vault-relative (or absolute) `.raw/` path.
   * @returns {Promise<{ rel: string, hash: string, alreadyIngested: boolean }>}
   */
  async inspectSource(sourcePath) {
    const absolute = isAbsolute(sourcePath) ? sourcePath : join(this.root, sourcePath)
    const rel = relative(this.root, absolute).split(sep).join('/')
    if (!rel.startsWith('.raw/')) {
      throw new Error('wiki-tools: source_path must be a vault-relative path under .raw/')
    }
    const raw = await readFile(absolute).catch(error => {
      if (error.code === 'ENOENT') throw new Error(`wiki-tools: source ${sourcePath} not found under the vault`)
      throw error
    })
    const hash = createHash('sha256').update(raw).digest('hex')
    const manifest = await readJson(join(this.root, '.raw', '.manifest.json'), { sources: {} })
    let previous
    for (const [key, entry] of Object.entries(manifest.sources)) {
      if (sameSourceKey(key, rel)) { previous = entry; break }
    }
    return { rel, hash, alreadyIngested: previous !== undefined && previous.hash === hash }
  }
}

/**
 * First non-heading, non-empty content line, for index summaries.
 * @param {string} content - markdown body.
 * @returns {string} up to 120 characters of the first prose line.
 */
function firstContentLine(content) {
  for (const line of content.split('\n')) {
    const trimmed = line.trim()
    if (trimmed.length > 0 && !trimmed.startsWith('#') && !trimmed.startsWith('---')) {
      return trimmed.length > 120 ? `${trimmed.slice(0, 117)}...` : trimmed
    }
  }
  return '(no summary)'
}

/**
 * Escape regex metacharacters so a title containing `(`, `)`, `+`, etc. matches literally.
 * @param {string} value - raw title.
 * @returns {string} regex-safe text.
 */
function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/** Frontmatter fields writePage manages itself; extraFrontmatter cannot override them. */
const MANAGED_FIELDS = new Set(['type', 'title', 'status', 'created', 'updated', 'tags'])

/**
 * Validate caller-supplied schema fields: flat mapping of primitives or lists
 * of primitives (the vault schema forbids nesting for Obsidian's Properties UI).
 * @param {Record<string, unknown> | undefined} extra - the extraFrontmatter input.
 * @returns {void} throws on any violation.
 */
function validateExtraFrontmatter(extra) {
  if (extra === undefined) return
  if (typeof extra !== 'object' || extra === null || Array.isArray(extra)) {
    throw new Error('wiki-tools: extraFrontmatter must be a flat object of schema fields')
  }
  for (const [key, value] of Object.entries(extra)) {
    if (MANAGED_FIELDS.has(key)) {
      throw new Error(`wiki-tools: extraFrontmatter cannot override managed field "${key}"`)
    }
    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      throw new Error(`wiki-tools: extraFrontmatter must stay flat; "${key}" is an object (the schema forbids nesting)`)
    }
    if (Array.isArray(value) && value.some(item => item !== null && typeof item === 'object')) {
      throw new Error(`wiki-tools: extraFrontmatter list "${key}" may hold only scalars`)
    }
  }
}

/**
 * Pick the index separator for one entry: reuse the matched line's style, else
 * the section's dominant style (`: ` or ` — `), else the canonical colon.
 * @param {string[]} section - existing entry lines of the index section.
 * @param {string | undefined} matched - the line being refreshed, when present.
 * @returns {string} the separator text before the summary.
 */
function indexSeparator(section, matched) {
  if (matched !== undefined && matched.includes(' — ')) return ' —'
  const dashes = section.filter(line => line.includes(' — ')).length
  const colons = section.filter(line => /: /.test(line)).length
  return dashes > colons ? ' —' : ':'
}

/**
 * Read a JSON file, returning the fallback when absent.
 * @param {string} path - absolute file path.
 * @param {T} fallback - value when the file is missing.
 * @returns {Promise<T>}
 * @template T
 */
async function readJson(path, fallback) {
  try {
    return JSON.parse(await readFile(path, 'utf8'))
  } catch (error) {
    if (error.code === 'ENOENT') return fallback
    throw error
  }
}

/**
 * Recursively collect every Markdown page under a directory with title and wikilinks.
 * @param {string} directory - absolute directory to walk.
 * @returns {Promise<{ name: string, path: string, rel: string, fields: Record<string, unknown> | undefined, content: string, links: string[] }[]>}
 */
export async function collectMarkdown(directory) {
  const pages = []
  let entries
  try {
    entries = await readdir(directory, { withFileTypes: true })
  } catch (error) {
    if (error.code === 'ENOENT') return pages
    throw error
  }
  for (const entry of entries) {
    const path = join(directory, entry.name)
    if (entry.isDirectory()) {
      pages.push(...await collectMarkdown(path))
    } else if (entry.isFile() && entry.name.endsWith('.md')) {
      const { fields, content } = splitFrontmatter(await readFile(path, 'utf8'), path)
      pages.push({
        name: entry.name.slice(0, -3),
        path,
        rel: relative(directory, path).split(sep).join('/'),
        fields,
        content,
        links: extractWikilinks(content),
        aliases: frontmatterAliases(fields),
      })
    }
  }
  pages.sort((left, right) => left.name.localeCompare(right.name))
  return pages
}

/**
 * Read a page's declared `aliases` frontmatter field (Obsidian resolves these
 * as link targets): a string or list of strings.
 * @param {Record<string, unknown> | undefined} fields - parsed frontmatter.
 * @returns {string[]} declared aliases, empty when absent or malformed.
 */
function frontmatterAliases(fields) {
  const raw = fields?.aliases
  if (typeof raw === 'string') return raw.trim().length > 0 ? [raw.trim()] : []
  if (Array.isArray(raw)) return raw.filter(alias => typeof alias === 'string' && alias.trim().length > 0).map(alias => alias.trim())
  return []
}

/**
 * Build the alias resolution map every link consumer shares: alias → page
 * title. Earlier pages win a duplicate alias, deterministically, because
 * {@link collectMarkdown} sorts by name.
 * @param {{ name: string, aliases?: string[] }[]} pages - collected pages.
 * @returns {Map<string, string>} alias → owning page title.
 */
export function buildAliasMap(pages) {
  const map = new Map()
  for (const page of pages) {
    for (const alias of page.aliases ?? []) {
      if (!map.has(alias)) map.set(alias, page.name)
    }
  }
  return map
}

/**
 * Resolve one wikilink target to a page title: direct name hit first, then the
 * alias map (Obsidian's resolution order).
 * @param {string} target - the raw link target.
 * @param {Set<string>} names - every page title.
 * @param {Map<string, string>} aliases - alias → page title.
 * @returns {string | undefined} the resolved page title, or undefined when dead.
 */
export function resolveLinkTarget(target, names, aliases) {
  if (names.has(target)) return target
  return aliases.get(target)
}

/**
 * Extract wikilink targets from markdown, dropping aliases and heading anchors.
 * Fenced code blocks and inline code spans are not links: examples written as
 * `` `[[Target]]` `` must not join the graph.
 * @param {string} content - markdown body.
 * @returns {string[]} link targets in order of appearance.
 */
export function extractWikilinks(content) {
  const links = []
  const withoutCode = content
    .replace(/```[\s\S]*?```/g, '')
    .replace(/`[^`\n]*`/g, '')
  for (const match of withoutCode.matchAll(/\[\[([^\]]+)\]\]/g)) {
    const target = match[1].split('|')[0].split('#')[0].trim()
    if (target.length > 0) links.push(target)
  }
  return links
}

/**
 * Whether a page basename is vault machinery rather than content: the index,
 * log, hot cache, overview, per-folder sub-indexes, and dated lint reports.
 * Lint reports quote past issues verbatim, so their wikilinks are records, not
 * graph edges.
 * @param {string} name - page basename without extension.
 * @returns {boolean} whether the page is machinery.
 */
export function isMachineryPage(name) {
  const lowered = name.toLowerCase()
  return META_FILENAMES.has(lowered)
    || name.startsWith('_')
    || lowered.startsWith('_')
    // Case-insensitive with a real boundary: reports have been hand-retitled
    // to "Lint Report …" in real sessions, and those are still machinery —
    // but "Lint Reporter Profile" is content.
    || /^lint[- _]?report([- _].+)?$/i.test(name)
}
