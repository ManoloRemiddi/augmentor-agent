/** Platform-independent document geometry and raster pixel conversion. */
import type { Rectangle } from './sheet-geometry.ts';
export declare const TWIPS_PER_CSS_PIXEL = 15;
export declare const MAX_TILE_PIXELS: number;
export interface EnginePage {
    readonly width: number;
    readonly height: number;
    readonly x: number;
    readonly y: number;
    readonly part: number;
}
export interface TileRequest {
    readonly pageIndex: number;
    readonly x: number;
    readonly y: number;
    readonly width: number;
    readonly height: number;
    readonly scale: number;
}
export interface RasterTile {
    readonly width: number;
    readonly height: number;
    readonly rgba: Uint8ClampedArray;
}
/** Split a region on its output-pixel grid, bounding the plan before allocating it. */
export declare function splitRasterRectangle(rectangle: Rectangle, scale: number, limits: {
    readonly maxPixels: number;
    readonly maxDimension: number;
    readonly maxTiles: number;
}): Rectangle[];
/** Writer's zero-area parity placeholders have no visible page. Offsets stay in twips. */
export declare function writerPages(rectangles: string): EnginePage[];
/** Validate coordinates before allocation or wasm32 integer conversion. */
export declare function tileDimensions(request: TileRequest, pages: readonly EnginePage[]): {
    page: EnginePage;
    width: number;
    height: number;
};
/** Cairo/LO channels are premultiplied; PNG and ImageData require straight RGBA. */
export declare function rgbaPixels(source: Uint8Array, tileMode: number): Uint8ClampedArray;
