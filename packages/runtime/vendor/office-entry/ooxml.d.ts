import type { ResolvedOptions } from './options.ts';
/** Declared font families and scalar values one inspected document carries. */
export interface DocumentFontMetadata {
    /** Normalized family key to the family name as the document declared it. */
    readonly families: Map<string, string>;
    readonly codePoints: readonly number[];
}
/**
 * Validate ZIP size and membership before decoding selected document XML.
 * @param bytes - Complete source document bytes.
 * @param extension - Input extension, which selects the main document part.
 * @param limits - Archive entry and declared uncompressed byte limits.
 * @returns declared font families and the scalar values readable document XML declares.
 * @throws ConversionError when the extension is unsupported or the archive violates its limits.
 */
export declare function inspectDocument(bytes: Uint8Array, extension: string, limits: Pick<ResolvedOptions, 'maxArchiveEntries' | 'maxUncompressedBytes'>): DocumentFontMetadata;
