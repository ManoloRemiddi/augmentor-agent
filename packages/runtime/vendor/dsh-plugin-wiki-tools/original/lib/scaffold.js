/**
 * Vault scaffolding: the mechanical half of the wiki skill's SCAFFOLD
 * operation as one call. Creates the mode's folder structure, the core wiki
 * files (index, log, hot cache, overview), per-folder sub-indexes, the mode's
 * key seed pages, the vault AGENTS.md conventions file, and the raw-source
 * manifest. Idempotent: existing files are kept and reported as skipped.
 *
 * @module dsh-plugin-wiki-tools/lib/scaffold
 */

import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { readFile } from 'node:fs/promises'
import { today } from './vault.js'

/**
 * Folder sets per scaffold mode. `generic` matches the wiki_write routing
 * (TYPE_FOLDERS); the six named modes follow the wiki skill's modes reference.
 * `stubFolder` holds the mode's overview page; `stubs` are the key pages the
 * mode's reference lists, each seeded into the folder named alongside it.
 */
export const SCAFFOLD_MODES = {
  generic: {
    label: 'Generic knowledge base',
    folders: ['wiki/sources', 'wiki/entities', 'wiki/concepts', 'wiki/domains', 'wiki/questions', 'wiki/comparisons', 'wiki/meta'],
    stubs: [],
    typeFolders: {},
  },
  sitemap: {
    label: 'Website / sitemap',
    folders: ['wiki/pages', 'wiki/structure', 'wiki/audits', 'wiki/keywords', 'wiki/entities'],
    stubs: [
      { title: 'Site Overview', folder: 'wiki/structure', type: 'page' },
      { title: 'Navigation Structure', folder: 'wiki/structure', type: 'page' },
      { title: 'Content Gaps', folder: 'wiki/audits', type: 'page' },
      { title: 'Redirect Map', folder: 'wiki/audits', type: 'page' },
      { title: 'Keyword Clusters', folder: 'wiki/keywords', type: 'page' },
    ],
    typeFolders: { source: 'wiki/pages', entity: 'wiki/entities' },
  },
  repository: {
    label: 'GitHub / repository',
    folders: ['wiki/modules', 'wiki/components', 'wiki/decisions', 'wiki/dependencies', 'wiki/flows'],
    stubs: [
      { title: 'Architecture Overview', folder: 'wiki/modules', type: 'module' },
      { title: 'Data Flow', folder: 'wiki/flows', type: 'flow' },
      { title: 'Tech Stack', folder: 'wiki/dependencies', type: 'dependency' },
      { title: 'Dependency Graph', folder: 'wiki/dependencies', type: 'dependency' },
      { title: 'Key Decisions', folder: 'wiki/decisions', type: 'decision' },
    ],
    typeFolders: { source: 'wiki/modules', comparison: 'wiki/decisions' },
  },
  business: {
    label: 'Business / project',
    folders: ['wiki/stakeholders', 'wiki/decisions', 'wiki/deliverables', 'wiki/intel', 'wiki/comms'],
    stubs: [
      { title: 'Project Overview', folder: 'wiki/deliverables', type: 'deliverable' },
      { title: 'Stakeholder Map', folder: 'wiki/stakeholders', type: 'stakeholder' },
      { title: 'Decision Log', folder: 'wiki/decisions', type: 'decision' },
      { title: 'Competitor Landscape', folder: 'wiki/intel', type: 'competitor' },
    ],
    typeFolders: { entity: 'wiki/stakeholders', source: 'wiki/comms', decision: 'wiki/decisions' },
  },
  personal: {
    label: 'Personal / second brain',
    folders: ['wiki/goals', 'wiki/learning', 'wiki/people', 'wiki/areas', 'wiki/resources'],
    stubs: [
      { title: 'North Star', folder: 'wiki/goals', type: 'goal' },
      { title: 'Annual Goals', folder: 'wiki/goals', type: 'goal' },
    ],
    typeFolders: { concept: 'wiki/learning', domain: 'wiki/areas', entity: 'wiki/people', source: 'wiki/resources' },
  },
  research: {
    label: 'Research',
    folders: ['wiki/papers', 'wiki/concepts', 'wiki/entities', 'wiki/thesis', 'wiki/gaps'],
    stubs: [
      { title: 'Research Overview', folder: 'wiki/thesis', type: 'thesis' },
      { title: 'Open Questions', folder: 'wiki/gaps', type: 'gap' },
    ],
    typeFolders: { source: 'wiki/papers', question: 'wiki/gaps', concept: 'wiki/concepts' },
  },
  book: {
    label: 'Book / course',
    folders: ['wiki/characters', 'wiki/themes', 'wiki/concepts', 'wiki/timeline', 'wiki/synthesis'],
    stubs: [
      { title: 'Book Overview', folder: 'wiki/timeline', type: 'chapter' },
      { title: 'My Takeaways', folder: 'wiki/synthesis', type: 'synthesis' },
    ],
    typeFolders: { concept: 'wiki/concepts', question: 'wiki/synthesis' },
  },
}

