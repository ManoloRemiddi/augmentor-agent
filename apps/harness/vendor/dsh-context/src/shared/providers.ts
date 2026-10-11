/** The provider-id seam between dsh request envelopes and the models.dev registry, read by
 * client/cost.ts (price-book branches) and host/fold.ts (the peak/off-peak split); unmapped dsh
 * route keys pass through unchanged. */

const MODELS_DEV_PROVIDER_IDS: Record<string, string> = {
  // dsh's two native DeepSeek routes share one registry vendor and one period-based list, so
  // `deepseek-account` must resolve for the fold's peak/off-peak split too.
  'deepseek-official': 'deepseek',
  'deepseek-account': 'deepseek',
  'kimi-coding': 'moonshotai',
  'minimax-cn': 'minimax',
  'zai-coding-cn': 'zhipuai',
}

export function modelsDevProviderOf(dshProviderId: string): string {
  return MODELS_DEV_PROVIDER_IDS[dshProviderId] ?? dshProviderId
}

export function isDeepSeekProvider(dshProviderId: string): boolean {
  return modelsDevProviderOf(dshProviderId) === 'deepseek'
}
