import { Link } from 'react-router-dom'
import { ArrowRight, Rocket, Users, TrendingUp, Target } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { usePlatformStats, useTrendingCampaigns } from '@/hooks/useApi'
import { CampaignCard } from '@/components/campaigns/CampaignCard'

export function Home() {
  const { data: stats, isLoading: statsLoading } = usePlatformStats()
  const { data: trending, isLoading: trendingLoading } = useTrendingCampaigns({
    limit: 6,
    type: 'recent_donations',
  })

  return (
    <div className="flex flex-col">
      {/* Hero Section */}
      <section className="relative overflow-hidden border-b bg-gradient-to-br from-primary/5 via-background to-background">
        <div className="container py-24 md:py-32">
          <div className="flex flex-col items-center text-center space-y-8">
            <div className="space-y-4">
              <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl lg:text-7xl">
                Fund the Future,{' '}
                <span className="text-primary">Decentralized</span>
              </h1>
              <p className="mx-auto max-w-2xl text-lg text-muted-foreground md:text-xl">
                Launch your campaign on the blockchain. Get funded by a global community.
                No intermediaries, complete transparency.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-4">
              <Button size="lg" asChild>
                <Link to="/create">
                  <Rocket className="mr-2 h-5 w-5" />
                  Start a Campaign
                </Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link to="/campaigns">
                  Explore Campaigns
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="border-b py-12">
        <div className="container">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <StatsCard
              title="Total Campaigns"
              value={stats?.total_campaigns.toString() ?? '0'}
              icon={<Target className="h-4 w-4 text-muted-foreground" />}
              loading={statsLoading}
            />
            <StatsCard
              title="Total Raised"
              value={stats ? `${stats.total_raised_eth} ETH` : '0 ETH'}
              icon={<TrendingUp className="h-4 w-4 text-muted-foreground" />}
              loading={statsLoading}
            />
            <StatsCard
              title="Unique Donors"
              value={stats?.unique_donors.toString() ?? '0'}
              icon={<Users className="h-4 w-4 text-muted-foreground" />}
              loading={statsLoading}
            />
            <StatsCard
              title="Success Rate"
              value={stats ? `${stats.success_rate.toFixed(1)}%` : '0%'}
              icon={<Rocket className="h-4 w-4 text-muted-foreground" />}
              loading={statsLoading}
            />
          </div>
        </div>
      </section>

      {/* Trending Campaigns */}
      <section className="py-16">
        <div className="container">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-3xl font-bold tracking-tight">Trending Campaigns</h2>
              <p className="text-muted-foreground mt-2">
                Popular campaigns getting the most support
              </p>
            </div>
            <Button variant="ghost" asChild>
              <Link to="/campaigns">
                View All
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>

          {trendingLoading ? (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <CampaignCardSkeleton key={i} />
              ))}
            </div>
          ) : trending?.results && trending.results.length > 0 ? (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {trending.results.map((campaign) => (
                <CampaignCard key={campaign.address} campaign={campaign} />
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Rocket className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-lg font-medium">No campaigns yet</p>
                <p className="text-sm text-muted-foreground mb-4">
                  Be the first to start a campaign!
                </p>
                <Button asChild>
                  <Link to="/create">Create Campaign</Link>
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </section>

      {/* How It Works */}
      <section className="border-t bg-muted/50 py-16">
        <div className="container">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold tracking-tight">How It Works</h2>
            <p className="text-muted-foreground mt-2">
              Launch your campaign in three simple steps
            </p>
          </div>

          <div className="grid gap-8 md:grid-cols-3">
            <Card>
              <CardHeader>
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                  <span className="text-xl font-bold text-primary">1</span>
                </div>
                <CardTitle>Create Your Campaign</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground">
                Set your funding goal, deadline, and tell your story.
                Your campaign metadata is stored on IPFS for permanence.
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                  <span className="text-xl font-bold text-primary">2</span>
                </div>
                <CardTitle>Receive Contributions</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground">
                Supporters send ETH directly to your campaign smart contract.
                All transactions are transparent and verifiable.
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                  <span className="text-xl font-bold text-primary">3</span>
                </div>
                <CardTitle>Withdraw Funds</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground">
                If you reach your goal, withdraw the funds. If not, contributors
                can reclaim their donations automatically.
              </CardContent>
            </Card>
          </div>
        </div>
      </section>
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
      <CardHeader>
        <Skeleton className="h-6 w-3/4" />
        <Skeleton className="h-4 w-full" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-4 w-full mb-2" />
        <Skeleton className="h-4 w-2/3" />
      </CardContent>
    </Card>
  )
}
