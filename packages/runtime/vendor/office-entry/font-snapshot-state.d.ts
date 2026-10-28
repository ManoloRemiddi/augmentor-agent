import type { FontSnapshot } from './font-snapshot.ts';
import type { FontFileMetadata } from './fonts.ts';
import type { ResolvedOptions } from './options.ts';
/** Run one scan outside the event loop and join it before returning or cleaning its temporary file. */
export declare function runFontSnapshot(options: ResolvedOptions, previous: readonly FontFileMetadata[], signal: AbortSignal): Promise<FontSnapshot>;
/** Each acquisition refreshes inventory; overlapping acquisitions share only the active scan. */
export declare class FontSnapshotState {
    private previous;
    private scan;
    /** Revalidate files for an operation without coupling its cancellation to other waiters. */
    acquire(options: ResolvedOptions, signal: AbortSignal): Promise<FontSnapshot>;
    /** Release completed metadata after the owning factory has joined its operations. */
    clear(): void;
}
