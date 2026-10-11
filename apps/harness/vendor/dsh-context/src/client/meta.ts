/** Build-time defines (tsdown.config.ts); the typeof guards cover a bundle built without them. */

declare const __DSH_CTX_VERSION__: string | undefined
declare const __DSH_CTX_REPO__: string | undefined

export const PLUGIN_NAME = 'dsh-context'
export const PLUGIN_VERSION: string =
  typeof __DSH_CTX_VERSION__ === 'string' ? __DSH_CTX_VERSION__ : '0.0.0-dev'
export const PLUGIN_REPO: string =
  typeof __DSH_CTX_REPO__ === 'string' ? __DSH_CTX_REPO__ : 'https://github.com/bowenliang123/dsh-context'
export const PLUGIN_REPO_SHORT = PLUGIN_REPO.replace(/^https?:\/\/github\.com\//, '')
