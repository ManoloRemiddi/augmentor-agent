import type { FontFileMetadata } from './fonts.ts';
import type { ResolvedOptions } from './options.ts';
type CacheOptions = Pick<ResolvedOptions, 'fontMetadataCacheDirectory' | 'maxFontMetadataCacheBytes'>;
/** Resolve the platform's user-local cache, independently of font discovery. */
export declare function defaultFontMetadataCacheDirectory(platform?: NodeJS.Platform, home?: string, env?: NodeJS.ProcessEnv): string;
/** Read validated records within the configured byte limit; unusable derived data is a cache miss. */
export declare function readFontMetadataCache(options: CacheOptions): FontFileMetadata[];
/** Atomically publish a bounded snapshot through a caller-owned unique temporary path. */
export declare function writeFontMetadataCache(options: CacheOptions, records: readonly FontFileMetadata[], temporaryPath: string): void;
export {};
