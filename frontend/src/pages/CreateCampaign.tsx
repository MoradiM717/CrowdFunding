import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAccount, useChainId, useSwitchChain } from 'wagmi'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { format, addDays } from 'date-fns'
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  CheckCircle,
  Calendar,
  Info,
  AlertTriangle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useCreateCampaign } from '@/hooks/useContracts'
import { CAMPAIGN_CATEGORIES } from '@/types/api'
import { getFactoryAddress } from '@/lib/contracts'
import { hardhatLocal } from '@/lib/wagmi'

const createCampaignSchema = z.object({
  title: z.string().min(5, 'Title must be at least 5 characters').max(100, 'Title must be less than 100 characters'),
  description: z.string().min(20, 'Description must be at least 20 characters').max(5000, 'Description must be less than 5000 characters'),
  category: z.string().min(1, 'Please select a category'),
  goal: z.string().refine((val) => {
    const num = parseFloat(val)
    return !isNaN(num) && num >= 0.01
  }, 'Goal must be at least 0.01 ETH'),
  deadline: z.string().refine((val) => {
    const date = new Date(val)
    const minDate = addDays(new Date(), 1)
    return date > minDate
  }, 'Deadline must be at least 1 day from now'),
})

type CreateCampaignFormData = z.infer<typeof createCampaignSchema>

