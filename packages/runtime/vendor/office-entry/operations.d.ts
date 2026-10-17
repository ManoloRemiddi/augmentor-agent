/** Conversions supported by the bundled Writer, Calc, and Impress components. */
export declare const CONVERSION_FORMATS: readonly [{
    readonly inputs: readonly ["doc", "docx", "odt"];
    readonly outputs: readonly ["pdf", "docx", "odt", "txt"];
}, {
    readonly inputs: readonly ["xls", "xlsx", "ods"];
    readonly outputs: readonly ["pdf", "xlsx", "ods", "csv"];
}, {
    readonly inputs: readonly ["ppt", "pptx", "odp"];
    readonly outputs: readonly ["pdf", "pptx", "odp"];
}];
/** Absolute input and fresh output paths, with an exact worksheet name for CSV export. */
export interface ConversionRequest {
    readonly inputPath: string;
    readonly outputPath: string;
    /** CSV only; required for a workbook containing multiple sheets. */
    readonly sheet?: string;
}
/** Engine operation after extension and parameter validation. */
export interface ConversionSpec {
    readonly inputPath: string;
    readonly outputPath: string;
    readonly extension: string;
    readonly format: string;
    readonly recalculate: boolean;
    readonly sheet?: string;
}
/**
 * Validate paths and the format matrix before file access or queue admission.
 * @param request - Public conversion parameters.
 * @param operation - PDF compatibility entry, general conversion, or workbook recalculation.
 * @returns The explicit engine operation.
 */
export declare function resolveConversion(request: ConversionRequest, operation: 'render' | 'convert' | 'recalculate'): ConversionSpec;
/**
 * Reject an engine output with an incorrect container signature.
 * @param bytes - Complete bounded output.
 * @param format - Requested output suffix.
 */
export declare function validateOutput(bytes: Uint8Array, format: string): void;
