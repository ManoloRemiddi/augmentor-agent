import type { FontResolutionCacheEntry } from './font-loader.ts';
import type { ImageRenderSpec } from './image-operations.ts';
import type { ConversionSpec } from './operations.ts';
import type { Engine } from './engine.ts';
import type { FontFace } from './fonts.ts';
import type { ResolvedOptions } from './options.ts';
/** Worker input: inspected paths, validated limits, the resolved engine, and the current font snapshot. */
export interface WorkerRequest {
    readonly inputPath: string;
    readonly extension: string;
    readonly operation: ConversionSpec | ImageRenderSpec;
    readonly options: ResolvedOptions;
    readonly engine: Engine;
    readonly scratch: string;
    /** Faces the caller's font snapshot revalidated for this conversion. */
    readonly fontFaces: FontFace[];
    readonly fontCache?: FontResolutionCacheEntry[] | undefined;
}
