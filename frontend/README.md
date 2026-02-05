# Crowdfunding Frontend

A decentralized crowdfunding application built with React, TypeScript, and blockchain technology.

## Tech Stack

- **Framework**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS + shadcn/ui components
- **Routing**: React Router v6
- **State Management**: TanStack Query (React Query) for server state
- **Blockchain**: wagmi v2 + viem + RainbowKit for wallet connectivity
- **Forms**: React Hook Form + Zod validation

## Features

- **Campaign Management**: Browse, create, and manage crowdfunding campaigns
- **Wallet Integration**: Connect wallet via RainbowKit (MetaMask, WalletConnect, etc.)
- **Campaign Actions**: Donate to campaigns, withdraw funds (creators), claim refunds
- **Statistics Dashboard**: Platform-wide stats and leaderboards
- **Profile Pages**: View creator/donor profiles and history
- **Dark Mode**: Toggle between light and dark themes
- **Responsive Design**: Mobile-friendly layout

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Start development server
npm run dev
```

### Environment Variables

Create a `.env` file with the following variables:

```env
# API Base URL (defaults to /api/v1 for proxy)
VITE_API_URL=/api/v1

# WalletConnect Project ID (get one at https://cloud.walletconnect.com)
VITE_WALLET_CONNECT_PROJECT_ID=your_project_id

# Campaign Factory Contract Address
VITE_FACTORY_ADDRESS=0x...
```

### Development

```bash
# Start dev server (port 3000)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type check
npm run typecheck
```

## Project Structure

```
src/
├── components/
│   ├── campaigns/       # Campaign-specific components
│   ├── common/          # Shared components (ErrorBoundary, Loading)
│   ├── layout/          # Layout components (Header, Footer)
│   └── ui/              # shadcn/ui components
├── hooks/
│   ├── useApi.ts        # TanStack Query hooks for API
│   └── useContracts.ts  # wagmi hooks for smart contracts
├── lib/
│   ├── abi/             # Smart contract ABIs
│   ├── api.ts           # API client
│   ├── contracts.ts     # Contract configuration
│   ├── utils.ts         # Utility functions
│   └── wagmi.ts         # wagmi configuration
├── pages/               # Page components
├── types/
│   └── api.ts           # TypeScript types for API
├── App.tsx              # Main app with providers
└── main.tsx             # Entry point
```

## Pages

| Route | Description |
|-------|-------------|
| `/` | Home page with stats and trending campaigns |
| `/campaigns` | Browse all campaigns with filters |
| `/campaign/:address` | Campaign detail page |
| `/create` | Create a new campaign |
| `/profile` | Current user's profile |
| `/profile/:address` | View any address's profile |
| `/stats` | Platform statistics and leaderboards |

## API Integration

The frontend connects to the Django backend API at `/api/v1`. In development, Vite proxies requests to `http://localhost:8000`.

### Key API Endpoints

- `GET /campaigns/` - List campaigns
- `GET /campaigns/:address/` - Campaign details
- `GET /stats/platform/` - Platform statistics
- `GET /stats/trending/` - Trending campaigns
- `GET /creators/:address/campaigns/` - Creator's campaigns
- `GET /donors/:address/contributions/` - Donor's contributions

## Smart Contract Integration

The frontend interacts with two smart contracts:

1. **CampaignFactory**: Creates new campaigns
2. **Campaign**: Individual campaign contract for donations, withdrawals, and refunds

All contract interactions are handled through wagmi hooks in `src/hooks/useContracts.ts`.

## Styling

The project uses:
- Tailwind CSS for utility-first styling
- shadcn/ui components for consistent UI
- CSS variables for theming (light/dark mode)
- Responsive design with mobile-first approach

## Building for Production

```bash
npm run build
```

The build output will be in the `dist/` directory, ready for deployment.

## License

MIT
