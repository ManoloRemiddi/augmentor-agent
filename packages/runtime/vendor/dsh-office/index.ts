// Copyright © 2026 Manolo Remiddi. MIT supplier adaptation: Pi lifecycle/authorized byte-reader seat replaces Cordis, schema defaults and Typert decorators; original queue/scratch/error logic retained. Active teardown is exposed for maintenance; font disk cache is disabled. An explicit converter seat preserves the lazy pinned default and admits an authored native adapter.
/** Host LibreOffice kit provider with reusable converters and private disk input/output. */
import { randomUUID } from 'node:crypto'
import { mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { extname, isAbsolute, join } from 'node:path'
import type { ConverterOptions } from '@deepseek-ai/libreoffice-kit'
import type { OfficePreviewSeat as Context, WorkspaceFileScope, WorkspaceFileStat } from '../../src/office-preview.js'
import { brandString } from './brand.js'
import { PreviewReadError as RemoteError } from '../../src/file-preview.js'
import { OfficeToPdfError } from './errors.js'
import { OfficeToPdfGeneration, type OfficeSourceKey } from './identity.js'
import type { OfficeExtension, OfficeToPdfRequest, OfficeToPdfResult, OfficeToPdfPriority, RenderedDocumentBytes } from './types.js'
import { readPdf } from './output.js'
import { ConversionQueue } from './queue.js'

export * from './errors.js'
export * from './identity.js'
export * from './types.js'

/** Backend seat used by the original provider; no image/agent API is needed. */
export interface OfficeConverter {
  render(request: { inputPath: string; outputPath: string }, signal?: AbortSignal): Promise<{ missingFonts: string[] }>
  dispose(): Promise<void>
}
export type OfficeConverterFactory = (options: ConverterOptions) => Promise<OfficeConverter>
const pinnedConverter: OfficeConverterFactory = async options => (await import('@deepseek-ai/libreoffice-kit')).createConverter(options)

/** Provider concurrency and kit rendering/font configuration. */
export interface Config {
  /** Explicit backend seat; absence retains the pinned kit. */
  converterFactory?: OfficeConverterFactory
  /** Maximum simultaneous conversions; queued callers remain cancellable. */
  maxConcurrentConversions: number
  /** Maximum metadata-only jobs awaiting source admission. */
  maxQueuedJobs: number
  /** Maximum outstanding conversion readers. */
  maxReaders: number
  /** Maximum reserved bytes across admitted source reads and conversions. */
  maxSourceBytes: number
  /** Maximum concurrent background jobs; zero refuses speculative work. */
  maxBackgroundConversions: number
  /** Maximum retained content-addressed PDFs. */
  maxCachedEntries: number
  /** Maximum retained PDF bytes. */
  maxCachedBytes: number
  /** Maximum retained source-version aliases to cached content. */
  maxSourceEntries: number
  /** Conversion deadline in milliseconds; excludes the DSH queue. */
  timeoutMs: number
  /** Maximum authorized source bytes. */
  maxInputBytes: number
  /** Maximum complete PDF bytes. */
  maxOutputBytes: number
  /** Exported raster-image DPI. */
  maxImageResolution: number
  /** Maximum OOXML ZIP entries. */
  maxArchiveEntries: number
  /** Maximum total declared uncompressed OOXML bytes. */
  maxUncompressedBytes: number
  /** Absolute font roots; omission uses the kit's platform defaults. */
  fontDirectories?: string[]
  /** Ordered font-family preference groups; omission retains the kit defaults. */
  fontFallbacks?: string[][]
  /** Maximum physical font files indexed by each converter. */
  maxFontFiles: number
  /** Maximum individual font-file bytes. */
  maxFontFileBytes: number
  /** Maximum original font bytes loaded for a conversion. */
  maxLoadedFontBytes: number
}

interface Slot {
  busy: boolean
  converter?: Promise<OfficeConverter>
}

/** A provider lifetime owns all converters, queued calls, and temporary files. */
export class OfficeToPdf {
  /** Changes whenever engine, font, or conversion configuration is replaced. */
  readonly generation: OfficeToPdfGeneration = OfficeToPdfGeneration(randomUUID())
  private readonly remoteLifetime = new AbortController()
  private readonly remoteRequests = new Set<Promise<RenderedDocumentBytes>>()
  private readonly slots: Slot[] = []
  private readonly queue: ConversionQueue
  private readonly options: ConverterOptions

  /**
   * @param ctx - owning Host context.
   * @param config - resolved rendering, font, and concurrency limits.
   */
  constructor(private readonly ctx: Context, private readonly config: Config) {
    if (config.fontDirectories?.some(path => !isAbsolute(path))) throw new Error('fontDirectories must contain absolute paths.')
    if (config.maxSourceBytes < config.maxInputBytes) throw new Error('maxSourceBytes must be at least maxInputBytes.')
    const { fontDirectories, fontFallbacks, timeoutMs, maxInputBytes, maxOutputBytes, maxImageResolution,
      maxArchiveEntries, maxUncompressedBytes, maxFontFiles, maxFontFileBytes, maxLoadedFontBytes } = config
    this.options = { fontMetadataCacheDirectory: false, timeoutMs, maxInputBytes, maxOutputBytes, maxImageResolution, maxArchiveEntries, maxUncompressedBytes,
      maxFontFiles, maxFontFileBytes, maxLoadedFontBytes,
      ...(fontDirectories === undefined ? {} : { fontDirectories }),
      ...(fontFallbacks === undefined ? {} : { fontFallbacks }),
    }
    this.queue = new ConversionQueue(config, this.generation, (bytes, extension, signal) => this.convertBytes(bytes, extension, signal))
    ctx.effect(() => async () => {
      this.remoteLifetime.abort()
      await this.queue.dispose()
      await Promise.allSettled(this.remoteRequests)
      const results = await Promise.allSettled(this.slots.map(async (slot) => {
        const converter = await slot.converter
        await converter?.dispose()
      }))
      const failures = results.filter(result => result.status === 'rejected')
      if (failures.length > 0) throw new AggregateError(failures.map((result): unknown => result.reason), 'LibreOffice converter disposal failed.')
    })
  }

  /**
   * Convert Office bytes without modifying the source or writing Session events.
   * @param request - authorized metadata and deferred bounded source read.
   * @param signal - caller cancellation; provider disposal also stops active work.
   * @returns caller-owned PDF bytes after conversion and scratch cleanup settle; canceled readers reject independently.
   * @throws {OfficeToPdfError} Invalid input, unusable output, or engine failure; cancellation rejects with its reason.
   */
  convert(request: OfficeToPdfRequest, signal?: AbortSignal): Promise<OfficeToPdfResult> {
    return this.queue.read(request, signal)
  }

  /**
   * Read and convert one Office file using the Session's ordinary filesystem authorization.
   * @param workspaceFileScope - Session header lookup shared with workspaceFiles.
   * @param path - absolute or workspace-relative Office path.
   * @param priority - foreground preview or speculative background work.
   * @param signal - Remote cancellation; disposal also cancels outstanding reads and conversions.
   * @returns complete PDF bytes with original source identity and missing font families.
   */
  async render(
    workspaceFileScope: WorkspaceFileScope, path: string, priority: OfficeToPdfPriority, signal: AbortSignal,
  ): Promise<RenderedDocumentBytes> {
    const upstream = AbortSignal.any([signal, this.remoteLifetime.signal])
    const operation = this.renderFile(workspaceFileScope, path, priority, upstream)
    this.remoteRequests.add(operation)
    try { return await operation } finally { this.remoteRequests.delete(operation) }
  }

  /**
   * Read the current rendering generation before reusing a Client PDF.
   * @param signal - Remote caller cancellation.
   * @returns provider lifetime, replaced with rendering, font, or engine configuration.
   */
  getGeneration(signal: AbortSignal): OfficeToPdfGeneration { signal.throwIfAborted(); return this.generation }

  /** Pi maintenance retains admission until converter and scratch teardown settle. */
  get busy(): boolean { return this.queue.busy || this.remoteRequests.size > 0 || this.slots.some(slot => slot.busy) }

  private async renderFile(
    scope: WorkspaceFileScope, path: string, priority: OfficeToPdfPriority, signal: AbortSignal,
  ): Promise<RenderedDocumentBytes> {
    try {
      signal.throwIfAborted()
      const extension = extname(path).slice(1).toLowerCase()
      if (extension !== 'doc' && extension !== 'docx' && extension !== 'xls'
        && extension !== 'xlsx' && extension !== 'ppt' && extension !== 'pptx') {
        throw new OfficeToPdfError('unsupported-format', 'The path must end in doc, docx, xls, xlsx, ppt, or pptx.')
      }
      const files = this.ctx.get('workspaceFiles')
      if (files === undefined) throw new OfficeToPdfError('unavailable', 'Office file rendering requires authorized workspaceFiles.')
      const authorized = await files.readBytes(scope, path, { range: { offset: 0, length: 1 } }, signal)
      const source = await files.stat(scope, path, signal)
      const assertUnchanged = (current: WorkspaceFileStat): void => {
        if (current.absolutePath !== source.absolutePath || current.version !== source.version) {
          throw new OfficeToPdfError('source-changed', 'The source changed.')
        }
      }
      assertUnchanged(authorized)
      signal.throwIfAborted()
      const result = await this.convert({ extension, priority, source: {
        key: brandString<OfficeSourceKey>(JSON.stringify([scope.sessionId, scope.workspaceRoot, source.absolutePath])),
        version: source.version, ...(source.bytes === undefined ? {} : { bytes: source.bytes }),
        read: async (upstream, maxBytes) => {
          const read = await files.readBytes(scope, source.absolutePath, { expectedVersion: source.version }, upstream)
          upstream.throwIfAborted()
          assertUnchanged(read)
          if (read.data.byteLength > maxBytes) throw new OfficeToPdfError('input-too-large', 'The source exceeds the reserved byte capacity.')
          return { bytes: read.data, version: read.version }
        },
      } }, signal)
      signal.throwIfAborted()
      return { absolutePath: source.absolutePath, version: source.version,
        offset: 0, eof: true, bytes: result.pdf.byteLength, data: result.pdf,
        missingFonts: result.missingFonts, generation: result.generation }
    } catch (cause) {
      if (signal.aborted) throw new RemoteError('gateway/cancelled', 'The document preview was cancelled.')
      if (cause instanceof OfficeToPdfError) {
        throw new RemoteError('document-render/failed', 'Office conversion failed.', { reason: cause.code })
      }
      throw cause
    }
  }

  private async convertBytes(bytes: Uint8Array, extension: OfficeExtension, signal: AbortSignal): Promise<Pick<OfficeToPdfResult, 'pdf' | 'missingFonts'>> {
    signal.throwIfAborted()
    let slot = this.slots.find(candidate => !candidate.busy)
    if (slot === undefined) { slot = { busy: false }; this.slots.push(slot) }
    slot.busy = true
    let directory: string | undefined
    try {
      if (slot.converter === undefined) {
        slot.converter = (this.config.converterFactory ?? pinnedConverter)(this.options).catch((error: unknown) => {
          delete slot.converter
          throw error
        })
      }
      const converter = await slot.converter
      signal.throwIfAborted()
      directory = await mkdtemp(join(tmpdir(), 'dsh-office-to-pdf-'))
      const inputPath = join(directory, `source.${extension}`)
      const outputPath = join(directory, 'converted.pdf')
      await writeFile(inputPath, bytes, { flag: 'wx', mode: 0o600, signal })
      signal.throwIfAborted()
      const result = await converter.render({ inputPath, outputPath }, signal)
      signal.throwIfAborted()
      let pdf: Uint8Array
      try { pdf = await readPdf(outputPath, this.config.maxOutputBytes, signal) }
      catch (cause) {
        if (cause instanceof OfficeToPdfError) throw cause
        throw new OfficeToPdfError('invalid-output', 'The converter PDF could not be read.', { cause })
      }
      signal.throwIfAborted()
      return { pdf, missingFonts: result.missingFonts }
    } catch (cause) {
      signal.throwIfAborted()
      if (cause instanceof OfficeToPdfError) throw cause
      const code = typeof cause === 'object' && cause !== null && 'code' in cause ? cause.code : undefined
      switch (code) {
        case 'input-too-large': case 'output-too-large': case 'invalid-document': case 'unsupported-format':
        case 'invalid-output': case 'timeout': case 'unavailable':
          throw new OfficeToPdfError(code, 'LibreOffice conversion failed.', { cause })
        default: throw new OfficeToPdfError('failed', 'LibreOffice conversion failed.', { cause })
      }
    } finally {
      try { if (directory !== undefined) await rm(directory, { recursive: true, force: true }) }
      finally { slot.busy = false }
    }
  }
}

export default OfficeToPdf
