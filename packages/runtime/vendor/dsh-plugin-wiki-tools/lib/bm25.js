/**
 * BM25 ranking over wiki pages, the retrieval core the wiki-retrieve skill
 * describes. Latin text tokenizes on word boundaries; CJK runs tokenize into
 * character bigrams (plus unigrams) so Chinese queries rank without a
 * segmenter. Exact-phrase matching stays in search.js as a complementary
 * signal: BM25 ranks term overlap, not contiguous text.
 *
 * @module dsh-plugin-wiki-tools/lib/bm25
 */

const K1 = 1.2
const B = 0.75

/**
 * Tokenize text into ranking terms: latin words lowercased, CJK unigrams plus
 * bigrams.
 * @param {string} text - any text.
 * @returns {string[]} terms in order.
 */
export function tokenize(text) {
  const source = typeof text === 'string' ? text : ''
  const terms = []
  let buffer = ''
  const flush = () => {
    if (buffer.length > 0) {
      terms.push(buffer.toLowerCase())
      buffer = ''
    }
  }
  for (let index = 0; index < source.length; index += 1) {
    const code = source.charCodeAt(index)
    const isLatin = (code >= 0x41 && code <= 0x5a) || (code >= 0x61 && code <= 0x7a) || (code >= 0x30 && code <= 0x39)
    const isCjk = code >= 0x4e00 && code <= 0x9fff
    if (isLatin) {
      buffer += source[index]
    } else if (isCjk) {
      flush()
      terms.push(source[index])
      const previous = source[index - 1]
      if (previous !== undefined && previous.charCodeAt(0) >= 0x4e00 && previous.charCodeAt(0) <= 0x9fff) {
        terms.push(previous + source[index])
      }
    } else {
      flush()
    }
  }
  flush()
  return terms
}

/**
 * Build a BM25 index over documents.
 * @param {Map<string, string>} documents - docKey → searchable text.
 * @returns {Bm25Index} the built index.
 */
export function buildIndex(documents) {
  /** @type {Map<string, Map<string, number>>} */
  const termFreqs = new Map()
  /** @type {Map<string, number>} */
  const lengths = new Map()
  /** @type {Map<string, number>} */
  const docFreq = new Map()
  for (const [key, text] of documents) {
    const counts = new Map()
    for (const term of tokenize(text)) counts.set(term, (counts.get(term) ?? 0) + 1)
    termFreqs.set(key, counts)
    lengths.set(key, [...counts.values()].reduce((sum, n) => sum + n, 0))
    for (const term of counts.keys()) docFreq.set(term, (docFreq.get(term) ?? 0) + 1)
  }
  const avgLength = lengths.size === 0 ? 0 : [...lengths.values()].reduce((sum, n) => sum + n, 0) / lengths.size
  return { termFreqs, lengths, docFreq, avgLength, total: lengths.size }
}

/**
 * @typedef {object} Bm25Index
 * @property {Map<string, Map<string, number>>} termFreqs
 * @property {Map<string, number>} lengths
 * @property {Map<string, number>} docFreq
 * @property {number} avgLength
 * @property {number} total
 */

/**
 * Score one query against every indexed document.
 * @param {Bm25Index} index - built index.
 * @param {string} query - raw query text.
 * @returns {Map<string, number>} docKey → BM25 score; only nonzero scores included.
 */
export function rank(index, query) {
  const terms = tokenize(query)
  const scores = new Map()
  if (terms.length === 0 || index.total === 0) return scores
  for (const [key, counts] of index.termFreqs) {
    let score = 0
    const length = index.lengths.get(key) ?? 0
    const normalizer = K1 * (1 - B + B * (length / (index.avgLength || 1)))
    for (const term of terms) {
      const freq = counts.get(term)
      if (freq === undefined) continue
      const df = index.docFreq.get(term) ?? 0
      const idf = Math.log(1 + (index.total - df + 0.5) / (df + 0.5))
      score += idf * (freq * (K1 + 1)) / (freq + normalizer)
    }
    if (score > 0) scores.set(key, score)
  }
  return scores
}
