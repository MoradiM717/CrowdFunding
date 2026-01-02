import { expect } from "chai";
import { ethers } from "hardhat";
import { CampaignFactory, Campaign } from "../typechain-types";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";

describe("CampaignFactory", function () {
  let factory: CampaignFactory;
  let owner: SignerWithAddress;
  let creator: SignerWithAddress;
  let donor: SignerWithAddress;

  const GOAL = ethers.parseEther("10");
  const DEADLINE = BigInt(Math.floor(Date.now() / 1000) + 86400); // 24 hours from now
  const CID = "QmTest123";

  beforeEach(async function () {
    [owner, creator, donor] = await ethers.getSigners();

    const CampaignFactoryFactory = await ethers.getContractFactory(
      "CampaignFactory"
    );
    factory = await CampaignFactoryFactory.deploy();
    await factory.waitForDeployment();
  });

  describe("Deployment", function () {
    it("Should deploy factory successfully", async function () {
      expect(await factory.getAddress()).to.be.properAddress;
    });

    it("Should have zero campaigns initially", async function () {
      expect(await factory.getCampaignCount()).to.equal(0);
    });
  });

  describe("createCampaign", function () {
    it("Should create a campaign with valid parameters", async function () {
      const tx = await factory.connect(creator).createCampaign(GOAL, DEADLINE, CID);
      const receipt = await tx.wait();

      expect(await factory.getCampaignCount()).to.equal(1);

      const campaigns = await factory.getCampaigns();
      expect(campaigns.length).to.equal(1);
      expect(campaigns[0]).to.be.properAddress;
    });

    it("Should emit CampaignCreated event with correct fields", async function () {
      await expect(factory.connect(creator).createCampaign(GOAL, DEADLINE, CID))
        .to.emit(factory, "CampaignCreated")
        .withArgs(
          await factory.getAddress(),
          (value: string) => expect(value).to.be.properAddress,
          creator.address,
          GOAL,
          DEADLINE,
          CID
        );
    });

    it("Should store campaign in campaigns array", async function () {
      const tx = await factory.connect(creator).createCampaign(GOAL, DEADLINE, CID);
      const receipt = await tx.wait();

      const campaigns = await factory.getCampaigns();
      const campaignAddress = campaigns[0];

      const campaign = await ethers.getContractAt("Campaign", campaignAddress);
      const summary = await campaign.getSummary();

      expect(summary[0]).to.equal(creator.address);
      expect(summary[1]).to.equal(GOAL);
      expect(summary[2]).to.equal(DEADLINE);
      expect(summary[5]).to.equal(CID);
    });

    it("Should track campaigns by creator", async function () {
      await factory.connect(creator).createCampaign(GOAL, DEADLINE, CID);

      const creatorCampaigns = await factory.getCampaignsByCreator(creator.address);
      expect(creatorCampaigns.length).to.equal(1);
    });

    it("Should reject campaign with zero goal", async function () {
      await expect(
        factory.connect(creator).createCampaign(0, DEADLINE, CID)
      ).to.be.revertedWithCustomError(factory, "InvalidGoal");
    });

    it("Should reject campaign with past deadline", async function () {
      const pastDeadline = BigInt(Math.floor(Date.now() / 1000) - 3600); // 1 hour ago

      await expect(
        factory.connect(creator).createCampaign(GOAL, pastDeadline, CID)
      ).to.be.revertedWithCustomError(factory, "InvalidDeadline");
    });

    it("Should reject campaign with current timestamp as deadline", async function () {
      const currentTime = BigInt(Math.floor(Date.now() / 1000));

      await expect(
        factory.connect(creator).createCampaign(GOAL, currentTime, CID)
      ).to.be.revertedWithCustomError(factory, "InvalidDeadline");
    });

    it("Should reject campaign with empty CID", async function () {
      await expect(
        factory.connect(creator).createCampaign(GOAL, DEADLINE, "")
      ).to.be.revertedWithCustomError(factory, "InvalidCID");
    });

    it("Should allow multiple campaigns from same creator", async function () {
      await factory.connect(creator).createCampaign(GOAL, DEADLINE, CID);
      await factory.connect(creator).createCampaign(GOAL, DEADLINE, CID);

      expect(await factory.getCampaignCount()).to.equal(2);

      const creatorCampaigns = await factory.getCampaignsByCreator(creator.address);
      expect(creatorCampaigns.length).to.equal(2);
    });

    it("Should allow different creators to create campaigns", async function () {
      const creator2 = donor;

      await factory.connect(creator).createCampaign(GOAL, DEADLINE, CID);
      await factory.connect(creator2).createCampaign(GOAL, DEADLINE, CID);

      expect(await factory.getCampaignCount()).to.equal(2);

      const creator1Campaigns = await factory.getCampaignsByCreator(creator.address);
      const creator2Campaigns = await factory.getCampaignsByCreator(creator2.address);

      expect(creator1Campaigns.length).to.equal(1);
      expect(creator2Campaigns.length).to.equal(1);
    });
  });

  describe("getCampaigns", function () {
    it("Should return empty array when no campaigns", async function () {
      const campaigns = await factory.getCampaigns();
      expect(campaigns.length).to.equal(0);
    });

    it("Should return all created campaigns", async function () {
      await factory.connect(creator).createCampaign(GOAL, DEADLINE, CID);
      await factory.connect(creator).createCampaign(GOAL, DEADLINE, CID);

      const campaigns = await factory.getCampaigns();
      expect(campaigns.length).to.equal(2);
      expect(campaigns[0]).to.be.properAddress;
      expect(campaigns[1]).to.be.properAddress;
      expect(campaigns[0]).to.not.equal(campaigns[1]);
    });
  });

  describe("getCampaignsByCreator", function () {
    it("Should return empty array for creator with no campaigns", async function () {
      const campaigns = await factory.getCampaignsByCreator(creator.address);
      expect(campaigns.length).to.equal(0);
    });

    it("Should return only campaigns by specified creator", async function () {
      const creator2 = donor;

      await factory.connect(creator).createCampaign(GOAL, DEADLINE, CID);
      await factory.connect(creator2).createCampaign(GOAL, DEADLINE, CID);
      await factory.connect(creator).createCampaign(GOAL, DEADLINE, CID);

      const creator1Campaigns = await factory.getCampaignsByCreator(creator.address);
      const creator2Campaigns = await factory.getCampaignsByCreator(creator2.address);

      expect(creator1Campaigns.length).to.equal(2);
      expect(creator2Campaigns.length).to.equal(1);
    });
  });

  describe("getCampaignCount", function () {
    it("Should return correct count", async function () {
      expect(await factory.getCampaignCount()).to.equal(0);

      await factory.connect(creator).createCampaign(GOAL, DEADLINE, CID);
      expect(await factory.getCampaignCount()).to.equal(1);

      await factory.connect(creator).createCampaign(GOAL, DEADLINE, CID);
      expect(await factory.getCampaignCount()).to.equal(2);
    });
  });
});

