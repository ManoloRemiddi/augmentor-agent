import type { FontFace } from './fonts.ts';
import type { FontResolutionCacheEntry } from './font-loader.ts';
import type { DocumentFontMetadata } from './ooxml.ts';
import type { ResolvedOptions } from './options.ts';
import type { ConversionSpec } from './operations.ts';
import type { WasmEngine } from './engine.ts';
/** MEMFS operations the conversion uses inside the Emscripten module. */
interface EmscriptenFileSystem {
    /**
     * @param path - Absolute MEMFS path.
     */
    mkdirTree(path: string): void;
    /**
     * @param path - Absolute MEMFS path.
     * @param data - Complete file contents.
     */
    writeFile(path: string, data: Uint8Array): void;
    /**
     * @param path - Absolute MEMFS path.
     * @returns whether the path exists.
     */
    analyzePath(path: string): {
        exists: boolean;
    };
    /**
     * @param path - Absolute MEMFS path.
     * @returns the stat record the conversion inspects.
     */
    stat(path: string): {
        mode: number;
        size: number;
    };
    /**
     * @param mode - Stat mode flags.
     * @returns whether the mode flags describe a regular file.
     */
    isFile(mode: number): boolean;
    /**
     * @param path - Absolute MEMFS path.
     * @returns the complete file contents.
     */
    readFile(path: string): Uint8Array;
}
/** The Emscripten module surface the conversion drives. */
export interface EmscriptenModule {
    readonly HEAPU32: Uint32Array;
    readonly FS: EmscriptenFileSystem;
    readonly ENV: Record<string, string>;
    /**
     * @param name - Exported C function name.
     * @param returnType - Emscripten return type, or null for void.
     * @param argTypes - Emscripten argument types.
     * @param args - Call arguments.
     * @returns the exported function's numeric result.
     */
    ccall(name: string, returnType: string | null, argTypes: string[], args: unknown[]): number;
    /**
     * @param pointer - Pointer returned by the module.
     * @returns the NUL-terminated UTF-8 string at the pointer.
     */
    UTF8ToString(pointer: number): string;
    readonly PThread: {
        /** Stop every pthread the module started. */
        terminateAllThreads(): void;
    };
}
/** One conversion request executed inside the Node worker. */
export interface WasmConversionRequest {
    readonly engine: WasmEngine;
    readonly bytes: Uint8Array;
    readonly extension: string;
    readonly operation?: Pick<ConversionSpec, 'format' | 'recalculate' | 'sheet'>;
    readonly options: ResolvedOptions;
    readonly document: DocumentFontMetadata;
    readonly faces: readonly FontFace[];
    readonly fontCache?: readonly FontResolutionCacheEntry[];
    readonly onFontCache?: (entries: FontResolutionCacheEntry[]) => void;
}
/** Owned PDF bytes and declared families the installed catalog could not provide. */
export interface WasmConversionResult {
    readonly output: Uint8Array;
    readonly missingFonts: string[];
}
export declare function engineError(module: EmscriptenModule, office: number): Error;
/**
 * Convert bounded source bytes; return owned PDF bytes only after engine teardown.
 * @param request - Engine installation, source bytes, limits, and font metadata.
 * @returns the generated PDF bytes and the declared families the catalog could not provide.
 */
export interface WasmSession {
    readonly module: EmscriptenModule;
    readonly office: number;
    readonly document: number;
    readonly pdf: boolean;
    readonly missingFonts: string[];
    idle(): Promise<void>;
}
/** A single module loader and owned session lifecycle for export and direct raster operations. */
export declare function withWasmSession<T>(request: Omit<WasmConversionRequest, 'operation'>, use: (session: WasmSession) => Promise<T> | T): Promise<T>;
/** Convert bounded source bytes; return owned bytes only after engine teardown. */
export declare function convertWithWasm(request: WasmConversionRequest): Promise<WasmConversionResult>;
export {};
