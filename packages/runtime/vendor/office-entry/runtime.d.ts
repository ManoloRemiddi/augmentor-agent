/** Paths use the same installed Node API and precompiled engine as createConverter. */
export interface RuntimeInfo {
    readonly version: string;
    readonly backend: 'native' | 'wasm';
    readonly cliPath: string;
    readonly nodeApiPath: string;
}
/**
 * Inspect installed engine metadata without starting, downloading, or building an engine.
 * @returns Public entry paths, Node API version, and selected backend.
 * @throws ConversionError when the installed engine is unavailable or invalid.
 */
export declare function discoverRuntime(): Promise<RuntimeInfo>;
