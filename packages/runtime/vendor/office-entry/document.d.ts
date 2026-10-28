import type { DocumentFontMetadata } from './ooxml.ts';
import type { ResolvedOptions } from './options.ts';
/** Input suffixes accepted by the public converter. */
export declare const DOCUMENT_EXTENSIONS: readonly ["doc", "docx", "odt", "xls", "xlsx", "ods", "ppt", "pptx", "odp"];
/**
 * Inspect the input container before invoking LibreOffice's document importer.
 * Compound-file streams and legacy font tables are interpreted by LibreOffice;
 * they do not supply the API's OOXML font diagnostics.
 * @param bytes - Source bytes already bounded by maxInputBytes.
 * @param extension - Lowercase source suffix.
 * @param limits - Limits applied to ZIP-based document contents.
 * @returns OOXML font metadata, or empty diagnostics for a binary document.
 */
export declare function inspectDocument(bytes: Uint8Array, extension: string, limits: Pick<ResolvedOptions, 'maxArchiveEntries' | 'maxUncompressedBytes'>): DocumentFontMetadata;
