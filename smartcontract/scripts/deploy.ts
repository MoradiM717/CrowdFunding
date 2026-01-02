import { ethers } from "hardhat";

async function main() {
  console.log("Deploying CampaignFactory...");

  // Get signers
  const [deployer, creator, donor] = await ethers.getSigners();
  console.log("Deploying with account:", deployer.address);
  console.log("Account balance:", ethers.formatEther(await ethers.provider.getBalance(deployer.address)), "ETH");

  // Deploy Factory
  const CampaignFactory = await ethers.getContractFactory("CampaignFactory");
  const factory = await CampaignFactory.deploy();
  await factory.waitForDeployment();

  const factoryAddress = await factory.getAddress();
  console.log("CampaignFactory deployed to:", factoryAddress);

  // Create a sample campaign
  console.log("\nCreating sample campaign...");
  const goal = ethers.parseEther("10"); // 10 ETH goal
  const deadline = BigInt(Math.floor(Date.now() / 1000) + 86400 * 7); // 7 days from now
  const cid = "QmSampleCampaign123";

  const tx = await factory.connect(creator).createCampaign(goal, deadline, cid);
  const receipt = await tx.wait();

  // Get the created campaign address from event
  const campaignCreatedEvent = receipt?.logs.find(
    (log: any) => {
      try {
        const parsed = factory.interface.parseLog(log);
        return parsed?.name === "CampaignCreated";
      } catch {
        return false;
      }
    }
  );

  if (campaignCreatedEvent) {
    const parsed = factory.interface.parseLog(campaignCreatedEvent);
    const campaignAddress = parsed?.args[1];
    console.log("Campaign created at:", campaignAddress);

    // Get campaign contract instance
    const Campaign = await ethers.getContractFactory("Campaign");
    const campaign = Campaign.attach(campaignAddress);

    // Display campaign summary
    const summary = await campaign.getSummary();
    console.log("\nCampaign Summary:");
    console.log("  Creator:", summary[0]);
    console.log("  Goal:", ethers.formatEther(summary[1]), "ETH");
    console.log("  Deadline:", new Date(Number(summary[2]) * 1000).toLocaleString());
    console.log("  Total Raised:", ethers.formatEther(summary[3]), "ETH");
    console.log("  Withdrawn:", summary[4]);
    console.log("  CID:", summary[5]);

    // Demonstrate a donation
    console.log("\nMaking a sample donation...");
    const donationAmount = ethers.parseEther("2");
    const donateTx = await campaign.connect(donor).donate({ value: donationAmount });
    await donateTx.wait();
    console.log("Donated:", ethers.formatEther(donationAmount), "ETH");

    // Display updated summary
    const updatedSummary = await campaign.getSummary();
    console.log("  Updated Total Raised:", ethers.formatEther(updatedSummary[3]), "ETH");
    console.log("  Is Successful:", await campaign.isSuccessful());
    console.log("  Is Active:", await campaign.isActive());
  }

  console.log("\nDeployment and demonstration complete!");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });

