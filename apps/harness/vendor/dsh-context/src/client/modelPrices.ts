/**
 * The client's model-price book: the models.dev registry through the official
 * @opencode-ai/models SDK. The payload is untrusted wire input, so
 * `pricesBookOf` re-proves every field and a non-conforming entry drops whole.
 * One fetch per page load, kicked on first subscribe; a failure shows a visible
 * state with a backed-off retry, never a spinner or an unhandled rejection.
 */

import { Models } from '@opencode-ai/models'
import { useSyncExternalStore } from 'react'
import { asRecord } from './services'
import { priceIndexOf } from './cost'
import type { ModelBook, ModelPrices, PriceTriple } from './cost'

function rateOf(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null
}

/** Extract the registry's per-model USD rates from a delivered providers payload
 * (`/api.json`) and build the resolution index over it. Any shape failure skips
 * that entry; a payload that is not a record returns null (a failed fetch). */
export function pricesBookOf(value: unknown): ModelBook | null {
  const data = asRecord(value)
  if (data === null || Array.isArray(data)) return null
  const book: ModelPrices = {}
  const npmOf: Record<string, string | null> = {}
  for (const providerId of Object.keys(data)) {
    const provider = asRecord(data[providerId])
    if (provider === null) continue
    const modelList = asRecord(provider.models)
    if (modelList === null) continue
    const npm: unknown = provider.npm
    npmOf[providerId] = typeof npm === 'string' ? npm : null
    const models: Record<string, PriceTriple> = {}
    for (const id of Object.keys(modelList)) {
      const model = asRecord(modelList[id])
      const cost = model !== null ? asRecord(model.cost) : null
      if (cost === null) continue
      const miss = rateOf(cost.input)
      const out = rateOf(cost.output)
      if (miss === null || out === null) continue
      models[id] = {
        hit: rateOf(cost.cache_read) ?? miss,
        miss,
        write: rateOf(cost.cache_write) ?? miss,
        out,
      }
    }
    if (Object.keys(models).length > 0) book[providerId] = models
  }
  return { prices: book, index: priceIndexOf(book, npmOf) }
}

export interface ModelPricesSnap {
  book: ModelBook | null
  failed: boolean
}

type Loader = () => Promise<unknown>

const defaultLoader: Loader = () => Models.make().providers()

const RETRY_BASE_MS = 30_000

let loader: Loader = defaultLoader
let snap: ModelPricesSnap = { book: null, failed: false }
let inFlight = false
let failures = 0
let timer: ReturnType<typeof setTimeout> | null = null
const listeners = new Set<() => void>()

function fail(): void {
  // fail() runs exactly once per fetch cycle (only fire() calls it, and both
  // fire() callers are blocked while a timer is armed), so re-arming cannot leak.
  snap = { ...snap, failed: true }
  failures++
  timer = setTimeout(() => {
    timer = null
    // Nobody reads the book anymore (the panel that subscribed is gone): end the
    // cycle instead of polling an unreachable registry for the page's whole life.
    if (listeners.size === 0) return
    void fire()
  }, RETRY_BASE_MS * 2 ** Math.min(failures - 1, 3))
}

async function fire(): Promise<void> {
  inFlight = true
  try {
    const book = pricesBookOf(await loader())
    if (book !== null) {
      snap = { book, failed: false }
      failures = 0
    } else {
      fail()
    }
  } catch {
    fail()
  }
  inFlight = false
  for (const fn of listeners) fn()
}

function kick(): void {
  if (snap.book !== null || inFlight || timer !== null) return
  void fire()
}

export const subscribeModelPrices = (fn: () => void): (() => void) => {
  listeners.add(fn)
  kick()
  return () => {
    listeners.delete(fn)
  }
}

export const getModelPricesSnap = (): ModelPricesSnap => snap

/** The stats board's read of the price book. */
export function useModelPrices(): ModelPricesSnap {
  return useSyncExternalStore(subscribeModelPrices, getModelPricesSnap)
}

export function resetModelPrices(): void {
  if (timer !== null) {
    clearTimeout(timer)
    timer = null
  }
  snap = { book: null, failed: false }
  inFlight = false
  failures = 0
  listeners.clear()
}

export function setModelPricesLoader(next: Loader | null): void {
  loader = next ?? defaultLoader
}
