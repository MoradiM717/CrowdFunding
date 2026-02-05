import hre from "hardhat";
import { ethers } from "ethers";

async function main() {
  console.log("Deploying CampaignFactory...");

  // Get the provider - use localhost for local Hardhat node
  const provider = new ethers.JsonRpcProvider("http://127.0.0.1:8545");

  // Get the first account as deployer (Hardhat node provides test accounts)
  // Account #0 private key from Hardhat node
  const deployerPrivateKey = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
  const creatorPrivateKey = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d";
  const donorPrivateKey = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a";

  const deployer = new ethers.Wallet(deployerPrivateKey, provider);
  const creator = new ethers.Wallet(creatorPrivateKey, provider);
  const donor = new ethers.Wallet(donorPrivateKey, provider);

  console.log("Deploying with account:", deployer.address);
  const balance = await provider.getBalance(deployer.address);
  console.log("Account balance:", ethers.formatEther(balance), "ETH");

  // Get contract factory - we need to use the artifacts
  const CampaignFactoryArtifact = await hre.artifacts.readArtifact("CampaignFactory");
  const CampaignFactory = new ethers.ContractFactory(
    CampaignFactoryArtifact.abi,
    CampaignFactoryArtifact.bytecode,
    deployer
  );

  // Deploy Factory
  const factory = await CampaignFactory.deploy();
  await factory.waitForDeployment();

  const factoryAddress = await factory.getAddress();
  console.log("CampaignFactory deployed to:", factoryAddress);

  // Create a sample campaign
  console.log("\nCreating sample campaign...");
  const goal = ethers.parseEther("5"); // 5 ETH goal (< 9.2 ETH bigint limit)
  const deadline = BigInt(Math.floor(Date.now() / 1000) + 86400 * 7); // 7 days from now
  const cid = "QmSampleCampaign1234";

  const factoryWithCreator = factory.connect(creator);
  const tx = await factoryWithCreator.createCampaign(goal, deadline, cid);
  const receipt = await tx.wait();

  // Get the created campaign address from event
  const iface = new ethers.Interface(CampaignFactoryArtifact.abi);
  const campaignCreatedEvent = receipt?.logs.find(
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
    console.log("Campaign created at:", campaignAddress);

    // Get campaign contract instance
    const CampaignArtifact = await hre.artifacts.readArtifact("Campaign");
    const campaign = new ethers.Contract(
      campaignAddress,
      CampaignArtifact.abi,
      provider
    );

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
    const campaignWithDonor = campaign.connect(donor);
    const donateTx = await campaignWithDonor.donate({ value: donationAmount });
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
