// Copyright © 2026 Manolo Remiddi. MIT supplier adaptation: NodeNext relative imports; the original branded primitives are selected locally.
/** Classified failures shared by conversion and its consumers. */
import type { OfficeToPdfErrorCode } from './types.js'

/** Classified conversion failure; engine details stay in the cause. */
export class OfficeToPdfError extends Error {
  /**
   * @param code - category suitable for a conversion consumer.
   * @param message - diagnostic explaining the failed conversion.
   * @param options - underlying engine or filesystem failure.
   */
  constructor(readonly code: OfficeToPdfErrorCode, message: string, options?: ErrorOptions) {
    super(message, options)
    this.name = 'OfficeToPdfError'
  }
}
