import { type FontFace } from './fonts.ts';
import type { ResolvedOptions } from './options.ts';
export type FontFileFormat = 'ttf' | 'otf' | 'ttc';
export declare function fontFileFormat(bytes: Uint8Array): FontFileFormat;
/** Keep full names, encoding tables and glyphs. Apple dfont containers expose one complete sfnt resource. */
export declare function fullFontFile(face: FontFace): {
    bytes: Uint8Array;
    sourceHash: string;
    format: FontFileFormat;
};
/** Mount a fixed bounded set before PDFium performs its first installed-font enumeration. */
export declare function preloadPdfFonts(options: ResolvedOptions, faces: readonly FontFace[], install: (name: string, bytes: Uint8Array) => void): void;
