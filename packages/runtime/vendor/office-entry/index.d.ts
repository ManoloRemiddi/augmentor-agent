import type { RenderImagesRequest, RenderImagesResult } from './image-operations.ts';
export { IMAGE_FORMATS } from './image-operations.ts';
export type { RenderImagesRequest, RenderImagesResult, RenderedImage } from './image-operations.ts';
import type { ConversionRequest } from './operations.ts';
export { CONVERSION_FORMATS } from './operations.ts';
export type { ConversionRequest } from './operations.ts';
export { discoverRuntime } from './runtime.ts';
export type { RuntimeInfo } from './runtime.ts';
export { ConversionError } from './errors.ts';
export type { ConversionErrorCode } from './errors.ts';
export { ENGINE_VERSION, ENGINE_VERSIONS } from './engine.ts';
/** Host limits used by both native and Node WASM conversions. All byte limits are positive safe integers. */
export interface ConverterOptions {
    /** User-local font metadata cache directory. Defaults to the platform cache directory; false disables disk reuse. */
    fontMetadataCacheDirectory?: string | false;
    /** Maximum persisted and reusable per-file metadata bytes. Default: 32 MiB. */
    maxFontMetadataCacheBytes?: number;
    /** Deadline after a queued conversion starts, including font work and output. Default: 120000 ms. */
    timeoutMs?: number;
    /** Maximum source bytes. Default: 64 MiB. */
    maxInputBytes?: number;
    /** Maximum generated output bytes. Default: 128 MiB. */
    maxOutputBytes?: number;
    /** PDF export image resolution in DPI. Default: 144. */
    maxImageResolution?: number;
    /** Maximum ZIP entries. Default: 20000. */
    maxArchiveEntries?: number;
    /** Maximum declared uncompressed archive bytes. Default: 512 MiB. */
    maxUncompressedBytes?: number;
    /** Font roots; defaults to conventional platform and user directories. */
    fontDirectories?: string[];
    /** Ordered family groups replace the defaults. Exact installed families precede alternatives; the full indexed
     * catalog remains available for missing glyphs. Native LibreOffice also resolves installed metric-compatible
     * fonts before configured choices. */
    fontFallbacks?: string[][];
    /** Families imported before loading a document. Defaults to none. */
    initialFontFamilies?: string[];
    /** Maximum visited physical font files. Default: 20000. */
    maxFontFiles?: number;
    /** Files exceeding this limit are omitted. Default: 256 MiB. */
    maxFontFileBytes?: number;
    /** Complete original font bytes imported per conversion. Default: 512 MiB. Native platform fonts remain OS-managed. */
    maxLoadedFontBytes?: number;
    /** Maximum font match records retained by each compatible process cache or explicit factory. Default: 4096. */
    maxFontResolutionEntries?: number;
}
/** Result of one conversion. */
export interface RenderResult {
    readonly backend: 'native' | 'wasm';
    /** Declared OOXML families no installed font provides; binary formats return an empty list. */
    readonly missingFonts: string[];
}
/** A converter serializes document operations; cancellation and disposal await process/worker exit. */
export interface Converter {
    readonly backend: 'native' | 'wasm';
    /**
     * Convert a private, caller-authorized regular Office file to a fresh exclusive PDF path.
     * The caller owns both directories and must prevent concurrent path changes.
     * Rejects existing output paths; removes a newly created output on failure or cancellation.
     * @param request - Absolute paths. Input suffixes are listed in CONVERSION_FORMATS.
     * @param signal - Optional cancellation, including while queued.
     * @returns Engine choice and missing declared font families.
     */
    render(request: {
        inputPath: string;
        outputPath: string;
    }, signal?: AbortSignal): Promise<RenderResult>;
    /** Render Office directly to PNG, or PDF through PDFium, in one fresh output directory.
     * Worksheets use sheet/A1 coordinates; page selections are one-based for documents and slides.
     * Failure/cancellation removes the complete batch. The manifest describes one saved input snapshot.
     */
    renderImages(request: RenderImagesRequest, signal?: AbortSignal): Promise<RenderImagesResult>;
    /** Convert to the output extension; CSV requires a sheet for multi-sheet inputs. */
    convert(request: ConversionRequest, signal?: AbortSignal): Promise<RenderResult>;
    /**
     * Recalculate the entire workbook synchronously and save formulas with refreshed cached results.
     * This does not validate formulas or business data.
     * @param request - XLS, XLSX, or ODS input and a distinct fresh XLSX or ODS output.
     * @param signal - Cancellation, including while queued.
     * @returns Engine choice and missing declared font families.
     */
    recalculate(request: Omit<ConversionRequest, 'sheet'>, signal?: AbortSignal): Promise<RenderResult>;
    /** Abort queued and active work, await exit and cleanup, and permanently reject further renders. */
    dispose(): Promise<void>;
}
/** Factory-scoped engine and font metadata shared by concurrent converters. */
export interface ConverterFactory {
    readonly backend: 'native' | 'wasm';
    /** Create one serial converter sharing this factory's bounded font cache. */
    create(): Promise<Converter>;
    /** Abort and join every converter created by this factory. */
    dispose(): Promise<void>;
}
/** Resolve one engine and share its bounded font state across many converters. */
export declare function createConverterFactory(options?: ConverterOptions): Promise<ConverterFactory>;
/** Create one converter with process-shared, configuration-isolated bounded font metadata. */
export declare function createConverter(options?: ConverterOptions): Promise<Converter>;
