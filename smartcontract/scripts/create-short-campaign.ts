import hre from "hardhat";
import { ethers } from "ethers";

/**
 * Create a campaign with a short deadline (for testing refunds)
 * Usage: FACTORY_ADDRESS=0x... npx hardhat run scripts/create-short-campaign.ts --network localhost
 * 
 * This creates a campaign with:
 * - 100 ETH goal (unlikely to be met)
 * - 60 second deadline (for quick testing of refund flow)
 */
async function main() {
    const factoryAddress = process.env.FACTORY_ADDRESS || "0x5FbDB2315678afecb367f032d93F642f64180aa3";

    // Get the provider
    const provider = new ethers.JsonRpcProvider("http://127.0.0.1:8545");

    // Creator account (Account #1 from Hardhat node)
    const creatorPrivateKey = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d";
    const creator = new ethers.Wallet(creatorPrivateKey, provider);

    console.log("Creating SHORT campaign (60s deadline) for refund testing");
    console.log("Creator:", creator.address);
    console.log("Factory:", factoryAddress);

    // Get factory contract
    const CampaignFactoryArtifact = await hre.artifacts.readArtifact("CampaignFactory");
    const factory = new ethers.Contract(factoryAddress, CampaignFactoryArtifact.abi, creator);

    // Campaign parameters - high goal, short deadline
    const goal = ethers.parseEther("5"); // 5 ETH goal (< 9.2 ETH bigint limit, won't be met)
    const deadline = BigInt(Math.floor(Date.now() / 1000) + 60); // 60 seconds from now
    const cid = `QmShortCampaign${Date.now()}`;

    console.log("\n📋 Campaign Parameters:");
    console.log("  Goal:", ethers.formatEther(goal), "ETH (high - for testing failure)");
    console.log("  Deadline:", new Date(Number(deadline) * 1000).toLocaleString());
    console.log("  Time until deadline: 60 seconds");
    console.log("  CID:", cid);

    // Create campaign
    const tx = await factory.createCampaign(goal, deadline, cid);
    console.log("\n📤 Transaction sent:", tx.hash);

    const receipt = await tx.wait();
    console.log("✅ Transaction confirmed in block:", receipt.blockNumber);

    // Get campaign address from event
    const iface = new ethers.Interface(CampaignFactoryArtifact.abi);
    const campaignCreatedEvent = receipt.logs.find((log: any) => {
        try {
            const parsed = iface.parseLog(log);
            return parsed?.name === "CampaignCreated";
        } catch {
            return false;
        }
    });

    if (campaignCreatedEvent) {
        const parsed = iface.parseLog(campaignCreatedEvent);
        const campaignAddress = parsed?.args[1];

        console.log("\n═══════════════════════════════════════════════════════════");
        console.log("🎉 SHORT CAMPAIGN CREATED!");
        console.log("═══════════════════════════════════════════════════════════");
        console.log("\nCampaign address:", campaignAddress);

        console.log("\n📝 TESTING WORKFLOW:");
        console.log("1. Donate (within 60s):");
        console.log(`   CAMPAIGN_ADDRESS=${campaignAddress} npx hardhat run scripts/donate.ts --network localhost`);
        console.log("\n2. Wait 60 seconds for deadline to pass...");
        console.log("\n3. Refund:");
        console.log(`   CAMPAIGN_ADDRESS=${campaignAddress} npx hardhat run scripts/refund.ts --network localhost`);
        console.log("\n═══════════════════════════════════════════════════════════");
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
