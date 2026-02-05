import { Link } from 'react-router-dom'
import { Clock, Users, Target } from 'lucide-react'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Campaign, CampaignWithMetadata } from '@/types/api'
import { shortenAddress, formatTimeRemaining } from '@/lib/utils'

interface CampaignCardProps {
  campaign: Campaign | CampaignWithMetadata
}

export function CampaignCard({ campaign }: CampaignCardProps) {
  const progress = campaign.progress_percent
  const timeRemaining = formatTimeRemaining(campaign.deadline_iso)
  const isEnded = new Date(campaign.deadline_iso) < new Date()
  const metadata = 'metadata' in campaign ? campaign.metadata : undefined

  return (
    <Link to={`/campaign/${campaign.address}`}>
      <Card className="h-full overflow-hidden transition-all hover:shadow-lg hover:border-primary/50">
        {/* Image placeholder - could be from IPFS metadata */}
        <div className="h-48 bg-gradient-to-br from-primary/20 via-primary/10 to-background flex items-center justify-center">
          <Target className="h-16 w-16 text-primary/40" />
        </div>

        <CardHeader className="space-y-2">
          <div className="flex items-center justify-between">
            <Badge variant={getStatusVariant(campaign.status)}>
              {formatStatus(campaign.status)}
            </Badge>
            {metadata?.category && (
              <Badge variant="outline">{metadata.category}</Badge>
            )}
          </div>
          <CardTitle className="line-clamp-2">
            {metadata?.name || `Campaign ${shortenAddress(campaign.address)}`}
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Progress */}
          <div className="space-y-2">
            <Progress value={progress} className="h-2" />
            <div className="flex justify-between text-sm">
              <span className="font-medium">{campaign.total_raised_eth} ETH</span>
              <span className="text-muted-foreground">
                of {campaign.goal_eth} ETH goal
              </span>
            </div>
          </div>

          {/* Stats Row */}
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <div className="flex items-center gap-1">
              <Users className="h-4 w-4" />
              <span>contributors</span>
            </div>
            <div className="flex items-center gap-1">
              <Clock className="h-4 w-4" />
              <span>{isEnded ? 'Ended' : timeRemaining}</span>
            </div>
          </div>
        </CardContent>

        <CardFooter className="pt-0">
          <div className="w-full flex items-center justify-between text-xs text-muted-foreground">
            <span>by {shortenAddress(campaign.creator_address)}</span>
            <span>{progress.toFixed(0)}% funded</span>
          </div>
        </CardFooter>
      </Card>
    </Link>
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
