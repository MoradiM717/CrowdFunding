import CampaignFactoryABI from './abi/CampaignFactory.json'
import CampaignABI from './abi/Campaign.json'

export const campaignFactoryAbi = CampaignFactoryABI
export const campaignAbi = CampaignABI

// Factory addresses per chain
// You can add more chains here as you deploy to them
const FACTORY_ADDRESSES: Record<number, `0x${string}` | undefined> = {
  // Hardhat Local (31337)
  31337: import.meta.env.VITE_FACTORY_ADDRESS as `0x${string}` | undefined,
  // Sepolia Testnet (11155111)
  11155111: import.meta.env.VITE_SEPOLIA_FACTORY_ADDRESS as `0x${string}` | undefined,
  // Ethereum Mainnet (1)
  1: import.meta.env.VITE_MAINNET_FACTORY_ADDRESS as `0x${string}` | undefined,
}

// Default factory address (for backward compatibility)
export const FACTORY_ADDRESS = import.meta.env.VITE_FACTORY_ADDRESS as `0x${string}` | undefined

/**
 * Get factory address for a specific chain
 */
export function getFactoryAddress(chainId: number): `0x${string}` | undefined {
  return FACTORY_ADDRESSES[chainId] || FACTORY_ADDRESS
}

/**
 * Get factory config for a specific chain
 */
export function getFactoryConfig(chainId: number) {
  return {
    address: getFactoryAddress(chainId),
    abi: campaignFactoryAbi,
  } as const
}

// Legacy config (uses default factory address)
export const campaignFactoryConfig = {
  address: FACTORY_ADDRESS,
  abi: campaignFactoryAbi,
} as const

export function getCampaignConfig(address: `0x${string}`) {
  return {
    address,
    abi: campaignAbi,
  } as const
}
