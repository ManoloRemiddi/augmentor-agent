import { type ImageRenderSpec, type RenderImagesResult } from './image-operations.ts';
import type { FontSubstitution } from './font-loader.ts';
import type { NativeEngine } from './engine.ts';
import type { ResolvedOptions } from './options.ts';
/** Run one native image batch and write final PNGs only after each bounded paint succeeds. */
export declare function renderImagesWithNative(request: {
    readonly engine: NativeEngine;
    readonly options: ResolvedOptions;
    readonly inputPath: string;
    readonly source: Uint8Array;
    readonly scratch: string;
    readonly profile: string;
    readonly fonts: readonly string[];
    readonly substitutions: readonly FontSubstitution[];
    readonly missingFonts: string[];
    readonly operation: ImageRenderSpec;
    readonly signal: AbortSignal;
}): Promise<RenderImagesResult>;
