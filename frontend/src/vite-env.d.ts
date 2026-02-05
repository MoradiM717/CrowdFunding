/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_WALLET_CONNECT_PROJECT_ID: string
  // Factory addresses per chain
  readonly VITE_FACTORY_ADDRESS: string // Hardhat Local (31337)
  readonly VITE_SEPOLIA_FACTORY_ADDRESS?: string // Sepolia Testnet (11155111)
  readonly VITE_MAINNET_FACTORY_ADDRESS?: string // Ethereum Mainnet (1)
  // Vite built-in
  readonly DEV: boolean
  readonly PROD: boolean
  readonly MODE: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module '*.css' {
  const content: { [className: string]: string }
  export default content
}
