import type { FontFace } from './fonts.ts';
/** @returns whether parsed font names belong to the curated Office compatibility set. */
export declare function officeFontFace(face: Pick<FontFace, 'aliases'>): boolean;
/** Find compatibility font files without exposing their paths outside the font Worker. */
export declare function officeFontFiles(platform?: NodeJS.Platform, home?: string, env?: NodeJS.ProcessEnv, applicationRoots?: readonly string[]): string[];
