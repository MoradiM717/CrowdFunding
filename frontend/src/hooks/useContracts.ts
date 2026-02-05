import { useReadContract, useWriteContract, useWaitForTransactionReceipt, useChainId } from 'wagmi'
import { parseEther } from 'viem'
import { campaignFactoryAbi, campaignAbi, getFactoryAddress, getCampaignConfig } from '@/lib/contracts'

// ============================================================================
// Campaign Factory Hooks
// ============================================================================

/**
 * Hook to get the current factory address based on connected chain
 */
export function useFactoryAddress() {
  const chainId = useChainId()
  return getFactoryAddress(chainId)
}

/**
 * Hook to create a new campaign via the CampaignFactory contract
 */
export function useCreateCampaign() {
  const chainId = useChainId()
  const factoryAddress = getFactoryAddress(chainId)
  const { writeContract, data: hash, isPending, error, reset } = useWriteContract()

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  })

  const createCampaign = async (args: {
    goalEth: string
    deadline: number
    cid: string
  }) => {
    if (!factoryAddress) {
      throw new Error(`Factory address not configured for chain ${chainId}`)
    }

    const goalWei = parseEther(args.goalEth)

    writeContract({
      address: factoryAddress,
      abi: campaignFactoryAbi,
      functionName: 'createCampaign',
      args: [goalWei, BigInt(args.deadline), args.cid],
    })
  }

  return {
    createCampaign,
    hash,
    isPending,
    isConfirming,
    isSuccess,
    error,
    reset,
    factoryAddress,
    chainId,
  }
}

/**
 * Hook to get total number of campaigns from factory
 */
export function useCampaignCount() {
  const chainId = useChainId()
  const factoryAddress = getFactoryAddress(chainId)

  return useReadContract({
    address: factoryAddress,
    abi: campaignFactoryAbi,
    functionName: 'getCampaignCount',
    query: {
      enabled: !!factoryAddress,
    },
  })
}

/**
 * Hook to get all campaign addresses from factory
 */
export function useAllCampaigns() {
  const chainId = useChainId()
  const factoryAddress = getFactoryAddress(chainId)

  return useReadContract({
    address: factoryAddress,
    abi: campaignFactoryAbi,
    functionName: 'getAllCampaigns',
    query: {
      enabled: !!factoryAddress,
    },
  })
}

/**
 * Hook to get campaigns by a specific creator from factory
 */
export function useCreatorCampaignsOnChain(creatorAddress: `0x${string}` | undefined) {
  const chainId = useChainId()
  const factoryAddress = getFactoryAddress(chainId)

  return useReadContract({
    address: factoryAddress,
    abi: campaignFactoryAbi,
    functionName: 'getCampaignsByCreator',
    args: creatorAddress ? [creatorAddress] : undefined,
    query: {
      enabled: !!creatorAddress && !!factoryAddress,
    },
  })
}

// ============================================================================
// Campaign Contract Hooks
// ============================================================================

/**
 * Hook to donate to a campaign
 */
export function useDonate(campaignAddress: `0x${string}`) {
  const { writeContract, data: hash, isPending, error, reset } = useWriteContract()

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  })

  const donate = (amountEth: string) => {
    const amountWei = parseEther(amountEth)

    writeContract({
      ...getCampaignConfig(campaignAddress),
      functionName: 'donate',
      value: amountWei,
    })
  }

  return {
    donate,
    hash,
    isPending,
    isConfirming,
    isSuccess,
    error,
    reset,
  }
}

/**
 * Hook to withdraw funds from a successful campaign (creator only)
 */
export function useWithdraw(campaignAddress: `0x${string}`) {
  const { writeContract, data: hash, isPending, error, reset } = useWriteContract()

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  })

  const withdraw = () => {
    writeContract({
      ...getCampaignConfig(campaignAddress),
      functionName: 'withdraw',
    })
  }

  return {
    withdraw,
    hash,
    isPending,
    isConfirming,
    isSuccess,
    error,
    reset,
  }
}

/**
 * Hook to refund contribution from a failed campaign (donor only)
 */
export function useRefund(campaignAddress: `0x${string}`) {
  const { writeContract, data: hash, isPending, error, reset } = useWriteContract()

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  })

  const refund = () => {
    writeContract({
      ...getCampaignConfig(campaignAddress),
      functionName: 'refund',
    })
  }

  return {
    refund,
    hash,
    isPending,
    isConfirming,
    isSuccess,
    error,
    reset,
  }
}

// ============================================================================
// Campaign Read Hooks
// ============================================================================

/**
 * Hook to read a user's contribution to a campaign
 */
export function useContributionOf(
  campaignAddress: `0x${string}` | undefined,
  userAddress: `0x${string}` | undefined
) {
  return useReadContract({
    address: campaignAddress,
    abi: campaignAbi,
    functionName: 'contributionOf',
    args: userAddress ? [userAddress] : undefined,
    query: {
      enabled: !!campaignAddress && !!userAddress,
    },
  })
}

/**
 * Hook to read campaign creator address
 */
export function useCampaignCreator(campaignAddress: `0x${string}` | undefined) {
  return useReadContract({
    address: campaignAddress,
    abi: campaignAbi,
    functionName: 'creator',
    query: {
      enabled: !!campaignAddress,
    },
  })
}

/**
 * Hook to read campaign goal
 */
export function useCampaignGoal(campaignAddress: `0x${string}` | undefined) {
  return useReadContract({
    address: campaignAddress,
    abi: campaignAbi,
    functionName: 'goal',
    query: {
      enabled: !!campaignAddress,
    },
  })
}

/**
 * Hook to read campaign deadline
 */
export function useCampaignDeadline(campaignAddress: `0x${string}` | undefined) {
  return useReadContract({
    address: campaignAddress,
    abi: campaignAbi,
    functionName: 'deadline',
    query: {
      enabled: !!campaignAddress,
    },
  })
}

/**
 * Hook to read campaign total raised
 */
export function useCampaignTotalRaised(campaignAddress: `0x${string}` | undefined) {
  return useReadContract({
    address: campaignAddress,
    abi: campaignAbi,
    functionName: 'totalRaised',
    query: {
      enabled: !!campaignAddress,
    },
  })
}

/**
 * Hook to read if campaign has been withdrawn
 */
export function useCampaignWithdrawn(campaignAddress: `0x${string}` | undefined) {
  return useReadContract({
    address: campaignAddress,
    abi: campaignAbi,
    functionName: 'withdrawn',
    query: {
      enabled: !!campaignAddress,
    },
  })
}

/**
 * Hook to read campaign CID (IPFS metadata hash)
 */
export function useCampaignCid(campaignAddress: `0x${string}` | undefined) {
  return useReadContract({
    address: campaignAddress,
    abi: campaignAbi,
    functionName: 'cid',
    query: {
      enabled: !!campaignAddress,
    },
  })
}

/**
 * Hook to check if a user has refunded from a campaign
 */
export function useHasRefunded(
  campaignAddress: `0x${string}` | undefined,
  userAddress: `0x${string}` | undefined
) {
  return useReadContract({
    address: campaignAddress,
    abi: campaignAbi,
    functionName: 'hasRefunded',
    args: userAddress ? [userAddress] : undefined,
    query: {
      enabled: !!campaignAddress && !!userAddress,
    },
  })
}
