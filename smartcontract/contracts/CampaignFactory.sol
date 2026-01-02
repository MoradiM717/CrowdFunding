// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./Campaign.sol";

/**
 * @title CampaignFactory
 * @notice Factory contract for creating and managing crowdfunding campaigns
 * @dev Deploys new Campaign contracts and tracks them
 */
contract CampaignFactory {
    // Custom errors
    error InvalidGoal();
    error InvalidDeadline();
    error InvalidCID();

    // State variables
    Campaign[] public campaigns;
    mapping(address => Campaign[]) public campaignsByCreator;

    // Events
    event CampaignCreated(
        address indexed factory,
        address indexed campaign,
        address indexed creator,
        uint256 goal,
        uint256 deadline,
        string cid
    );

    /**
     * @notice Creates a new campaign
     * @param goal The fundraising target in wei
     * @param deadline The unix timestamp when the campaign ends
     * @param cid The IPFS content identifier for campaign metadata
     * @return The address of the newly created campaign
     */
    function createCampaign(
        uint256 goal,
        uint256 deadline,
        string memory cid
    ) external returns (Campaign) {
        // Validation
        if (goal == 0) revert InvalidGoal();
        if (deadline <= block.timestamp) revert InvalidDeadline();
        if (bytes(cid).length == 0) revert InvalidCID();

        // Deploy new campaign
        Campaign newCampaign = new Campaign(
            msg.sender,
            goal,
            deadline,
            cid
        );

        // Store campaign
        campaigns.push(newCampaign);
        campaignsByCreator[msg.sender].push(newCampaign);

        // Emit event
        emit CampaignCreated(
            address(this),
            address(newCampaign),
            msg.sender,
            goal,
            deadline,
            cid
        );

        return newCampaign;
    }

    /**
     * @notice Returns all created campaigns
     * @return Array of campaign addresses
     */
    function getCampaigns() external view returns (Campaign[] memory) {
        return campaigns;
    }

    /**
     * @notice Returns campaigns created by a specific creator
     * @param creator The address of the creator
     * @return Array of campaign addresses created by the creator
     */
    function getCampaignsByCreator(
        address creator
    ) external view returns (Campaign[] memory) {
        return campaignsByCreator[creator];
    }

    /**
     * @notice Returns the total number of campaigns created
     * @return The number of campaigns
     */
    function getCampaignCount() external view returns (uint256) {
        return campaigns.length;
    }
}

