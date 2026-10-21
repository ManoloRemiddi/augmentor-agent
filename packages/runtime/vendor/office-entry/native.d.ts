import type { FontSubstitution } from './font-loader.ts';
import type { ConversionSpec } from './operations.ts';
import type { NativeEngine } from './engine.ts';
import type { ResolvedOptions } from './options.ts';
/**
 * Write missing-family choices into the private profile's VCL substitution table.
 * Installed originals and metric-compatible fonts are resolved before this table by LibreOffice.
 * @param profile - Existing, conversion-owned profile directory.
 * @param substitutions - Missing document families and the selected installed family.
 * @returns Resolves after the exclusive profile file is written; empty choices still disable the interactive CSV warning.
 */
export declare function prepareNativeFontProfile(profile: string, substitutions: readonly FontSubstitution[]): Promise<void>;
/**
 * Linux searches the verified program directory; ambient loader overrides and credentials are excluded.
 * @param profile - Conversion-owned profile directory the helper treats as home.
 * @param programDirectory - Verified engine program directory.
 * @param source - Embedding process environment.
 * @param platform - Host operating system.
 * @returns the environment the helper starts with.
 */
export declare function nativeEnvironment(profile: string, programDirectory: string, source?: NodeJS.ProcessEnv, platform?: string): Record<string, string>;
/**
 * Keep Windows engine resources reachable through a short profile-owned path until the helper exits.
 * @param engine - Verified engine installation; its resources remain in place.
 * @param profile - Private operation directory that owns the temporary executable and junction.
 * @param run - Operation that settles only after its helper closes.
 * @returns The operation result after removing the resource junction.
 */
export declare function withNativeEngine<T>(engine: NativeEngine, profile: string, run: (engine: NativeEngine) => Promise<T>): Promise<T>;
/**
 * Run one native conversion and await bounded result transport.
 * @param engine - Resolved native engine installation.
 * @param options - Validated conversion limits.
 * @param input - Private source path inside the conversion scratch directory.
 * @param output - Private PDF path inside the conversion scratch directory.
 * @param profile - Conversion-owned profile directory.
 * @param fonts - Installed font files the helper may load.
 * @param substitutions - Missing families and their selected installed substitutes.
 * @param signal - Cancellation; it kills the helper and awaits its exit.
 * @param operation - Validated output format, recalculation, and worksheet selection.
 * @throws ConversionError for a reported conversion failure, and the abort reason for cancellation.
 */
export declare function runNative(engine: NativeEngine, options: ResolvedOptions, input: string, output: string, profile: string, fonts: readonly string[], substitutions: readonly FontSubstitution[], signal: AbortSignal, operation?: Pick<ConversionSpec, 'format' | 'recalculate' | 'sheet'>): Promise<void>;
