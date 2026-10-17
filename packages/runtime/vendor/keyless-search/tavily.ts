// Augmentor adaptation: request-local bounded transport; original request/response and optional-key logic remain unchanged.
import {keylessProviderFetch as fetch} from "./transport.js";
export const TAVILY_SEARCH_URL = "https://api.tavily.com/search";

export interface SearchSource {
  url: string;
  title?: string;
  snippet?: string;
  publishedAt?: string;
}

export interface SearchResult {
  sources: SearchSource[];
  truncated: boolean;
  content?: string;
}

export interface TavilyRequest {
  query: string;
  maxResults?: number;
  apiKey?: string;
  signal?: AbortSignal;
}

interface TavilyHit {
  url?: unknown;
  title?: unknown;
  content?: unknown;
  published_date?: unknown;
}

interface TavilyBody {
  results?: TavilyHit[];
  answer?: unknown;
}

export function searchHeaders(apiKey?: string): Record<string, string> {
  const headers: Record<string, string> = {
    accept: "application/json",
    "content-type": "application/json",
  };
  if (apiKey) headers.authorization = `Bearer ${apiKey}`;
  else headers["x-tavily-access-mode"] = "keyless";
  return headers;
}

export function searchBody(query: string, maxResults = 5): string {
  return JSON.stringify({
    query,
    search_depth: "basic",
    max_results: maxResults,
    include_answer: false,
    include_raw_content: false,
    include_images: false,
  });
}

export function mapTavilyResponse(body: unknown): SearchResult {
  const parsed = (body ?? {}) as TavilyBody;
  const hits = Array.isArray(parsed.results) ? parsed.results : [];
  const sources: SearchSource[] = [];
  for (const hit of hits) {
    if (typeof hit?.url !== "string" || hit.url.length === 0) continue;
    const source: SearchSource = { url: hit.url };
    if (typeof hit.title === "string" && hit.title) source.title = hit.title;
    if (typeof hit.content === "string" && hit.content) source.snippet = hit.content;
    if (typeof hit.published_date === "string" && hit.published_date) {
      source.publishedAt = hit.published_date;
    }
    sources.push(source);
  }
  const result: SearchResult = { sources, truncated: false };
  if (typeof parsed.answer === "string" && parsed.answer) result.content = parsed.answer;
  return result;
}

export async function tavilySearch(request: TavilyRequest): Promise<SearchResult> {
  const response = await fetch(TAVILY_SEARCH_URL, {
    method: "POST",
    headers: searchHeaders(request.apiKey),
    body: searchBody(request.query, request.maxResults ?? 5),
    signal: request.signal,
  });
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`search failed HTTP ${response.status}${text ? `: ${text.slice(0, 200)}` : ""}`);
  }
  return mapTavilyResponse(await response.json());
}