export function CreateCampaign() {
  const { address, isConnected } = useAccount()
  const chainId = useChainId()
  const { switchChain, isPending: isSwitching } = useSwitchChain()
  const [step, setStep] = useState<'form' | 'confirm' | 'success'>('form')

  // Check if factory is configured for current chain
  const factoryAddress = getFactoryAddress(chainId)
  const isWrongNetwork = !factoryAddress

  const {
    createCampaign,
    hash,
    isPending,
    isConfirming,
    isSuccess,
    error,
    reset,
  } = useCreateCampaign()

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isValid },
  } = useForm<CreateCampaignFormData>({
    resolver: zodResolver(createCampaignSchema),
    mode: 'onChange',
    defaultValues: {
      title: '',
      description: '',
      category: '',
      goal: '',
      deadline: format(addDays(new Date(), 30), "yyyy-MM-dd'T'HH:mm"),
    },
  })

  const formValues = watch()

  const onSubmit = async (data: CreateCampaignFormData) => {
    if (!isConnected || !address) return

    // For now, we'll create a simple CID placeholder
    // In production, this would upload to IPFS first
    const metadata = {
      title: data.title,
      description: data.description,
      category: data.category,
      creator: address,
      createdAt: new Date().toISOString(),
    }

    // Create a simple hash as placeholder CID
    // In production, upload to IPFS and get real CID
    const cid = btoa(JSON.stringify(metadata)).replace(/[^a-zA-Z0-9]/g, '').substring(0, 46)

    const deadlineTimestamp = Math.floor(new Date(data.deadline).getTime() / 1000)

    try {
      await createCampaign({
        goalEth: data.goal,
        deadline: deadlineTimestamp,
        cid: cid,
      })
    } catch (err) {
      console.error('Failed to create campaign:', err)
    }
  }

  // Watch for success and navigate
  if (isSuccess && hash && step !== 'success') {
    setStep('success')
  }

  if (!isConnected) {
    return (
      <div className="container max-w-2xl py-8">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-medium">Wallet not connected</p>
            <p className="text-sm text-muted-foreground mb-4">
              Please connect your wallet to create a campaign
            </p>
            <Button asChild>
              <Link to="/campaigns">Browse Campaigns</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Network check - show warning if on wrong network
  if (isWrongNetwork) {
    return (
      <div className="container max-w-2xl py-8">
        <Card className="border-yellow-500/50">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertTriangle className="h-12 w-12 text-yellow-500 mb-4" />
            <p className="text-lg font-medium">Wrong Network</p>
            <p className="text-sm text-muted-foreground mb-2 text-center">
              Campaign creation is not available on this network.
            </p>
            <p className="text-sm text-muted-foreground mb-6 text-center">
              Current network: <span className="font-mono font-medium">Chain ID {chainId}</span>
            </p>
            <div className="flex flex-col gap-3 w-full max-w-xs">
              <Button
                onClick={() => switchChain({ chainId: hardhatLocal.id })}
                disabled={isSwitching}
              >
                {isSwitching ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Switching...
                  </>
                ) : (
                  'Switch to Hardhat Local'
                )}
              </Button>
              <Button variant="outline" asChild>
                <Link to="/campaigns">Browse Campaigns</Link>
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-6 text-center">
              Make sure your Hardhat node is running at http://127.0.0.1:8545
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (step === 'success') {
    return (
      <div className="container max-w-2xl py-8">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <CheckCircle className="h-12 w-12 text-green-500 mb-4" />
            <p className="text-lg font-medium">Campaign Created!</p>
            <p className="text-sm text-muted-foreground mb-4">
              Your campaign has been successfully created on the blockchain.
            </p>
            {hash && (
              <p className="text-xs text-muted-foreground mb-4 font-mono">
                Transaction: {hash.substring(0, 20)}...
              </p>
            )}
            <div className="flex gap-4">
              <Button asChild>
                <Link to="/campaigns">View Campaigns</Link>
              </Button>
              <Button variant="outline" onClick={() => {
                reset()
                setStep('form')
              }}>
                Create Another
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container max-w-2xl py-8">
      {/* Back Button */}
      <Button variant="ghost" asChild className="mb-6">
        <Link to="/campaigns">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Campaigns
        </Link>
      </Button>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Create a Campaign</CardTitle>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/10 text-green-600 text-sm font-medium">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              {chainId === 31337 ? 'Hardhat Local' : `Chain ${chainId}`}
            </div>
          </div>
          <CardDescription>
            Launch your crowdfunding campaign on the blockchain. All campaigns are
            transparent and funds are managed by smart contracts.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Title */}
            <div className="space-y-2">
              <Label htmlFor="title">Campaign Title</Label>
              <Input
                id="title"
                placeholder="Give your campaign a catchy title"
                {...register('title')}
                disabled={isPending || isConfirming}
              />
              {errors.title && (
                <p className="text-sm text-destructive">{errors.title.message}</p>
              )}
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Describe your campaign, what you're raising funds for, and how they'll be used..."
                rows={6}
                {...register('description')}
                disabled={isPending || isConfirming}
              />
              <p className="text-xs text-muted-foreground">
                {formValues.description?.length || 0} / 5000 characters
              </p>
              {errors.description && (
                <p className="text-sm text-destructive">{errors.description.message}</p>
              )}
            </div>

            {/* Category */}
            <div className="space-y-2">
              <Label>Category</Label>
              <Select
                value={formValues.category}
                onValueChange={(value) => setValue('category', value, { shouldValidate: true })}
                disabled={isPending || isConfirming}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a category" />
                </SelectTrigger>
                <SelectContent>
                  {CAMPAIGN_CATEGORIES.map((category) => (
                    <SelectItem key={category.value} value={category.value}>
                      {category.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.category && (
                <p className="text-sm text-destructive">{errors.category.message}</p>
              )}
            </div>

            {/* Goal */}
            <div className="space-y-2">
              <Label htmlFor="goal">Funding Goal (ETH)</Label>
              <Input
                id="goal"
                type="number"
                step="0.01"
                min="0.01"
                placeholder="1.0"
                {...register('goal')}
                disabled={isPending || isConfirming}
              />
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Info className="h-3 w-3" />
                Set a realistic goal. You'll need to reach this to withdraw funds.
              </p>
              {errors.goal && (
                <p className="text-sm text-destructive">{errors.goal.message}</p>
              )}
            </div>

            {/* Deadline */}
            <div className="space-y-2">
              <Label htmlFor="deadline">Campaign Deadline</Label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="deadline"
                  type="datetime-local"
                  className="pl-10"
                  min={format(addDays(new Date(), 1), "yyyy-MM-dd'T'HH:mm")}
                  {...register('deadline')}
                  disabled={isPending || isConfirming}
                />
              </div>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Info className="h-3 w-3" />
                Campaign must run for at least 1 day
              </p>
              {errors.deadline && (
                <p className="text-sm text-destructive">{errors.deadline.message}</p>
              )}
            </div>

            {/* Error Display */}
            {error && (
              <div className="p-4 rounded-lg bg-destructive/10 text-destructive text-sm">
                <p className="font-medium">Transaction failed</p>
                <p>{error.message || 'An error occurred while creating the campaign'}</p>
              </div>
            )}

            {/* Submit Button */}
            <Button
              type="submit"
              className="w-full"
              size="lg"
              disabled={!isValid || isPending || isConfirming}
            >
              {isPending || isConfirming ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {isPending ? 'Confirm in wallet...' : 'Creating campaign...'}
                </>
              ) : (
                'Create Campaign'
              )}
            </Button>

            {/* Info Box */}
            <div className="p-4 rounded-lg bg-muted text-sm">
              <p className="font-medium mb-2">How it works:</p>
              <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                <li>Your campaign will be created as a smart contract</li>
                <li>Contributors send ETH directly to the contract</li>
                <li>If you reach your goal, you can withdraw the funds</li>
                <li>If you don't reach your goal, contributors can get refunds</li>
              </ul>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
