import hre from "hardhat";
import { ethers } from "ethers";

/**
 * Get campaign information
 * Usage: CAMPAIGN_ADDRESS=0x... npx hardhat run scripts/campaign-info.ts --network localhost
 */
async function main() {
    const campaignAddress = process.env.CAMPAIGN_ADDRESS;
    if (!campaignAddress) {
        console.error("❌ Error: CAMPAIGN_ADDRESS environment variable is required");
        console.log("\nUsage: CAMPAIGN_ADDRESS=0x... npx hardhat run scripts/campaign-info.ts --network localhost");
        process.exit(1);
    }

    // Get the provider
    const provider = new ethers.JsonRpcProvider("http://127.0.0.1:8545");

    // Get Campaign contract
    const CampaignArtifact = await hre.artifacts.readArtifact("Campaign");
    const campaign = new ethers.Contract(campaignAddress, CampaignArtifact.abi, provider);

    // Get all info
    const summary = await campaign.getSummary();
    const isActive = await campaign.isActive();
    const isSuccessful = await campaign.isSuccessful();
    const isFailed = await campaign.isFailed();
    const contractBalance = await provider.getBalance(campaignAddress);

    console.log("═══════════════════════════════════════════════════════════");
    console.log("                     CAMPAIGN INFO");
    console.log("═══════════════════════════════════════════════════════════");
    console.log("\n📍 Address:", campaignAddress);
    console.log("👤 Creator:", summary._creator);
    console.log("📝 CID:", summary._cid);

    console.log("\n💰 FINANCIALS:");
    console.log("  Goal:", ethers.formatEther(summary._goal), "ETH");
    console.log("  Total Raised:", ethers.formatEther(summary._totalRaised), "ETH");
    console.log("  Contract Balance:", ethers.formatEther(contractBalance), "ETH");
    console.log("  Progress:", ((Number(summary._totalRaised) / Number(summary._goal)) * 100).toFixed(1) + "%");

    console.log("\n⏰ TIMELINE:");
    console.log("  Deadline:", new Date(Number(summary._deadline) * 1000).toLocaleString());
    const now = Date.now();
    const deadline = Number(summary._deadline) * 1000;
    if (now < deadline) {
        const remaining = deadline - now;
        const days = Math.floor(remaining / (1000 * 60 * 60 * 24));
        const hours = Math.floor((remaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        console.log("  Time Remaining:", days, "days,", hours, "hours");
    } else {
        console.log("  Status: DEADLINE PASSED");
    }

    console.log("\n📊 STATUS:");
    console.log("  Active (accepting donations):", isActive ? "✅ YES" : "❌ NO");
    console.log("  Goal Met:", isSuccessful ? "✅ YES" : "❌ NO");
    console.log("  Failed:", isFailed ? "✅ YES" : "❌ NO");
    console.log("  Withdrawn:", summary._withdrawn ? "✅ YES" : "❌ NO");

    // Determine overall status
    let status = "";
    if (summary._withdrawn) {
        status = "🏆 WITHDRAWN (Success!)";
    } else if (isFailed) {
        status = "💔 FAILED (Refunds available)";
    } else if (isSuccessful) {
        status = "🎉 SUCCESSFUL (Awaiting withdrawal)";
    } else if (isActive) {
        status = "🔥 ACTIVE (Accepting donations)";
    } else {
        status = "⏳ PENDING";
    }
    console.log("\n🏷️  OVERALL STATUS:", status);

    // Check contributions for known accounts
    console.log("\n👥 CONTRIBUTIONS (Hardhat test accounts):");
    const accounts = [
        { name: "Account #0 (Deployer)", key: "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80" },
        { name: "Account #1 (Creator)", key: "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d" },
        { name: "Account #2 (Donor)", key: "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a" },
        { name: "Account #3", key: "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6" },
    ];

    for (const acc of accounts) {
        const wallet = new ethers.Wallet(acc.key);
        const contribution = await campaign.contributions(wallet.address);
        if (contribution > 0n) {
            const refunded = await campaign.refunded(wallet.address);
            console.log(`  ${acc.name}:`);
            console.log(`    Address: ${wallet.address}`);
            console.log(`    Contributed: ${ethers.formatEther(contribution)} ETH`);
            console.log(`    Refunded: ${refunded ? "YES" : "NO"}`);
        }
    }

    console.log("\n═══════════════════════════════════════════════════════════");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
