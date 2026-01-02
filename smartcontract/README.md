# Crowdfunding Smart Contracts

Production-ready Solidity smart contracts for a hybrid Web2/Web3 crowdfunding platform using the Factory-Campaign pattern.

## Overview

This project implements a decentralized crowdfunding system where:
- A **Factory** contract creates independent **Campaign** contracts
- Each campaign accepts ETH donations toward a funding goal
- Campaign creators can withdraw funds when the goal is met
- Donors can refund their contributions if the goal is not met by the deadline

## Architecture

### Factory-Campaign Pattern

The system uses a factory pattern where:
- `CampaignFactory` deploys new `Campaign` contracts
- Each campaign is an independent contract with its own state
- The factory tracks all created campaigns

### Campaign Lifecycle

1. **Created**: Campaign is deployed with goal, deadline, and IPFS CID
2. **Active**: Accepting donations (before deadline, not withdrawn)
3. **Success**: Goal met (`totalRaised >= goal`) - creator can withdraw
4. **Failure**: Deadline passed and goal not met - donors can refund
5. **Closed**: Funds withdrawn or refunds processed

## Prerequisites

- Node.js (v18 or higher)
- npm or yarn
- Git

## Installation

1. Clone the repository and navigate to the smartcontract directory:
```bash
cd smartcontract
```

2. Install dependencies:
```bash
npm install
```

## Project Structure

```
smartcontract/
├── contracts/
│   ├── Campaign.sol          # Main campaign contract
│   └── CampaignFactory.sol   # Factory contract
├── test/
│   ├── Campaign.test.ts      # Campaign contract tests
│   └── CampaignFactory.test.ts # Factory contract tests
├── scripts/
│   └── deploy.ts             # Deployment script
├── hardhat.config.ts         # Hardhat configuration
├── tsconfig.json             # TypeScript configuration
└── README.md                  # This file
```

## Usage

### Compile Contracts

```bash
npm run compile
```

### Run Tests

```bash
npm run test
```

### Deploy Contracts

Deploy to local Hardhat network:
```bash
npm run deploy
```

Or to a specific network (configure in `hardhat.config.ts`):
```bash
npx hardhat run scripts/deploy.ts --network <network-name>
```

### Test Coverage

```bash
npm run coverage
```

## Local Development

### Start Local Hardhat Node

In one terminal:
```bash
npx hardhat node
```

This starts a local Ethereum node at `http://127.0.0.1:8545` with 20 test accounts.

### Deploy to Local Node

In another terminal:
```bash
npm run deploy
```

## Contract Details

### CampaignFactory

**Functions:**
- `createCampaign(uint256 goal, uint256 deadline, string memory cid)`: Creates a new campaign
- `getCampaigns()`: Returns all created campaigns
- `getCampaignsByCreator(address creator)`: Returns campaigns by a specific creator
- `getCampaignCount()`: Returns total number of campaigns

**Events:**
- `CampaignCreated(address indexed factory, address indexed campaign, address indexed creator, uint256 goal, uint256 deadline, string cid)`

### Campaign

**State Variables:**
- `creator`: Campaign creator address (immutable)
- `goal`: Fundraising target in wei (immutable)
- `deadline`: Campaign end timestamp (immutable)
- `cid`: IPFS content identifier (immutable)
- `totalRaised`: Total contributions received
- `withdrawn`: Whether funds have been withdrawn
- `contributions`: Mapping of donor addresses to contribution amounts
- `refunded`: Mapping of donor addresses to refund status

**Functions:**
- `donate()`: Accept ETH donations (payable)
- `withdraw()`: Creator withdraws funds when goal is met
- `refund()`: Donor refunds contribution when campaign fails
- `getSummary()`: Returns campaign summary information
- `contributionOf(address)`: Returns contribution amount for an address
- `isActive()`: Checks if campaign is accepting donations
- `isSuccessful()`: Checks if goal is met
- `isFailed()`: Checks if deadline passed and goal not met

**Events:**
- `DonationReceived(address indexed campaign, address indexed donor, uint256 amount, uint256 newTotalRaised, uint256 timestamp)`
- `Withdrawn(address indexed campaign, address indexed creator, uint256 amount, uint256 timestamp)`
- `Refunded(address indexed campaign, address indexed donor, uint256 amount, uint256 timestamp)`

## Event Structure for Indexer

All events are designed for off-chain indexing. The indexer should listen for:

### CampaignCreated
Emitted when a new campaign is created.
- `factory`: Factory contract address
- `campaign`: New campaign contract address
- `creator`: Campaign creator address
- `goal`: Fundraising goal in wei
- `deadline`: Campaign deadline timestamp
- `cid`: IPFS content identifier

### DonationReceived
Emitted on every donation.
- `campaign`: Campaign contract address
- `donor`: Donor address
- `amount`: Donation amount in wei
- `newTotalRaised`: Updated total raised after this donation
- `timestamp`: Block timestamp

### Withdrawn
Emitted when creator withdraws funds.
- `campaign`: Campaign contract address
- `creator`: Creator address
- `amount`: Withdrawn amount in wei
- `timestamp`: Block timestamp

### Refunded
Emitted when a donor refunds their contribution.
- `campaign`: Campaign contract address
- `donor`: Donor address
- `amount`: Refunded amount in wei
- `timestamp`: Block timestamp

## Security Features

1. **ReentrancyGuard**: All money-moving functions are protected against reentrancy attacks
2. **Custom Errors**: Gas-efficient error handling
3. **Checks-Effects-Interactions**: Follows CEI pattern for secure state changes
4. **Safe ETH Transfers**: Uses `call{value: ...}("")` instead of deprecated `transfer()`
5. **Input Validation**: Comprehensive validation of all inputs
6. **State Machine**: Enforced state transitions prevent invalid operations

## Testing

The test suite covers:
- Factory deployment and campaign creation
- Donation functionality and edge cases
- Withdrawal scenarios (success cases and failures)
- Refund scenarios (failure cases and edge cases)
- View function correctness
- Reentrancy protection
- Event emission verification

Run tests with:
```bash
npm run test
```

## Gas Optimization

- Uses `immutable` for constant values (creator, goal, deadline, cid)
- Custom errors instead of revert strings
- Minimal storage operations
- Efficient event structure

## Network Configuration

Configure networks in `hardhat.config.ts`:

```typescript
networks: {
  hardhat: {
    chainId: 1337,
  },
  localhost: {
    url: "http://127.0.0.1:8545",
  },
  // Add other networks as needed
}
```

## Troubleshooting

### Compilation Issues

If you encounter compilation errors:
1. Ensure all dependencies are installed: `npm install`
2. Check Solidity version compatibility (^0.8.20)
3. Verify OpenZeppelin contracts are installed

### Hardhat Configuration

Hardhat 3.x requires ESM (ES Modules). Ensure:
- `package.json` has `"type": "module"`
- `tsconfig.json` uses `"module": "ESNext"`
- Config file uses ESM syntax (`import`/`export`)

### Test Failures

If tests fail:
1. Check that Hardhat network helpers are properly imported
2. Verify time manipulation functions are used correctly for deadline tests
3. Ensure test accounts have sufficient balance

## License

MIT

## Contributing

1. Follow Solidity style guide
2. Write comprehensive tests for new features
3. Update documentation
4. Ensure all tests pass before submitting

## Support

For issues or questions, please open an issue in the repository.

