import type { FontSnapshot } from './font-snapshot.ts';
/** Reject changed, removed, or replaced sources without exposing local font paths. */
export declare function validateFontSnapshot(snapshot: FontSnapshot): Promise<void>;
