/**
 * Wiki Skills — the claude-obsidian-derived knowledge-suite skills for
 * DeepSeek Harness.
 *
 * Mounts the skills bundled in this package's `skills/` directory as a
 * read-only provider on `ctx.skills`. Skill bodies stay plain Markdown files
 * with `name`/`description` YAML frontmatter. Adapted from claude-obsidian
 * (MIT, © 2026 AgriciDaniel); see README.md and ORIGINAL_LICENSE.
 *
 * @module dsh-plugin-wiki-skills
 */

import { readdir, readFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { parse as parseYaml } from 'yaml'

export const name = 'wiki-skills'
export const inject = ['skills']

const SKILL_NAME = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
// Mirrors BUNDLED_SKILL_RANK from @deepseek-ai/dsh-skill: packaged skills lose
// duplicate-name contests against project, runtime, and user registrations.
const BUNDLED_RANK = 600
const DEFAULT_INVOCATION = { modelInvocable: true, userInvocable: true }
const SKILLS_DIR = join(dirname(fileURLToPath(import.meta.url)), 'skills')

/**
 * Register the bundled wiki-skill catalog on `ctx.skills`.
 * @param {import('@deepseek-ai/cordis').Context} ctx - context exposing the skills service.
 * @returns {void}
 */
export function apply(ctx) {
  ctx.skills.registerProvider(() => createProvider())
}

/** Opaque locator carried from `list()` back into `get()`. */
function locatorOf(directory) {
  return { directory, path: join(directory, 'SKILL.md') }
}

/**
 * Build the read-only provider over this package's bundled skills.
 * @returns {import('@deepseek-ai/dsh-skill').SkillProvider} the provider registered under the name `wiki-skills`.
 */
function createProvider() {
  return {
    name,
    /**
     * List every bundled skill candidate. The directory is part of the package,
     * so discovery is one bounded scan whose failures are configuration errors,
     * not partial observations.
     * @param {import('@deepseek-ai/dsh-skill').SkillLookupOptions} options - lookup options whose signal cancels the scan.
     * @returns {Promise<import('@deepseek-ai/dsh-skill').SkillCandidate[]>}
     */
    async list(options) {
      throwIfAborted(options?.signal)
      const entries = await readdir(SKILLS_DIR, { withFileTypes: true })
      const directories = entries
        .filter(entry => entry.isDirectory())
        .map(entry => entry.name)
        .sort()
      const candidates = []
      for (const skillName of directories) {
        const directory = join(SKILLS_DIR, skillName)
        const raw = await readFile(join(directory, 'SKILL.md'), 'utf8')
        const parsed = parseSkillFile(raw, directory)
        if (parsed.name !== skillName) {
          throw new Error(`wiki-skills: directory "${skillName}" holds skill "${parsed.name}"; rename one to match the other`)
        }
        candidates.push({
          name: parsed.name,
          description: parsed.description,
          ...(parsed.whenToUse !== undefined ? { whenToUse: parsed.whenToUse } : {}),
          invocation: DEFAULT_INVOCATION,
          source: 'bundled',
          provider: name,
          resourceBase: { kind: 'directory', path: directory },
          rank: BUNDLED_RANK,
          locator: locatorOf(directory),
          path: join(directory, 'SKILL.md'),
          ...(parsed.metadata !== undefined ? { metadata: parsed.metadata } : {}),
        })
      }
      if (candidates.length === 0) {
        throw new Error(`wiki-skills: no skills found under ${SKILLS_DIR}`)
      }
      return candidates
    },
    /**
     * Load one bundled skill body for a candidate this provider listed.
     * @param {import('@deepseek-ai/dsh-skill').SkillCandidate} candidate - the winning candidate from `list()`.
     * @param {import('@deepseek-ai/dsh-skill').SkillLookupOptions} options - lookup options whose signal cancels the read.
     * @returns {Promise<import('@deepseek-ai/dsh-skill').SkillDefinition | undefined>} the full skill, or `undefined` once the file disappeared.
     */
    async get(candidate, options) {
      throwIfAborted(options?.signal)
      const locator = candidate.locator
      if (locator === undefined || typeof locator !== 'object' || !('path' in locator)) {
        return undefined
      }
      let raw
      try {
        raw = await readFile(locator.path, 'utf8')
      } catch (error) {
        if ((error).code === 'ENOENT' || (error).code === 'ENOTDIR') return undefined
        throw error
      }
      const parsed = parseSkillFile(raw, locator.directory)
      return {
        name: parsed.name,
        description: parsed.description,
        ...(parsed.whenToUse !== undefined ? { whenToUse: parsed.whenToUse } : {}),
        invocation: DEFAULT_INVOCATION,
        source: 'bundled',
        provider: name,
        resourceBase: { kind: 'directory', path: locator.directory },
        path: locator.path,
        ...(parsed.metadata !== undefined ? { metadata: parsed.metadata } : {}),
        content: parsed.content,
      }
    },
  }
}

/**
 * Parse one SKILL.md into registry fields. Malformed frontmatter fails loud:
 * these files ship inside the package, so a defect is a release blocker, not a
 * runtime condition to swallow. Exported for the package tests.
 * @param {string} raw - the complete file text.
 * @param {string} source - path shown in error messages.
 * @returns {{ name: string, description: string, whenToUse?: string, metadata?: Record<string, unknown>, content: string }}
 */
export function parseSkillFile(raw, source) {
  if (!raw.startsWith('---\n')) {
    throw new Error(`wiki-skills: ${source} must open with a --- frontmatter fence`)
  }
  const firstLineEnd = raw.indexOf('\n')
  const rest = raw.slice(firstLineEnd + 1)
  const closing = rest.search(/^---(?:\r?\n|$)/m)
  if (closing < 0) {
    throw new Error(`wiki-skills: ${source} has no closing --- frontmatter fence`)
  }
  const frontmatterText = rest.slice(0, closing)
  const content = rest.slice(closing).replace(/^---\r?\n?/, '')
  let fields
  try {
    fields = parseYaml(frontmatterText)
  } catch (error) {
    throw new Error(`wiki-skills: ${source} has invalid YAML frontmatter: ${error.message}`)
  }
  if (fields === null || typeof fields !== 'object' || Array.isArray(fields)) {
    throw new Error(`wiki-skills: ${source} frontmatter must be a YAML mapping`)
  }
  const { name: skillName, description, whenToUse, ...metadata } = fields
  if (typeof skillName !== 'string' || !SKILL_NAME.test(skillName)) {
    throw new Error(`wiki-skills: ${source} frontmatter needs a kebab-case string "name"`)
  }
  if (typeof description !== 'string' || description.length === 0) {
    throw new Error(`wiki-skills: ${source} frontmatter needs a non-empty string "description"`)
  }
  if (whenToUse !== undefined && typeof whenToUse !== 'string') {
    throw new Error(`wiki-skills: ${source} frontmatter "whenToUse" must be a string`)
  }
  return {
    name: skillName,
    description,
    ...(whenToUse !== undefined ? { whenToUse } : {}),
    ...(Object.keys(metadata).length > 0 ? { metadata } : {}),
    content,
  }
}

/** Throw a total Error for an already-aborted lookup. */
function throwIfAborted(signal) {
  if (signal?.aborted === true) {
    throw signal.reason instanceof Error ? signal.reason : new Error(String(signal.reason))
  }
}
