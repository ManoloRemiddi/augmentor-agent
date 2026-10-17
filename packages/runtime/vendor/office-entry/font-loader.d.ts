import type { FontFace, FontMatchRequest } from './fonts.ts';
import type { DocumentFontMetadata } from './ooxml.ts';
import type { ResolvedOptions } from './options.ts';
/** Missing-family choices the native helper writes into its private profile. */
export interface FontSubstitution {
    readonly family: string;
    /** Installed family selected for the missing one. */
    readonly substitute: string;
}
/** Serializable match state shared by converters created from one factory. */
export interface FontResolutionCacheEntry {
    readonly key: string;
    readonly codePoints: number[];
    readonly emptyRequest: boolean;
    readonly faces: {
        readonly path: string;
        readonly faceIndex: number;
    }[];
    readonly missingFamily?: string;
}
/** One conversion's font imports: a serialized resolver plus its diagnostics. */
export interface FontLoader {
    readonly missingFonts: string[];
    readonly substitutions: FontSubstitution[];
    readonly files: string[];
    /** Most-recently-used entries safe to merge into the owning factory. */
    readonly cacheEntries: FontResolutionCacheEntry[];
    resolve(request: FontMatchRequest): string[];
}
/** Place installed original bytes where the engine can read them. */
export type FontInstaller = (name: string, bytes: Buffer) => string;
/** Build one operation's loader over a factory-owned immutable font snapshot. */
export declare function createFontLoader(options: ResolvedOptions, document: DocumentFontMetadata, install: FontInstaller, faces: readonly FontFace[], cache?: readonly FontResolutionCacheEntry[]): FontLoader;
/** Supply native imports and seed WASM's first usable default font. */
export declare function preloadFonts(loader: FontLoader, options: ResolvedOptions, document: DocumentFontMetadata, native?: boolean): void;
/** Fontconfig XML restricts WASM discovery to imported originals in MEMFS. */
export declare function memoryFontConfig(families: readonly (readonly string[])[], requested?: Iterable<string>): string;
