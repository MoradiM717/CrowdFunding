// API Response Types

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// Chain Types
export interface Chain {
  id: number
  name: string
  chain_id: number
  rpc_url: string | null
  created_at: string
  updated_at: string
}

export interface SyncState {
  chain_id: number
  chain_name: string
  last_block: number
  last_block_hash: string
  updated_at: string
}

// Campaign Types
export interface Campaign {
  address: string
  factory_address: string
  creator_address: string
  goal_wei: string
  goal_eth: string
  deadline_ts: number
  deadline_iso: string
  cid: string | null
  status: 'ACTIVE' | 'SUCCESS' | 'FAILED' | 'WITHDRAWN'
  total_raised_wei: string
  total_raised_eth: string
  progress_percent: number
  withdrawn: boolean
  withdrawn_amount_wei: string | null
  withdrawn_amount_eth: string | null
  created_at: string
  updated_at: string
}

export interface CampaignDetail extends Campaign {
  contributions_count: number
  events_count: number
  metadata?: CampaignMetadata
}

export interface CampaignWithMetadata extends Campaign {
  metadata?: CampaignMetadataSummary
}

// Metadata Types
export interface CampaignMetadata {
  id: number
  campaign_address: string
  cid: string
  name: string | null
  description: string | null
  short_description: string | null
  image_cid: string | null
  image_url: string | null
  banner_cid: string | null
  banner_url: string | null
  category: string | null
  tags: string[]
  location: string | null
  creator_name: string | null
  creator_avatar_cid: string | null
  creator_avatar_url: string | null
  website_url: string | null
  twitter_handle: string | null
  discord_url: string | null
  ipfs_fetched_at: string | null
  created_at: string
  updated_at: string
}

export interface CampaignMetadataSummary {
  name: string | null
  short_description: string | null
  image_url: string | null
  category: string | null
}

// Contribution Types
export interface Contribution {
  id: number
  campaign_address: string
  donor_address: string
  contributed_wei: string
  contributed_eth: string
  refunded_wei: string
  refunded_eth: string
  net_contributed_eth: string
  created_at: string
  updated_at: string
}

export interface ContributionWithCampaign extends Contribution {
  campaign: Campaign
}

// Event Types
export interface BlockchainEvent {
  id: number
  chain_id: number
  tx_hash: string
  log_index: number
  block_number: number
  block_hash: string
  address: string | null
  event_name: string
  event_data: string | null
  event_data_parsed: Record<string, unknown> | null
  removed: boolean
  created_at: string
}

// Statistics Types
export interface PlatformStats {
  total_campaigns: number
  active_campaigns: number
  successful_campaigns: number
  failed_campaigns: number
  withdrawn_campaigns: number
  total_raised_wei: string
  total_raised_eth: string
  total_goal_wei: string
  total_goal_eth: string
  total_contributions: number
  unique_donors: number
  success_rate: number
}

export interface TrendingCampaign extends Campaign {
  recent_contributions_count: number
  recent_raised_wei: string
  recent_raised_eth: string
  distance_to_goal_percent: number
}

export interface TrendingResponse {
  period: string
  type: string
  count: number
  results: TrendingCampaign[]
}

export interface CampaignLeaderboardEntry extends Campaign {
  rank: number
  contributions_count: number
}

export interface DonorLeaderboardEntry {
  rank: number
  donor_address: string
  total_contributed_wei: string
  total_contributed_eth: string
  total_refunded_wei: string
  total_refunded_eth: string
  net_contributed_wei: string
  net_contributed_eth: string
  campaigns_supported: number
}

export interface LeaderboardResponse<T> {
  count: number
  offset: number
  limit: number
  results: T[]
}

export interface CreatorStats {
  creator_address: string
  total_campaigns: number
  active_campaigns: number
  successful_campaigns: number
  failed_campaigns: number
  total_raised_wei: string
  total_raised_eth: string
  total_goal_wei: string
  total_goal_eth: string
  total_withdrawn_wei: string
  total_withdrawn_eth: string
  success_rate: number
  average_progress_percent: number
}

// Filter Types
export interface CampaignFilters {
  status?: string
  creator_address?: string
  factory_address?: string
  min_goal?: string
  max_goal?: string
  min_raised?: string
  has_withdrawn?: boolean
  deadline_before?: number
  deadline_after?: number
  category?: string
  q?: string
  has_metadata?: boolean
  ordering?: string
  page?: number
  page_size?: number
  include_metadata?: boolean
  [key: string]: string | number | boolean | undefined
}

export interface TrendingFilters {
  period?: '24h' | '7d' | '30d'
  limit?: number
  type?: 'recent_donations' | 'close_to_goal'
  [key: string]: string | number | undefined
}

// Category options
export const CAMPAIGN_CATEGORIES = [
  { value: 'technology', label: 'Technology' },
  { value: 'art', label: 'Art & Creative' },
  { value: 'music', label: 'Music' },
  { value: 'film', label: 'Film & Video' },
  { value: 'games', label: 'Games' },
  { value: 'publishing', label: 'Publishing' },
  { value: 'food', label: 'Food & Craft' },
  { value: 'fashion', label: 'Fashion & Design' },
  { value: 'environment', label: 'Environment' },
  { value: 'community', label: 'Community' },
  { value: 'health', label: 'Health & Wellness' },
  { value: 'education', label: 'Education' },
  { value: 'sports', label: 'Sports' },
  { value: 'travel', label: 'Travel & Adventure' },
  { value: 'charity', label: 'Charity & Nonprofit' },
  { value: 'other', label: 'Other' },
] as const

export type CampaignCategory = typeof CAMPAIGN_CATEGORIES[number]['value']
