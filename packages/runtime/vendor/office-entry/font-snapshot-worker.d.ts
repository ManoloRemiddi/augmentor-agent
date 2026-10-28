import type { FontFileMetadata } from './fonts.ts';
import type { ResolvedOptions } from './options.ts';
/** Private input supplied by the shared scan owner. */
export interface FontSnapshotRequest {
    readonly options: ResolvedOptions;
    readonly previous: readonly FontFileMetadata[];
    readonly temporaryPath?: string;
}
