import { type Rectangle } from './sheet-geometry.ts';
export declare const IMAGE_FORMATS: readonly ["doc", "docx", "odt", "xls", "xlsx", "ods", "ppt", "pptx", "odp", "pdf"];
export interface RenderImagesRequest {
    readonly inputPath: string;
    /** Must not exist. A failed or cancelled batch removes this entire new directory. */
    readonly outputDir: string;
    /** One-based physical pages/slides; forbidden for worksheets. Default: all. */
    readonly pages?: 'all' | readonly number[];
    /** Calc only. Exact worksheet name. Without it, render each visible worksheet's data area. */
    readonly sheet?: string;
    /** Calc only. A1 rectangle, requiring an exact sheet. Default: A1 through the last data cell. */
    readonly range?: string;
    /** Raster DPI. Default 144, range 24–600. */
    readonly dpi?: number;
    /** Total output image limit, including worksheet fragments. Never truncates. Default: 100. */
    readonly maxPages?: number;
    /** Per-image pixel limit. Default and maximum: 16777216. */
    readonly maxPixels?: number;
    /** Per-image width/height limit in output pixels. Default: 8192. */
    readonly maxDimension?: number;
}
export interface RenderedImage {
    readonly index: number;
    readonly page?: number;
    readonly sheet?: string;
    readonly range?: string;
    readonly rtl?: boolean;
    readonly path: string;
    readonly width: number;
    readonly height: number;
    /** Source rectangle in CSS pixels at 96 DPI, before raster scale. */
    readonly rectangle: Rectangle;
    readonly byteLength: number;
}
export interface RenderImagesResult {
    readonly schemaVersion: 1;
    readonly backend: 'native' | 'wasm';
    readonly rasterEngine: 'libreoffice' | 'pdfium';
    readonly source: 'saved';
    readonly inputPath: string;
    readonly sourceSha256: string;
    readonly dpi: number;
    /** Total physical pages/slides, or visible worksheets; images contains the selected subset. */
    readonly pageCount: number;
    readonly images: readonly RenderedImage[];
    readonly missingFonts: string[];
}
export interface ImageRenderSpec extends RenderImagesRequest {
    readonly kind: 'images';
    readonly extension: string;
    readonly dpi: number;
    readonly maxPages: number;
    readonly maxPixels: number;
    readonly maxDimension: number;
}
export declare function resolveImageRender(request: RenderImagesRequest): ImageRenderSpec;
export declare function selectedPages(pages: 'all' | readonly number[] | undefined, count: number, limit: number): number[];
