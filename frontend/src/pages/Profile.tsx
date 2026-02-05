import { useParams, Link } from 'react-router-dom'
import { useAccount } from 'wagmi'
import {
  User,
  Wallet,
  Target,
  TrendingUp,
  Calendar,
  ExternalLink,
  Copy,
  Check,
} from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  useCreatorStats,
  useCreatorCampaigns,
  useDonorStats,
  useDonorContributions,
} from '@/hooks/useApi'
import { CampaignCard } from '@/components/campaigns/CampaignCard'
import { shortenAddress, formatDateTime } from '@/lib/utils'

export function Profile() {
  const { address: paramAddress } = useParams<{ address: string }>()
  const { address: connectedAddress, isConnected } = useAccount()

  // Use param address or connected address
  const profileAddress = paramAddress || connectedAddress
  const isOwnProfile = !paramAddress || (isConnected && paramAddress?.toLowerCase() === connectedAddress?.toLowerCase())

  const [copied, setCopied] = useState(false)

  const { data: creatorStats, isLoading: creatorStatsLoading } = useCreatorStats(
    profileAddress as string
  )
  const { data: creatorCampaigns, isLoading: campaignsLoading } = useCreatorCampaigns(
    profileAddress as string
  )
  const { data: donorStats } = useDonorStats(profileAddress as string)
  const { data: donorContributions, isLoading: contributionsLoading } = useDonorContributions(
    profileAddress as string
  )

  const copyAddress = () => {
    if (profileAddress) {
      navigator.clipboard.writeText(profileAddress)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  if (!profileAddress) {
    return (
      <div className="container py-8">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Wallet className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-medium">No wallet connected</p>
            <p className="text-sm text-muted-foreground mb-4">
              Connect your wallet to view your profile
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container py-8">
      {/* Profile Header */}
      <Card className="mb-8">
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row md:items-center gap-6">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
              <User className="h-10 w-10 text-primary" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <h1 className="text-2xl font-bold">
                  {isOwnProfile ? 'My Profile' : shortenAddress(profileAddress)}
                </h1>
                {isOwnProfile && (
                  <Badge variant="secondary">You</Badge>
                )}
              </div>
              <div className="flex items-center gap-2 text-muted-foreground">
                <code className="text-sm">{shortenAddress(profileAddress)}</code>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={copyAddress}
                >
                  {copied ? (
                    <Check className="h-3 w-3 text-green-500" />
                  ) : (
                    <Copy className="h-3 w-3" />
                  )}
                </Button>
                <a
                  href={`https://etherscan.io/address/${profileAddress}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-primary hover:underline text-sm"
                >
                  View on Etherscan
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
        <StatsCard
          title="Campaigns Created"
          value={creatorStats?.total_campaigns.toString() ?? '0'}
          icon={<Target className="h-4 w-4 text-muted-foreground" />}
          loading={creatorStatsLoading}
        />
        <StatsCard
          title="Total Raised"
          value={creatorStats ? `${creatorStats.total_raised_eth} ETH` : '0 ETH'}
          icon={<TrendingUp className="h-4 w-4 text-muted-foreground" />}
          loading={creatorStatsLoading}
        />
        <StatsCard
          title="Contributions Made"
          value={donorStats?.total_contributions.toString() ?? '0'}
          icon={<Wallet className="h-4 w-4 text-muted-foreground" />}
          loading={creatorStatsLoading}
        />
        <StatsCard
          title="Total Donated"
          value={donorStats ? `${donorStats.total_donated_eth} ETH` : '0 ETH'}
          icon={<TrendingUp className="h-4 w-4 text-muted-foreground" />}
          loading={creatorStatsLoading}
        />
      </div>

      {/* Tabs */}
      <Tabs defaultValue="campaigns">
        <TabsList>
          <TabsTrigger value="campaigns">
            Created Campaigns ({creatorCampaigns?.count ?? 0})
          </TabsTrigger>
          <TabsTrigger value="contributions">
            Contributions ({donorContributions?.count ?? 0})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="campaigns" className="mt-6">
          {campaignsLoading ? (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <CampaignCardSkeleton key={i} />
              ))}
            </div>
          ) : creatorCampaigns?.results && creatorCampaigns.results.length > 0 ? (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {creatorCampaigns.results.map((campaign) => (
                <CampaignCard key={campaign.address} campaign={campaign} />
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Target className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-lg font-medium">No campaigns yet</p>
                <p className="text-sm text-muted-foreground mb-4">
                  {isOwnProfile
                    ? "You haven't created any campaigns yet"
                    : 'This address has not created any campaigns'}
                </p>
                {isOwnProfile && (
                  <Button asChild>
                    <Link to="/create">Create Campaign</Link>
                  </Button>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="contributions" className="mt-6">
          {contributionsLoading ? (
            <div className="space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : donorContributions?.results && donorContributions.results.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Contribution History</CardTitle>
                <CardDescription>
                  All contributions made by this address
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {donorContributions.results.map((contribution, index) => (
                    <div
                      key={`${contribution.campaign_address}-${index}`}
                      className="flex items-center justify-between py-3 border-b last:border-0"
                    >
                      <div>
                        <Link
                          to={`/campaign/${contribution.campaign_address}`}
                          className="font-medium hover:text-primary hover:underline"
                        >
                          {shortenAddress(contribution.campaign_address)}
                        </Link>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Calendar className="h-3 w-3" />
                          {formatDateTime(contribution.created_at)}
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-medium">{contribution.contributed_eth} ETH</p>
                        <Badge variant="outline" className="text-xs">
                          {contribution.refunded_wei !== '0' ? 'Refunded' : 'Active'}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Wallet className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-lg font-medium">No contributions yet</p>
                <p className="text-sm text-muted-foreground mb-4">
                  {isOwnProfile
                    ? "You haven't made any contributions yet"
                    : 'This address has not made any contributions'}
                </p>
                {isOwnProfile && (
                  <Button asChild>
                    <Link to="/campaigns">Browse Campaigns</Link>
                  </Button>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

function StatsCard({
  title,
  value,
  icon,
  loading,
}: {
  title: string
  value: string
  icon: React.ReactNode
  loading?: boolean
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-24" />
        ) : (
          <div className="text-2xl font-bold">{value}</div>
        )}
      </CardContent>
    </Card>
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
