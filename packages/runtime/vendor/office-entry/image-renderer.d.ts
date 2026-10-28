import { type WasmConversionRequest } from './wasm.ts';
import { type ImageRenderSpec, type RenderImagesResult } from './image-operations.ts';
export declare function renderImagesWithWasm(request: Omit<WasmConversionRequest, 'operation'> & {
    operation: ImageRenderSpec;
}): Promise<RenderImagesResult>;
