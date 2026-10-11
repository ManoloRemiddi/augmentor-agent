/**
 * Per-image token estimate for DeepSeek's vision model — a port of the official image-token
 * calculator on the DeepSeek API docs
 * (https://api-docs.deepseek.com/zh-cn/quick_start/token_usage): aspect-preserved rescale, then
 * the 14px patch grid with 3:1 downsampling, capped at 384 tokens per image.
 *
 * Pure math shared by the Host fold (message pricing) and the Client (attachment card badges).
 */

const PATCH_SIZE = 14
const DOWNSAMPLE_RATIO = 3
const MAX_TOKENS = 384
const COMPRESS_PAD_TO = 4
const MAX_WH_RATIO = 8
const MIN_PIXELS = 147456

const floorDiv = (a: number, b: number): number => Math.floor(a / b)
const ceilDiv = (a: number, b: number): number => Math.floor((a + b - 1) / b)

function gridTokens(rows: number, cols: number): number {
  let n = rows * (cols + 1) + 2
  if (rows % 2 === 1) n += cols + 1
  n += (ceilDiv(rows, 2) * (cols + 1) % 2) * 2
  return n
}

interface ResizeSolution {
  nLlmH: number
  nLlmW: number
  bestHeight: number
  bestWidth: number
  numTokens: number
}

function solveResizeRatio(height: number, width: number, budget: number): ResizeSolution {
  const ratio = height / width
  const gridW = Math.sqrt((budget - 2) / ratio + 0.25) - 0.5
  const gridH = gridW * ratio
  const unit = PATCH_SIZE * DOWNSAMPLE_RATIO
  let bestHeight: number
  let bestWidth: number
  if (gridW < 1) {
    let rows = floorDiv(budget - 2, 2)
    /* v8 ignore else -- the tall solve never decrements, so rows is always odd here. */
    if (rows % 2 === 1) rows -= 1
    bestWidth = unit
    bestHeight = rows * unit
  /* v8 ignore start -- unreachable: the MAX_WH_RATIO clamp keeps height/width ≥ 1/8, so
     gridH can never fall below 2; port kept verbatim from the official calculator. */
  } else if (gridH < 2) {
    const cols = floorDiv(budget - 2, 2) - 1
    if (cols <= 1) throw new Error('image tokens: budget too small to solve')
    bestHeight = 2 * unit
    bestWidth = cols * unit
  /* v8 ignore stop */
  } else {
    const cols = Math.trunc(gridW)
    // The official grid pairs rows: odd counts round down.
    let rows = Math.trunc(gridH)
    if (rows % 2 === 1) rows -= 1
    const scale = Math.min(cols * unit / width, rows * unit / height)
    bestWidth = Math.trunc(width * scale / PATCH_SIZE) * PATCH_SIZE
    bestHeight = Math.trunc(height * scale / PATCH_SIZE) * PATCH_SIZE
  }
  const nLlmH = ceilDiv(floorDiv(bestHeight, PATCH_SIZE), DOWNSAMPLE_RATIO)
  const nLlmW = ceilDiv(floorDiv(bestWidth, PATCH_SIZE), DOWNSAMPLE_RATIO)
  return { nLlmH, nLlmW, bestHeight, bestWidth, numTokens: gridTokens(nLlmH, nLlmW) }
}

function safeResize(height: number, width: number, paddedHeight: number, paddedWidth: number): ResizeSolution {
  const nLlmH = ceilDiv(floorDiv(paddedHeight, PATCH_SIZE), DOWNSAMPLE_RATIO)
  const nLlmW = ceilDiv(floorDiv(paddedWidth, PATCH_SIZE), DOWNSAMPLE_RATIO)
  const pad = COMPRESS_PAD_TO - 1
  const budget = MAX_TOKENS - pad
  let result: ResizeSolution = {
    nLlmH,
    nLlmW,
    bestHeight: paddedHeight,
    bestWidth: paddedWidth,
    numTokens: gridTokens(nLlmH, nLlmW),
  }
  if (result.numTokens > budget) {
    result = solveResizeRatio(height, width, budget)
    let nextBudget = budget
    while (result.numTokens > budget) {
      nextBudget -= 1
      result = solveResizeRatio(height, width, nextBudget)
    }
  }
  result.numTokens += pad
  return result
}

function calcResizeInner(width: number, height: number): ResizeSolution {
  let w = width
  let h = height
  if (w > h * MAX_WH_RATIO) w = h * MAX_WH_RATIO
  const pixels = w * h
  if (pixels < MIN_PIXELS && pixels > 0) {
    const scale = Math.sqrt(MIN_PIXELS / pixels)
    w = Math.trunc(w * scale)
    h = Math.trunc(h * scale)
  }
  const paddedWidth = ceilDiv(w, PATCH_SIZE) * PATCH_SIZE
  const paddedHeight = ceilDiv(h, PATCH_SIZE) * PATCH_SIZE
  return safeResize(h, w, paddedHeight, paddedWidth)
}

/** Estimate one image's DeepSeek vision tokens; null for degenerate dimensions or a
 * non-converging solve, where callers fall back to the structural price. */
export function estimateImageTokens(width: number, height: number): number | null {
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) return null
  try {
    let result = calcResizeInner(width, height)
    for (let i = 1; i < 10; i++) {
      const next = calcResizeInner(result.bestWidth, result.bestHeight)
      if (next.nLlmH === result.nLlmH && next.nLlmW === result.nLlmW
        && next.bestHeight === result.bestHeight && next.bestWidth === result.bestWidth
        && next.numTokens === result.numTokens) return result.numTokens
      result = next
    }
    return null
  } catch {
    /* v8 ignore next -- the only throw site is the clamped-away budget guard above; keeps a
       hostile dimension from breaking the fold. */
    return null
  }
}
