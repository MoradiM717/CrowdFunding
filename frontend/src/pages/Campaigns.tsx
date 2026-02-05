import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, Filter, Plus, ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useCampaigns } from '@/hooks/useApi'
import { CampaignCard } from '@/components/campaigns/CampaignCard'
import { CAMPAIGN_CATEGORIES, CampaignFilters } from '@/types/api'

const PAGE_SIZE = 12

export function Campaigns() {
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<CampaignFilters>({})
  const [searchQuery, setSearchQuery] = useState('')

  const { data, isLoading, isError } = useCampaigns({
    page,
    page_size: PAGE_SIZE,
    ...filters,
  })

  const handleFilterChange = (key: keyof CampaignFilters, value: string | undefined) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value === 'all' ? undefined : value,
    }))
    setPage(1) // Reset to first page on filter change
  }

  const handleTabChange = (value: string) => {
    if (value === 'all') {
      setFilters((prev) => ({ ...prev, status: undefined }))
    } else {
      setFilters((prev) => ({ ...prev, status: value }))
    }
    setPage(1)
  }

  const totalPages = data ? Math.ceil(data.count / PAGE_SIZE) : 0

  return (
    <div className="container py-8">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Campaigns</h1>
          <p className="text-muted-foreground mt-1">
            Browse and support campaigns from creators around the world
          </p>
        </div>
        <Button asChild>
          <Link to="/create">
            <Plus className="mr-2 h-4 w-4" />
            Create Campaign
          </Link>
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center mb-6">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search campaigns..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        <div className="flex gap-2">
          <Select
            value={filters.category || 'all'}
            onValueChange={(value) => handleFilterChange('category', value)}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {CAMPAIGN_CATEGORIES.map((cat) => (
                <SelectItem key={cat.value} value={cat.value}>
                  {cat.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={filters.ordering || '-created_at'}
            onValueChange={(value) => handleFilterChange('ordering', value)}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="-created_at">Newest</SelectItem>
              <SelectItem value="created_at">Oldest</SelectItem>
              <SelectItem value="-total_raised_wei">Most Raised</SelectItem>
              <SelectItem value="deadline">Ending Soon</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="all" onValueChange={handleTabChange} className="mb-6">
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="active">Active</TabsTrigger>
          <TabsTrigger value="successful">Successful</TabsTrigger>
          <TabsTrigger value="failed">Failed</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Results */}
      {isLoading ? (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: PAGE_SIZE }).map((_, i) => (
            <CampaignCardSkeleton key={i} />
          ))}
        </div>
      ) : isError ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-lg font-medium text-destructive">Error loading campaigns</p>
            <p className="text-sm text-muted-foreground">
              Please try again later or check your connection
            </p>
          </CardContent>
        </Card>
      ) : data?.results && data.results.length > 0 ? (
        <>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {data.results.map((campaign) => (
              <CampaignCard key={campaign.address} campaign={campaign} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <Button
                variant="outline"
                size="icon"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="icon"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Filter className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-medium">No campaigns found</p>
            <p className="text-sm text-muted-foreground mb-4">
              Try adjusting your filters or create a new campaign
            </p>
            <Button asChild>
              <Link to="/create">Create Campaign</Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function CampaignCardSkeleton() {
  return (
    <Card>
      <Skeleton className="h-48 rounded-t-lg rounded-b-none" />
      <div className="p-6">
        <Skeleton className="h-6 w-3/4 mb-2" />
        <Skeleton className="h-4 w-full mb-4" />
        <Skeleton className="h-2 w-full mb-2" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    </Card>
  )
}
