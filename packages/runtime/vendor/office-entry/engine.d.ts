/** Node API release version returned by runtime discovery. */
export declare const ENGINE_VERSION = "0.1.3-augmentor.1";
/** Exact compatible engine versions; unchanged platforms retain their published packages. */
export declare const ENGINE_VERSIONS: Readonly<Record<string, string>>;
/** Host diagnostic fields used to identify the runtime glibc version. */
export interface EngineHostReport {
    readonly header?: {
        readonly glibcVersionRuntime?: string;
    };
}
/** Process identification and diagnostic report the resolver classifies the host with. */
export interface EngineResolutionHost {
    readonly platform?: string;
    readonly arch?: string;
    readonly report?: () => EngineHostReport;
}
/** Engine installation fields both backends carry. */
interface EngineInstallation {
    /** Installed package root the manifest resolved to. */
    readonly root: string;
    /** Program resources the engine loads: a real directory natively, a virtual path in WASM. */
    readonly programDirectory: string;
    /** Recorded glibc floor when the native manifest declares one. */
    readonly glibcMinimum?: string;
}
/** A resolved native LibreOfficeKit helper. */
export interface NativeEngine extends EngineInstallation {
    readonly backend: 'native';
    readonly executable: string;
}
/** A resolved shared Node WebAssembly engine. */
export interface WasmEngine extends EngineInstallation {
    readonly backend: 'wasm';
    readonly loader: string;
    readonly wasm: string;
    readonly data: string;
    readonly metadata: string;
}
/** One resolved engine installation. */
export type Engine = NativeEngine | WasmEngine;
/** Engine backend a conversion runs in. */
export type EngineBackend = Engine['backend'];
/**
 * Whether an installed engine package directory is present on the resolution path.
 * @param name - Engine package name.
 * @returns true when at least one resolution directory holds the package.
 */
export declare function installedPackageExists(name: string): boolean;
/**
 * Return the optional package target for the current process ABI.
 * @param platform - Host operating system.
 * @param arch - Host CPU architecture.
 * @param report - Host diagnostic report used to identify glibc.
 * @returns the declared platform target, or undefined for an unsupported host.
 */
export declare function platformTarget(platform?: string, arch?: string, report?: () => EngineHostReport): string | undefined;
/**
 * macOS and Windows require their native engine. Linux uses WASM when no compatible development native engine is installed.
 * @param resolvePackage - Package manifest resolver; injectable for selection tests.
 * @param packageExists - Installed-package probe; injectable for selection tests.
 * @param host - Process identification and diagnostic report.
 * @returns the installed native engine, or the installed WASM engine.
 */
export declare function resolveEngine(resolvePackage?: (name: string) => string, packageExists?: (name: string) => boolean, { platform, arch, report }?: EngineResolutionHost): Promise<Engine>;
export {};