/**
 * Scaffold one vault for a mode. Every artifact is written only when absent,
 * so re-running after a partial scaffold or over an existing vault is safe.
 * @param {string} root - absolute vault root.
 * @param {object} input - scaffold options.
 * @param {keyof typeof SCAFFOLD_MODES} input.mode - scaffold mode.
 * @param {string} [input.purpose] - one-line vault purpose for overview and AGENTS.md.
 * @returns {Promise<{ mode: string, created: string[], skipped: string[], suggestedTypeFolders: Record<string, string> }>}
 */
export async function scaffoldVault(root, { mode, purpose }) {
  const spec = SCAFFOLD_MODES[mode]
  if (spec === undefined) {
    throw new Error(`wiki-tools: unknown scaffold mode "${mode}"; choose one of ${Object.keys(SCAFFOLD_MODES).join(', ')}`)
  }
  const date = today()
  const created = []
  const skipped = []
  const writeIfAbsent = async (relPath, content) => {
    const path = join(root, relPath)
    if (await readFile(path, 'utf8').then(() => true, () => false)) {
      skipped.push(relPath)
      return
    }
    await mkdir(join(path, '..'), { recursive: true })
    await writeFile(path, content, 'utf8')
    created.push(relPath)
  }

  await writeIfAbsent('.raw/.manifest.json', '{"sources":{}}\n')
  for (const folder of spec.folders) {
    await writeIfAbsent(`${folder}/_index.md`, [
      '---',
      'type: meta',
      `title: "${folder.split('/').pop()} Index"`,
      `updated: ${date}`,
      '---',
      '',
      `# ${folder.split('/').pop()}`,
      '',
    ].join('\n'))
  }

  await writeIfAbsent('wiki/index.md', indexTemplate(date))
  await writeIfAbsent('wiki/log.md', `# Wiki Log\n`)
  await writeIfAbsent('wiki/hot.md', [
    '---',
    'type: meta',
    'title: "Hot Cache"',
    `updated: ${date}`,
    '---',
    '',
    '# Recent Context',
    '',
    `Scaffolded ${date}. ${purpose ?? spec.label}.`,
    '',
  ].join('\n'))
  await writeIfAbsent('wiki/overview.md', [
    '---',
    'type: overview',
    `title: "Overview"`,
    `updated: ${date}`,
    '---',
    '',
    '# Overview',
    '',
    purpose ?? spec.label,
    '',
  ].join('\n'))

  for (const stub of spec.stubs) {
    await writeIfAbsent(`${stub.folder}/${stub.title}.md`, [
      '---',
      `type: ${stub.type}`,
      `title: "${stub.title}"`,
      'status: seed',
      `created: ${date}`,
      `updated: ${date}`,
      'tags:',
      `  - ${stub.type}`,
      '---',
      '',
      `# ${stub.title}`,
      '',
      `Seed page from ${mode} scaffold. Fill in.`,
      '',
    ].join('\n'))
  }

  await writeIfAbsent('AGENTS.md', agentsTemplate(mode, spec.label, purpose, date))

  return { mode, created, skipped, suggestedTypeFolders: spec.typeFolders }
}

/**
 * Master-index template with one empty section per generic type, in catalog
 * order; named-mode vaults keep the same sections for their mapped types.
 * @param {string} date - scaffold date.
 * @returns {string} the index file content.
 */
function indexTemplate(date) {
  const sections = ['Entities', 'Concepts', 'Sources', 'Questions']
  return [
    '---',
    'type: meta',
    'title: "Wiki Index"',
    `updated: ${date}`,
    '---',
    '',
    '# Wiki Index',
    '',
    ...sections.flatMap(section => [`## ${section}`, '']),
  ].join('\n')
}

/**
 * Vault conventions file: the rules every contributing agent follows.
 * @param {string} mode - scaffold mode id.
 * @param {string} label - human-readable mode label.
 * @param {string | undefined} purpose - one-line vault purpose.
 * @param {string} date - scaffold date.
 * @returns {string} the AGENTS.md content.
 */
function agentsTemplate(mode, label, purpose, date) {
  return `# Wiki Vault Conventions

Mode: ${mode} (${label})
Purpose: ${purpose ?? '(fill in)'}
Created: ${date}

## Rules

- Every page uses flat YAML frontmatter: type, title, status, created, updated, tags at minimum.
- status is one of seed | developing | mature | evergreen.
- Wikilinks use [[Note Name]]; filenames are unique across the vault, no paths needed.
- .raw/ holds immutable sources; never modify them.
- wiki/index.md is the master catalog; every page is listed in its section.
- wiki/log.md is append-only; new entries go at the TOP; never edit past entries.
- wiki/hot.md is a ~500-word cache of recent context; overwrite it completely each update.
- Prefer the wiki tools (wiki_query, wiki_write, wiki_rename, wiki_lint) over raw file edits;
  they keep frontmatter, the index, the folder _index.md files, and the log consistent.
- Contradictions between pages get > [!contradiction] callouts on both pages, never silent edits.
`
}
