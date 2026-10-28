/** Validated deployment limits shared by native and Node WASM conversions. */
import type { ConverterOptions } from './index.ts';
/** Ordered family groups used when the caller supplies none. */
export declare const FONT_FALLBACKS: readonly (readonly string[])[];
/** Resolved limits and font settings used by every conversion of one converter. */
export interface ResolvedOptions {
    readonly fontMetadataCacheDirectory: string | false;
    readonly maxFontMetadataCacheBytes: number;
    readonly timeoutMs: number;
    readonly maxInputBytes: number;
    readonly maxOutputBytes: number;
    readonly maxImageResolution: number;
    readonly maxArchiveEntries: number;
    readonly maxUncompressedBytes: number;
    readonly maxFontFiles: number;
    readonly maxFontFileBytes: number;
    readonly maxLoadedFontBytes: number;
    readonly maxFontResolutionEntries: number;
    readonly fontDirectories: string[];
    readonly includeOfficeFonts: boolean;
    readonly fontFallbacks: string[][];
    readonly initialFontFamilies: string[];
}
/**
 * Resolve defaults once; reject misspelled options and malformed font settings.
 * @param input - Caller options; absent fields keep their documented default.
 * @returns The validated limits and font settings, with caller arrays copied.
 * @throws TypeError for a non-object argument or an unknown option name.
 * @throws RangeError for a limit outside the positive safe-integer timer range.
 */
export declare function resolveOptions(input?: ConverterOptions): ResolvedOptions;
