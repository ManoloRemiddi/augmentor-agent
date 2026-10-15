/** Exact filesystem identifiers with JSON-compatible font metadata. */
import type { BigIntStats } from 'node:fs';
/** Preserve 64-bit device and inode values without JavaScript integer rounding. */
export declare function fontFileIdentity(status: BigIntStats): {
    dev: string;
    ino: string;
    size: number;
    mtimeMs: number;
    ctimeMs: number;
};
/** Compare a source descriptor's exact identity with its indexed font metadata. */
export declare function matchesFontFile(status: BigIntStats, expected: ReturnType<typeof fontFileIdentity>): boolean;
