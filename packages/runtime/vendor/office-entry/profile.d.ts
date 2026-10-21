/** Private headless profile used by both native and WASM conversions. */
/**
 * CSV selection is checked by the engine wrapper before saving; suppress the interactive warning.
 * @param fontNodes - Escaped VCL font-substitution nodes, or an empty string for WASM.
 * @returns The per-operation registry XML; macro execution is independently disabled at load.
 */
export declare function profileXml(fontNodes?: string): string;
