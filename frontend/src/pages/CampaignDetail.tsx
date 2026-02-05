import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAccount } from 'wagmi'
import {
  ArrowLeft,
  Clock,
  Users,
  Target,
  ExternalLink,
  AlertCircle,
  CheckCircle,
  Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useCampaign, useCampaignContributions, useCampaignMetadata } from '@/hooks/useApi'
import { useDonate, useWithdraw, useRefund, useContributionOf } from '@/hooks/useContracts'
import {
  shortenAddress,
  formatTimeRemaining,
  formatDateTime,
} from '@/lib/utils'

export function CampaignDetail() {
  const { address } = useParams<{ address: string }>()
  const { address: userAddress, isConnected } = useAccount()

  const campaignAddress = address as `0x${string}`

  const { data: campaign, isLoading, isError } = useCampaign(campaignAddress)
  const { data: metadata } = useCampaignMetadata(campaignAddress)
  const { data: contributions } = useCampaignContributions(campaignAddress, 1, 10)

  const { data: userContributionData } = useContributionOf(
    campaignAddress,
    userAddress as `0x${string}` | undefined
  )
  const userContribution = userContributionData as bigint | undefined

  if (isLoading) {
    return <CampaignDetailSkeleton />
  }

  if (isError || !campaign) {
    return (
      <div className="container py-8">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="h-12 w-12 text-destructive mb-4" />
            <p className="text-lg font-medium">Campaign not found</p>
            <p className="text-sm text-muted-foreground mb-4">
              The campaign you're looking for doesn't exist or has been removed.
            </p>
            <Button asChild>
              <Link to="/campaigns">Back to Campaigns</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const progress = campaign.progress_percent
  const timeRemaining = formatTimeRemaining(campaign.deadline_iso)
  const isEnded = new Date(campaign.deadline_iso) < new Date()
  const isCreator = userAddress?.toLowerCase() === campaign.creator_address.toLowerCase()
  const canWithdraw = isCreator && campaign.status === 'SUCCESS' && !campaign.withdrawn
  const canRefund = campaign.status === 'FAILED' && userContribution !== undefined && userContribution > 0n
  const canDonate = campaign.status === 'ACTIVE' && !isEnded

  return (
    <div className="container py-8">
      {/* Back Button */}
      <Button variant="ghost" asChild className="mb-6">
        <Link to="/campaigns">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Campaigns
        </Link>
      </Button>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Header */}
          <Card>
            <div className="h-64 bg-gradient-to-br from-primary/20 via-primary/10 to-background flex items-center justify-center">
              <Target className="h-24 w-24 text-primary/40" />
            </div>
            <CardHeader>
              <div className="flex items-center gap-2 mb-2">
                <Badge variant={getStatusVariant(campaign.status)}>
                  {formatStatus(campaign.status)}
                </Badge>
                {metadata?.category && (
                  <Badge variant="outline">{metadata.category}</Badge>
                )}
              </div>
              <CardTitle className="text-2xl">
                {metadata?.name || `Campaign ${shortenAddress(campaign.address)}`}
              </CardTitle>
              <CardDescription>
                Created by{' '}
                <Link
                  to={`/profile/${campaign.creator_address}`}
                  className="text-primary hover:underline"
                >
                  {shortenAddress(campaign.creator_address)}
                </Link>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                {metadata?.description || 'No description available'}
              </p>
            </CardContent>
          </Card>

          {/* Tabs */}
          <Tabs defaultValue="details">
            <TabsList>
              <TabsTrigger value="details">Details</TabsTrigger>
              <TabsTrigger value="contributions">
                Contributions ({campaign.contributions_count})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="details" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Campaign Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <InfoItem
                      label="Contract Address"
                      value={
                        <a
                          href={`https://etherscan.io/address/${campaign.address}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-primary hover:underline"
                        >
                          {shortenAddress(campaign.address)}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      }
                    />
                    <InfoItem label="Creator" value={shortenAddress(campaign.creator_address)} />
                    <InfoItem label="Goal" value={`${campaign.goal_eth} ETH`} />
                    <InfoItem label="Raised" value={`${campaign.total_raised_eth} ETH`} />
                    <InfoItem label="Deadline" value={formatDateTime(campaign.deadline_iso)} />
                    <InfoItem
                      label="Time Remaining"
                      value={isEnded ? 'Campaign ended' : timeRemaining}
                    />
                    {campaign.cid && (
                      <InfoItem
                        label="IPFS CID"
                        value={
                          <a
                            href={`https://ipfs.io/ipfs/${campaign.cid}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-primary hover:underline"
                          >
                            {campaign.cid.substring(0, 16)}...
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        }
                      />
                    )}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="contributions">
              <Card>
                <CardHeader>
                  <CardTitle>Recent Contributions</CardTitle>
                  <CardDescription>
                    {campaign.contributions_count} total contributions
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {contributions?.results && contributions.results.length > 0 ? (
                    <div className="space-y-4">
                      {contributions.results.map((contribution, index) => (
                        <div
                          key={`${contribution.donor_address}-${index}`}
                          className="flex items-center justify-between py-2"
                        >
                          <div className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                              <Users className="h-4 w-4 text-primary" />
                            </div>
                            <div>
                              <p className="text-sm font-medium">
                                {shortenAddress(contribution.donor_address)}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {formatDateTime(contribution.created_at)}
                              </p>
                            </div>
                          </div>
                          <span className="font-medium">
                            {contribution.contributed_eth} ETH
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-center py-8">
                      No contributions yet. Be the first to donate!
                    </p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Progress Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Funding Progress</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="font-medium">{campaign.total_raised_eth} ETH</span>
                  <span className="text-muted-foreground">
                    of {campaign.goal_eth} ETH
                  </span>
                </div>
                <Progress value={progress} className="h-3" />
                <p className="text-right text-sm text-muted-foreground mt-1">
                  {progress.toFixed(1)}% funded
                </p>
              </div>

              <Separator />

              <div className="grid grid-cols-2 gap-4 text-center">
                <div>
                  <Users className="h-5 w-5 mx-auto text-muted-foreground mb-1" />
                  <p className="text-2xl font-bold">{campaign.contributions_count}</p>
                  <p className="text-xs text-muted-foreground">Contributors</p>
                </div>
                <div>
                  <Clock className="h-5 w-5 mx-auto text-muted-foreground mb-1" />
                  <p className="text-2xl font-bold">{isEnded ? '0' : timeRemaining.split(' ')[0]}</p>
                  <p className="text-xs text-muted-foreground">
                    {isEnded ? 'Ended' : timeRemaining.split(' ').slice(1).join(' ') || 'Remaining'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Action Card */}
          {isConnected && (
            <ActionCard
              campaignAddress={campaignAddress}
              canDonate={canDonate}
              canWithdraw={canWithdraw}
              canRefund={!!canRefund}
              isCreator={isCreator}
              userContribution={userContribution}
            />
          )}

          {!isConnected && (
            <Card>
              <CardContent className="py-6 text-center">
                <AlertCircle className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                <p className="text-sm text-muted-foreground">
                  Connect your wallet to donate, withdraw, or refund
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

function ActionCard({
  campaignAddress,
  canDonate,
  canWithdraw,
  canRefund,
  isCreator,
  userContribution,
}: {
  campaignAddress: `0x${string}`
  canDonate: boolean
  canWithdraw: boolean
  canRefund: boolean
  isCreator: boolean
  userContribution: bigint | undefined
}) {
  const [donateAmount, setDonateAmount] = useState('')

  const {
    donate,
    isPending: isDonating,
    isConfirming: isDonateConfirming,
    isSuccess: isDonateSuccess,
    error: donateError,
  } = useDonate(campaignAddress)

  const {
    withdraw,
    isPending: isWithdrawing,
    isConfirming: isWithdrawConfirming,
    isSuccess: isWithdrawSuccess,
    error: withdrawError,
  } = useWithdraw(campaignAddress)

  const {
    refund,
    isPending: isRefunding,
    isConfirming: isRefundConfirming,
    isSuccess: isRefundSuccess,
    error: refundError,
  } = useRefund(campaignAddress)

  const handleDonate = (e: React.FormEvent) => {
    e.preventDefault()
    if (donateAmount && parseFloat(donateAmount) > 0) {
      donate(donateAmount)
    }
  }

  const formatUserContribution = (contribution: bigint | undefined): string => {
    if (!contribution) return '0 ETH'
    const eth = Number(contribution) / 1e18
    return `${eth.toFixed(6)} ETH`
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">
          {canDonate ? 'Support this Campaign' : isCreator ? 'Creator Actions' : 'Actions'}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Donate Form */}
        {canDonate && (
          <form onSubmit={handleDonate} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="amount">Amount (ETH)</Label>
              <Input
                id="amount"
                type="number"
                step="0.001"
                min="0"
                placeholder="0.1"
                value={donateAmount}
                onChange={(e) => setDonateAmount(e.target.value)}
                disabled={isDonating || isDonateConfirming}
              />
            </div>
            <Button
              type="submit"
              className="w-full"
              disabled={!donateAmount || isDonating || isDonateConfirming}
            >
              {isDonating || isDonateConfirming ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {isDonating ? 'Confirm in wallet...' : 'Processing...'}
                </>
              ) : (
                'Donate'
              )}
            </Button>
            {isDonateSuccess && (
              <div className="flex items-center gap-2 text-sm text-green-600">
                <CheckCircle className="h-4 w-4" />
                Donation successful!
              </div>
            )}
            {donateError && (
              <p className="text-sm text-destructive">
                {donateError.message || 'Transaction failed'}
              </p>
            )}
          </form>
        )}

        {/* Withdraw Button */}
        {canWithdraw && (
          <div className="space-y-2">
            <Button
              className="w-full"
              onClick={() => withdraw()}
              disabled={isWithdrawing || isWithdrawConfirming}
            >
              {isWithdrawing || isWithdrawConfirming ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {isWithdrawing ? 'Confirm in wallet...' : 'Processing...'}
                </>
              ) : (
                'Withdraw Funds'
              )}
            </Button>
            {isWithdrawSuccess && (
              <div className="flex items-center gap-2 text-sm text-green-600">
                <CheckCircle className="h-4 w-4" />
                Withdrawal successful!
              </div>
            )}
            {withdrawError && (
              <p className="text-sm text-destructive">
                {withdrawError.message || 'Transaction failed'}
              </p>
            )}
          </div>
        )}

        {/* Refund Button */}
        {canRefund && (
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Your contribution: {formatUserContribution(userContribution)}
            </p>
            <Button
              variant="outline"
              className="w-full"
              onClick={() => refund()}
              disabled={isRefunding || isRefundConfirming}
            >
              {isRefunding || isRefundConfirming ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {isRefunding ? 'Confirm in wallet...' : 'Processing...'}
                </>
              ) : (
                'Claim Refund'
              )}
            </Button>
            {isRefundSuccess && (
              <div className="flex items-center gap-2 text-sm text-green-600">
                <CheckCircle className="h-4 w-4" />
                Refund successful!
              </div>
            )}
            {refundError && (
              <p className="text-sm text-destructive">
                {refundError.message || 'Transaction failed'}
              </p>
            )}
          </div>
        )}

        {!canDonate && !canWithdraw && !canRefund && (
          <p className="text-sm text-muted-foreground text-center py-4">
            No actions available for this campaign
          </p>
        )}
      </CardContent>
    </Card>
  )
}

function InfoItem({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  )
}

function getStatusVariant(status: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'ACTIVE':
      return 'default'
    case 'SUCCESS':
      return 'secondary'
    case 'FAILED':
      return 'destructive'
    case 'WITHDRAWN':
      return 'outline'
    default:
      return 'outline'
  }
}

function formatStatus(status: string): string {
  switch (status) {
    case 'ACTIVE':
      return 'Active'
    case 'SUCCESS':
      return 'Successful'
    case 'FAILED':
      return 'Failed'
    case 'WITHDRAWN':
      return 'Withdrawn'
    default:
      return status
  }
}

function CampaignDetailSkeleton() {
  return (
    <div className="container py-8">
      <Skeleton className="h-10 w-40 mb-6" />
      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <Skeleton className="h-64 rounded-t-lg rounded-b-none" />
            <CardHeader>
              <Skeleton className="h-6 w-24 mb-2" />
              <Skeleton className="h-8 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-4 w-full mb-2" />
              <Skeleton className="h-4 w-full mb-2" />
              <Skeleton className="h-4 w-2/3" />
            </CardContent>
          </Card>
        </div>
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-32" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-4 w-full mb-2" />
              <Skeleton className="h-3 w-full mb-4" />
              <Skeleton className="h-20 w-full" />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
