import hre from "hardhat";
import { ethers } from "ethers";

async function main() {
    // Factory address from your deployment (use FACTORY_ADDRESS env var or default)
    // You can set it like: FACTORY_ADDRESS=0x... npx hardhat run scripts/create-campaign.ts --network localhost
    const factoryAddress = process.env.FACTORY_ADDRESS || "0x5FbDB2315678afecb367f032d93F642f64180aa3";

    // Get the provider
    const provider = new ethers.JsonRpcProvider("http://127.0.0.1:8545");

    // Creator account (Account #1 from Hardhat node)
    const creatorPrivateKey = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d";
    const creator = new ethers.Wallet(creatorPrivateKey, provider);

    console.log("Creating campaign with creator:", creator.address);

    // Get factory contract
    const CampaignFactoryArtifact = await hre.artifacts.readArtifact("CampaignFactory");
    const factory = new ethers.Contract(
        factoryAddress,
        CampaignFactoryArtifact.abi,
        creator
    );

    // Campaign parameters
    const goal = ethers.parseEther("5"); // 5 ETH goal
    const deadline = BigInt(Math.floor(Date.now() / 1000) + 86400 * 7); // 7 days from now
    const cid = `QmTestCampaign2${Date.now()}`; // Unique CID

    console.log("\nCampaign Parameters:");
    console.log("  Goal:", ethers.formatEther(goal), "ETH");
    console.log("  Deadline:", new Date(Number(deadline) * 1000).toLocaleString());
    console.log("  CID:", cid);

    // Create campaign
    const tx = await factory.createCampaign(goal, deadline, cid);
    console.log("\nTransaction sent:", tx.hash);

    const receipt = await tx.wait();
    console.log("Transaction confirmed in block:", receipt.blockNumber);

    // Get campaign address from event
    const iface = new ethers.Interface(CampaignFactoryArtifact.abi);
    const campaignCreatedEvent = receipt.logs.find(
        (log: any) => {
            try {
                const parsed = iface.parseLog(log);
                return parsed?.name === "CampaignCreated";
            } catch {
                return false;
            }
        }
    );

    if (campaignCreatedEvent) {
        const parsed = iface.parseLog(campaignCreatedEvent);
        const campaignAddress = parsed?.args[1];
        console.log("\n✅ Campaign created successfully!");
        console.log("Campaign address:", campaignAddress);
        console.log("\nThe indexer should pick this up automatically.");
    } else {
        console.log("\n⚠️  CampaignCreated event not found in receipt");
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });

