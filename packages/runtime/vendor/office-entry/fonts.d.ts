import type { Font, FontCollection } from 'fontkit';
/** One inclusive Unicode range a physical face renders. */
export type GlyphRange = [number, number];
/** Metadata for one physical face, captured without retaining its bytes or glyph coverage. */
export interface FontFace {
    readonly path: string;
    readonly size: number;
    readonly mtimeMs: number;
    readonly ctimeMs: number;
    readonly dev: string;
    readonly ino: string;
    readonly faceIndex: number;
    readonly family: string;
    readonly style: string;
    readonly aliases: string[];
    readonly weight: number;
    readonly width: number;
    readonly italic: boolean;
    readonly fixed: boolean;
    readonly postscriptName: string | null;
    /** Decoded glyph ranges; absent until a match reads this face's coverage. */
    coverage?: GlyphRange[];
}
/** All faces decoded from one unchanged physical file, including an empty parse result. */
export interface FontFileMetadata extends Pick<FontFace, 'path' | 'dev' | 'ino' | 'size' | 'mtimeMs' | 'ctimeMs'> {
    readonly faces: FontFace[];
}
/** VCL attributes LibreOffice requests one family for. */
export interface FontMatchRequest {
    readonly family: string;
    readonly style: string;
    readonly weight: number;
    readonly italic: number;
    readonly width: number;
    readonly pitch: number;
    readonly language: string;
    readonly codePoints: readonly number[];
}
/** Selected physical files and the requested family the catalog could not find. */
export interface FontMatchResult {
    readonly fonts: FontFace[];
    readonly missingFamily?: string;
    readonly unresolvedCodePoints?: number[];
}
/** One host font snapshot and the ordered fallback groups a conversion supplies. */
export interface SystemFontCatalogOptions {
    readonly faces: readonly FontFace[];
    readonly fallbackFamilies: readonly (readonly string[])[];
}
/** Host font roots and physical file limits. */
export interface FontIndexOptions {
    readonly directories: readonly string[];
    readonly maxFiles: number;
    readonly maxFileBytes: number;
}
/**
 * @param error - Thrown filesystem value.
 * @returns whether it means the path is not a usable font source.
 */
export declare function absent(error: unknown): boolean;
/**
 * Case- and separator-insensitive family key used to compare names across sources.
 * @param value - Family, style, or postscript name as recorded by a document or font.
 * @returns The normalized key.
 */
export declare function normalize(value: string): string;
/**
 * Order named substitutions and their generic text family without excluding unlisted fonts.
 * @param requested - Original family names, in document order.
 * @param groups - Ordered family groups shared with Fontconfig aliases.
 * @param pitch - VCL pitch; one requests a monospaced fallback.
 * @param symbols - Whether symbol alternatives precede the generic fallback.
 * @returns distinct family names, with original requests first.
 */
export declare function fontFamilyPriority(requested: readonly string[], groups: readonly (readonly string[])[], pitch?: number, symbols?: boolean): string[];
/**
 * Discover system and per-user font roots using the selected platform's path separators.
 * @param platform - Host operating system.
 * @param home - Host user home used to locate per-user font directories.
 * @param env - Host environment containing Windows and XDG directory overrides.
 * @returns candidate directories; missing platform directories are ignored during indexing.
 */
export declare function systemFontDirectories(platform?: NodeJS.Platform, home?: string, env?: NodeJS.ProcessEnv): string[];
/**
 * Font asset directories macOS publishes under its MobileAsset root.
 * @param assets - Absolute MobileAsset font directory root.
 * @returns matching asset directories, sorted by name.
 * @throws when the root exists but cannot be read for a reason other than its absence or protection.
 */
export declare function mobileAssetFontDirectories(assets: string): string[];
/**
 * Decode glyph coverage for one parsed face.
 * @param font - The parsed physical face.
 * @returns the inclusive ranges the face renders, or none when its glyph tables reject decoding.
 */
export declare function faceCoverage(font: Font): GlyphRange[];
/**
 * @param parsed - Parsed font file: one face, or a collection of faces.
 * @param face - Indexed metadata naming the face inside that file.
 * @returns the physical face the index names.
 * @throws when the file no longer provides the indexed face.
 */
export declare function indexedFace(parsed: Font | FontCollection, face: Pick<FontFace, 'faceIndex' | 'postscriptName'>): Font;
/**
 * VCL weight, width, and fixed-pitch values for one parsed face.
 * @param font - The parsed physical face, whose `OS/2` and `post` tables may be absent.
 * @returns the recorded classes, or the regular defaults for an absent table.
 */
export declare function faceMetrics(font: Pick<Font, 'OS/2' | 'post'>): {
    weight: number;
    width: number;
    fixed: boolean;
};
/**
 * Snapshot eligible local font metadata without retaining font bytes or decoding glyph coverage.
 * @param options - Host font roots and physical file limits.
 * @param previous - Prior per-file records, reused only after opening and checking the current file.
 * @param observed - Receives successfully read records for this scan, including damaged-font parse results.
 * @returns metadata in discovery order for the current font inventory.
 */
export declare function indexSystemFonts(options: FontIndexOptions, previous?: ReadonlyMap<string, FontFileMetadata>, observed?: Map<string, FontFileMetadata>): FontFace[];
/** Conversion-local glyph coverage over one operation's metadata snapshot. */
export declare class SystemFontCatalog {
    private readonly options;
    private readonly faces;
    /**
       * @param options - Host metadata snapshot and fallback families.
       */
    constructor(options: SystemFontCatalogOptions);
    /**
       * Find installed faces covering the requested family or missing characters.
       * Exact families precede configured alternatives, symbol families for missing symbols,
       * generic families, then other glyph-covering faces.
       * @param request - VCL family/style attributes and Unicode scalars missing from its current font.
       * @param signal - cancellation checked between synchronous font reads.
       * @returns selected physical files, deduplicated across collection faces; absent glyphs remain unresolved.
       * @throws if an indexed font changes or cannot be read during glyph matching.
       */
    match(request: FontMatchRequest, signal: AbortSignal): FontMatchResult;
}
/**
 * Read the unchanged indexed regular file; reject concurrent replacement or truncation.
 * @param face - Indexed face metadata whose identity and timestamps must still match the file.
 * @returns the complete original font bytes.
 * @throws when the file changed, was replaced, or was truncated since indexing.
 */
export declare function readFont(face: FontFace): Buffer;
