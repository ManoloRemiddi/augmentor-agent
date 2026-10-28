/** Shared bounded raster allocations for browser and Node engine owners. */
import { type EnginePage, type RasterTile, type TileRequest } from './rendering.ts';
export interface RasterModule {
    readonly HEAPU32: Uint32Array;
    ccall(name: string, returnType: string | null, argTypes: string[], args: unknown[]): number;
    UTF8ToString(pointer: number): string;
}
export declare function numericCall(module: RasterModule, name: string, args: number[]): number;
/** Copy/free one engine-owned UTF-8 return value. */
export declare function engineString(module: RasterModule, name: string, types: string[], args: unknown[], failure: () => Error): string;
/** Paint into a temporary allocation; copy pixels before free or another engine call. */
export declare function renderRegion(module: RasterModule, document: number, request: TileRequest, pages: readonly EnginePage[], failure: () => Error, pdf?: boolean): RasterTile;
/** PDF page dimensions use the same twips ABI, with an immutable PDF page index as part. */
export declare function pdfPages(module: RasterModule, pdf: number, failure: () => Error): EnginePage[];
