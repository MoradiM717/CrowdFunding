# Hardhat Local Network Setup Guide

This guide will help you set up a local Hardhat blockchain network for testing your crowdfunding smart contracts.

## Prerequisites

- Node.js installed
- All dependencies installed (`npm install`)

## Step-by-Step Setup

### 1. Verify Hardhat Installation

```bash
npx hardhat --version
# Should output: 3.1.2
```

### 2. Compile Contracts

```bash
npx hardhat compile
```

You should see: "Compiled 2 Solidity files" (Campaign.sol and CampaignFactory.sol)

### 3. Start Local Hardhat Node

In your **first terminal**, run:

```bash
npx hardhat node
```

This will:
- Start a local blockchain at `http://127.0.0.1:8545`
- Use chain ID `31337`
- Create 20 test accounts with 10000 ETH each
- **Keep this terminal running** - this is your local blockchain

You'll see output like:
```
Started HTTP and WebSocket JSON-RPC server at http://127.0.0.1:8545/

Accounts
========
Account #0: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 (10000 ETH)
Private Key: 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
...
```

### 4. Deploy Contracts to Local Network

In a **new terminal** (keep the first one running), navigate to the smartcontract directory and run:

```bash
cd smartcontract
npx hardhat run scripts/deploy.ts --network localhost
```

This will:
- Deploy the CampaignFactory contract
- Create a sample campaign
- Make a sample donation
- Print all contract addresses

You should see output like:
```
Deploying CampaignFactory...
CampaignFactory deployed to: 0x5FbDB2315678afecb367f032d93F642f64180aa3
Campaign created at: 0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
...
```

### 5. Interact with Contracts (Optional)

You can use Hardhat console to interact with your contracts:

```bash
npx hardhat console --network localhost
```

In the console, you can:
```javascript
// Get the factory
const Factory = await ethers.getContractFactory("CampaignFactory");
const factory = await Factory.attach("0x5FbDB2315678afecb367f032d93F642f64180aa3");

// Get campaigns
const campaigns = await factory.getCampaigns();
console.log("Campaigns:", campaigns);

// Interact with a campaign
const Campaign = await ethers.getContractFactory("Campaign");
const campaign = Campaign.attach(campaigns[0]);

// Check campaign status
const summary = await campaign.getSummary();
console.log("Summary:", summary);
```

### 6. Configure Your Indexer

Point your indexer to the local Hardhat network:

**Environment variables:**
```bash
RPC_URL=http://127.0.0.1:8545
CHAIN_ID=31337
```

### 7. Test Your Indexer

1. Start the Hardhat node (Step 3)
2. Deploy contracts (Step 4)
3. Start your indexer with the RPC URL above
4. Trigger on-chain actions:
   - Create new campaigns
   - Make donations
   - Withdraw funds (when goal met)
   - Request refunds (when goal not met)
5. Verify your indexer catches all events and updates the database

### 8. Use Remix with Hardhat Network (Optional)

If you want to use Remix UI but still test against your local Hardhat network:

1. Start `npx hardhat node` (Step 3)
2. Add network to MetaMask:
   - Network Name: `Hardhat Local`
   - RPC URL: `http://127.0.0.1:8545`
   - Chain ID: `31337`
   - Currency Symbol: `ETH`
3. Import a test account from Hardhat node output (use the private key)
4. In Remix:
   - Go to **Deploy & Run Transactions**
   - Select **Injected Provider - MetaMask**
   - Deploy and interact with contracts
5. Your indexer will see all transactions because they're on the same local network

## Network Information

- **RPC URL**: `http://127.0.0.1:8545`
- **Chain ID**: `31337`
- **Network Name**: `localhost` (in Hardhat config)
- **Default Accounts**: 20 test accounts with 10000 ETH each

## Troubleshooting

### "Cannot connect to network"
- Make sure `npx hardhat node` is running in another terminal
- Check that the RPC URL is correct: `http://127.0.0.1:8545`

### "Nonce too high" errors
- Restart the Hardhat node to reset the chain state
- This will give you a fresh blockchain

### Contracts not deploying
- Verify contracts compile: `npx hardhat compile`
- Check that you're using `--network localhost` flag
- Ensure the Hardhat node is running

## Quick Reference Commands

```bash
# Compile contracts
npx hardhat compile

# Start local node (keep running)
npx hardhat node

# Deploy to local network (in new terminal)
npx hardhat run scripts/deploy.ts --network localhost

# Open console (in new terminal)
npx hardhat console --network localhost

# Run tests
npx hardhat test
```

## Next Steps

1. ✅ Set up local Hardhat network
2. ✅ Deploy contracts
3. ✅ Configure indexer to listen to local network
4. ✅ Test full flow: create campaign → donate → withdraw/refund
5. ✅ Verify indexer captures all events correctly

