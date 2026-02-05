import hre from "hardhat";
import { ethers } from "ethers";

/**
 * Withdraw funds from a successful campaign (creator only)
 * Usage: CAMPAIGN_ADDRESS=0x... npx hardhat run scripts/withdraw.ts --network localhost
 */
async function main() {
    const campaignAddress = process.env.CAMPAIGN_ADDRESS;
    if (!campaignAddress) {
        console.error("❌ Error: CAMPAIGN_ADDRESS environment variable is required");
        console.log("\nUsage: CAMPAIGN_ADDRESS=0x... npx hardhat run scripts/withdraw.ts --network localhost");
        process.exit(1);
    }

    // Get the provider
    const provider = new ethers.JsonRpcProvider("http://127.0.0.1:8545");

    // Creator account (Account #1 from Hardhat node - the campaign creator)
    const creatorPrivateKey = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d";
    const creator = new ethers.Wallet(creatorPrivateKey, provider);

    console.log("Withdrawing from campaign:", campaignAddress);
    console.log("Creator:", creator.address);

    // Get Campaign contract
    const CampaignArtifact = await hre.artifacts.readArtifact("Campaign");
    const campaign = new ethers.Contract(campaignAddress, CampaignArtifact.abi, creator);

    // Check if we can withdraw
    const summary = await campaign.getSummary();
    const isSuccessful = await campaign.isSuccessful();

    console.log("\n📊 Campaign status:");
    console.log("  Goal:", ethers.formatEther(summary._goal), "ETH");
    console.log("  Total Raised:", ethers.formatEther(summary._totalRaised), "ETH");
    console.log("  Goal Met:", isSuccessful ? "✅ YES" : "❌ NO");
    console.log("  Already Withdrawn:", summary._withdrawn ? "YES" : "NO");
    console.log("  Campaign Creator:", summary._creator);

    if (summary._creator.toLowerCase() !== creator.address.toLowerCase()) {
        console.error("\n❌ Error: You are not the campaign creator!");
        console.log("  Campaign creator:", summary._creator);
        console.log("  Your address:", creator.address);
        process.exit(1);
    }

    if (!isSuccessful) {
        console.error("\n❌ Error: Campaign has not met its goal. Cannot withdraw.");
        process.exit(1);
    }

    if (summary._withdrawn) {
        console.error("\n❌ Error: Funds have already been withdrawn.");
        process.exit(1);
    }

    // Get balance before
    const balanceBefore = await provider.getBalance(creator.address);
    const contractBalance = await provider.getBalance(campaignAddress);
    console.log("\n💰 Balances:");
    console.log("  Contract balance:", ethers.formatEther(contractBalance), "ETH");
    console.log("  Creator balance before:", ethers.formatEther(balanceBefore), "ETH");

    // Withdraw
    const tx = await campaign.withdraw();
    console.log("\n📤 Transaction sent:", tx.hash);

    const receipt = await tx.wait();
    console.log("✅ Transaction confirmed in block:", receipt.blockNumber);

    // Check for Withdrawn event
    const iface = new ethers.Interface(CampaignArtifact.abi);
    const withdrawnEvent = receipt.logs.find((log: any) => {
        try {
            const parsed = iface.parseLog(log);
            return parsed?.name === "Withdrawn";
        } catch {
            return false;
        }
    });

    if (withdrawnEvent) {
        const parsed = iface.parseLog(withdrawnEvent);
        console.log("\n🎉 Withdrawn event emitted!");
        console.log("  Campaign:", parsed?.args[0]);
        console.log("  Creator:", parsed?.args[1]);
        console.log("  Amount:", ethers.formatEther(parsed?.args[2]), "ETH");
    }

    // Get balance after
    const balanceAfter = await provider.getBalance(creator.address);
    console.log("\n💰 Creator balance after:", ethers.formatEther(balanceAfter), "ETH");
    console.log("   Received (minus gas):", ethers.formatEther(balanceAfter - balanceBefore), "ETH");
    console.log("\n💡 The indexer should pick up the Withdrawn event automatically.");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
