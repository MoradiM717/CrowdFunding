import type {
  Campaign,
  CampaignDetail,
  CampaignWithMetadata,
  CampaignMetadata,
  Contribution,
  ContributionWithCampaign,
  BlockchainEvent,
  PlatformStats,
  TrendingResponse,
  LeaderboardResponse,
  CampaignLeaderboardEntry,
  DonorLeaderboardEntry,
  CreatorStats,
  PaginatedResponse,
  CampaignFilters,
  TrendingFilters,
  Chain,
  SyncState,
} from '@/types/api'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new ApiError(
      response.status,
      errorData.detail || errorData.error || `HTTP ${response.status}`
    )
  }

  return response.json()
}

function buildQueryString(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value))
    }
  })
  const queryString = searchParams.toString()
  return queryString ? `?${queryString}` : ''
}

// Chains API
export const chainsApi = {
  list: () => fetchApi<Chain[]>('/chains/'),

  get: (chainId: number) => fetchApi<Chain>(`/chains/${chainId}/`),

  getSyncState: (chainId: number) =>
    fetchApi<SyncState>(`/chains/${chainId}/sync-state/`),
}

// Campaigns API
export const campaignsApi = {
  list: (filters?: CampaignFilters) => {
    const params = filters?.include_metadata
      ? { ...filters, include_metadata: 'true' }
      : filters
    return fetchApi<PaginatedResponse<CampaignWithMetadata>>(
      `/campaigns/${buildQueryString(params || {})}`
    )
  },

  get: (address: string, includeMetadata = true) =>
    fetchApi<CampaignDetail>(
      `/campaigns/${address}/${buildQueryString({ include_metadata: includeMetadata })}`
    ),

  getMetadata: (address: string) =>
    fetchApi<CampaignMetadata>(`/campaigns/${address}/metadata/`),

  refreshMetadata: (address: string) =>
    fetchApi<CampaignMetadata>(`/campaigns/${address}/metadata/refresh/`, {
      method: 'POST',
    }),

  getContributions: (address: string, page = 1, pageSize = 20) =>
    fetchApi<PaginatedResponse<Contribution>>(
      `/campaigns/${address}/contributions/${buildQueryString({ page, page_size: pageSize })}`
    ),

  getEvents: (address: string, filters?: { event_name?: string; removed?: boolean }) =>
    fetchApi<PaginatedResponse<BlockchainEvent>>(
      `/campaigns/${address}/events/${buildQueryString(filters || {})}`
    ),
}

// Creators API
export const creatorsApi = {
  getCampaigns: (creatorAddress: string, filters?: CampaignFilters) =>
    fetchApi<PaginatedResponse<Campaign>>(
      `/creators/${creatorAddress}/campaigns/${buildQueryString(filters || {})}`
    ),
}

// Donors API
export const donorsApi = {
  getContributions: (donorAddress: string, page = 1, pageSize = 20) =>
    fetchApi<PaginatedResponse<ContributionWithCampaign>>(
      `/donors/${donorAddress}/contributions/${buildQueryString({ page, page_size: pageSize })}`
    ),
}

// Events API
export const eventsApi = {
  list: (filters?: {
    chain_id?: number
    event_name?: string
    address?: string
    block_number_gte?: number
    block_number_lte?: number
    tx_hash?: string
    removed?: boolean
    page?: number
  }) =>
    fetchApi<PaginatedResponse<BlockchainEvent>>(
      `/events/${buildQueryString(filters || {})}`
    ),

  get: (id: number) => fetchApi<BlockchainEvent>(`/events/${id}/`),
}

// Stats API
export const statsApi = {
  getPlatform: () => fetchApi<PlatformStats>('/stats/platform/'),

  getTrending: (filters?: TrendingFilters) =>
    fetchApi<TrendingResponse>(`/stats/trending/${buildQueryString(filters || {})}`),

  getCampaignLeaderboard: (params?: { limit?: number; offset?: number; status?: string }) =>
    fetchApi<LeaderboardResponse<CampaignLeaderboardEntry>>(
      `/stats/leaderboard/campaigns/${buildQueryString(params || {})}`
    ),

  getDonorLeaderboard: (params?: { limit?: number; offset?: number }) =>
    fetchApi<LeaderboardResponse<DonorLeaderboardEntry>>(
      `/stats/leaderboard/donors/${buildQueryString(params || {})}`
    ),

  getCreatorStats: (creatorAddress: string) =>
    fetchApi<CreatorStats>(`/stats/creator/${creatorAddress}/`),
}

// Export all APIs as a single object
export const api = {
  chains: chainsApi,
  campaigns: campaignsApi,
  creators: creatorsApi,
  donors: donorsApi,
  events: eventsApi,
  stats: statsApi,
}

export { ApiError }
