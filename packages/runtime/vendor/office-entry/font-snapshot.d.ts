import type { FontFace, FontFileMetadata } from './fonts.ts';
import type { ResolvedOptions } from './options.ts';
/** Immutable metadata handed to one operation; generation excludes document-specific matches. */
export interface FontSnapshot {
    readonly faces: FontFace[];
    readonly records: FontFileMetadata[];
    readonly generation: string;
}
/** Re-enumerate all configured sources; only unchanged physical files skip inspection. */
export declare function scanFontSnapshot(options: ResolvedOptions, previous?: readonly FontFileMetadata[]): FontSnapshot;
