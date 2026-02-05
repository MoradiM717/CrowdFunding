import hre from "hardhat";
import { ethers } from "ethers";

/**
 * Refund contribution from a failed campaign
 * Usage: CAMPAIGN_ADDRESS=0x... npx hardhat run scripts/refund.ts --network localhost
 * 
 * Note: Campaign must be past deadline AND goal not met
 */
async function main() {
    const campaignAddress = process.env.CAMPAIGN_ADDRESS;
    if (!campaignAddress) {
        console.error("❌ Error: CAMPAIGN_ADDRESS environment variable is required");
        console.log("\nUsage: CAMPAIGN_ADDRESS=0x... npx hardhat run scripts/refund.ts --network localhost");
        process.exit(1);
    }

    // Get the provider
    const provider = new ethers.JsonRpcProvider("http://127.0.0.1:8545");

    // Donor account (Account #2 - same as donate script)
    const donorPrivateKey = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a";
    const donor = new ethers.Wallet(donorPrivateKey, provider);

    console.log("Refunding from campaign:", campaignAddress);
    console.log("Donor:", donor.address);

    // Get Campaign contract
    const CampaignArtifact = await hre.artifacts.readArtifact("Campaign");
    const campaign = new ethers.Contract(campaignAddress, CampaignArtifact.abi, donor);

    // Check campaign status
    const summary = await campaign.getSummary();
    const isFailed = await campaign.isFailed();
    const contribution = await campaign.contributions(donor.address);
    const alreadyRefunded = await campaign.refunded(donor.address);

    console.log("\n📊 Campaign status:");
    console.log("  Goal:", ethers.formatEther(summary._goal), "ETH");
    console.log("  Total Raised:", ethers.formatEther(summary._totalRaised), "ETH");
    console.log("  Deadline:", new Date(Number(summary._deadline) * 1000).toLocaleString());
    console.log("  Deadline Passed:", Date.now() > Number(summary._deadline) * 1000 ? "YES" : "NO");
    console.log("  Campaign Failed:", isFailed ? "✅ YES" : "❌ NO");
    console.log("\n👤 Your status:");
    console.log("  Your contribution:", ethers.formatEther(contribution), "ETH");
    console.log("  Already refunded:", alreadyRefunded ? "YES" : "NO");

    if (contribution === 0n) {
        console.error("\n❌ Error: You have no contribution to refund.");
        process.exit(1);
    }

    if (alreadyRefunded) {
        console.error("\n❌ Error: You have already been refunded.");
        process.exit(1);
    }

    if (!isFailed) {
        // On Hardhat, block.timestamp doesn't advance automatically
        // We need to mine a block to update the timestamp
        const currentTime = Math.floor(Date.now() / 1000);
        const deadlineTime = Number(summary._deadline);

        if (currentTime > deadlineTime) {
            console.log("\n⏰ Deadline passed in real time but blockchain timestamp is stale.");
            console.log("   Mining a block to advance blockchain time...");

            // Advance time and mine a block
            await provider.send("evm_setNextBlockTimestamp", [currentTime]);
            await provider.send("evm_mine", []);

            // Check again
            const isFailedNow = await campaign.isFailed();
            if (!isFailedNow) {
                console.error("\n❌ Error: Campaign still not failed after time advance.");
                console.log("Campaign must be past deadline AND goal not met.");
                process.exit(1);
            }
            console.log("   ✅ Blockchain time updated. Campaign is now marked as failed.");
        } else {
            console.error("\n❌ Error: Campaign has not failed. Cannot refund.");
            console.log("Campaign must be past deadline AND goal not met.");
            process.exit(1);
        }
    }

    // Get balance before
    const balanceBefore = await provider.getBalance(donor.address);
    console.log("\n💰 Your balance before:", ethers.formatEther(balanceBefore), "ETH");

    // Refund
    const tx = await campaign.refund();
    console.log("\n📤 Transaction sent:", tx.hash);

    const receipt = await tx.wait();
    console.log("✅ Transaction confirmed in block:", receipt.blockNumber);

    // Check for Refunded event
    const iface = new ethers.Interface(CampaignArtifact.abi);
    const refundedEvent = receipt.logs.find((log: any) => {
        try {
            const parsed = iface.parseLog(log);
            return parsed?.name === "Refunded";
        } catch {
            return false;
        }
    });

    if (refundedEvent) {
        const parsed = iface.parseLog(refundedEvent);
        console.log("\n🎉 Refunded event emitted!");
        console.log("  Campaign:", parsed?.args[0]);
        console.log("  Donor:", parsed?.args[1]);
        console.log("  Amount:", ethers.formatEther(parsed?.args[2]), "ETH");
    }

    // Get balance after
    const balanceAfter = await provider.getBalance(donor.address);
    console.log("\n💰 Your balance after:", ethers.formatEther(balanceAfter), "ETH");
    console.log("   Received (minus gas):", ethers.formatEther(balanceAfter - balanceBefore), "ETH");
    console.log("\n💡 The indexer should pick up the Refunded event automatically.");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
