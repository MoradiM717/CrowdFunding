import { getDefaultConfig } from '@rainbow-me/rainbowkit'
import { http } from 'wagmi'
import { mainnet, sepolia, hardhat } from 'wagmi/chains'

// Custom localhost chain for Hardhat with proper configuration
export const hardhatLocal = {
  ...hardhat,
  id: 31337,
  name: 'Hardhat Local',
  nativeCurrency: {
    decimals: 18,
    name: 'Ether',
    symbol: 'ETH',
  },
  rpcUrls: {
    default: {
      http: ['http://127.0.0.1:8545'],
    },
    public: {
      http: ['http://127.0.0.1:8545'],
    },
  },
} as const

// Determine which chains to enable based on environment
const isDev = import.meta.env.DEV || import.meta.env.MODE === 'development'

// In development, put Hardhat first; in production, use mainnet/sepolia
const chains = isDev
  ? [hardhatLocal, sepolia, mainnet] as const
  : [mainnet, sepolia, hardhatLocal] as const

export const config = getDefaultConfig({
  appName: 'Crowdfunding DApp',
  projectId: import.meta.env.VITE_WALLET_CONNECT_PROJECT_ID || 'test',
  chains,
  transports: {
    [hardhatLocal.id]: http('http://127.0.0.1:8545'),
    [sepolia.id]: http(),
    [mainnet.id]: http(),
  },
})

declare module 'wagmi' {
  interface Register {
    config: typeof config
  }
}
