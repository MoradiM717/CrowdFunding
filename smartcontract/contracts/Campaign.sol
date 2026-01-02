// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title Campaign
 * @notice A crowdfunding campaign contract that accepts donations, allows creator withdrawal on success,
 *         and enables donor refunds on failure.
 * @dev Uses Factory-Campaign pattern. Each campaign is an independent contract.
 */
contract Campaign is ReentrancyGuard {
    // Custom errors for gas efficiency
    error InvalidDonation();
    error CampaignClosed();
    error DeadlinePassed();
    error DeadlineNotPassed();
    error GoalNotMet();
    error GoalMet();
    error NotCreator();
    error AlreadyWithdrawn();
    error NoContribution();
    error AlreadyRefunded();

    // Immutable state variables (gas efficient)
    address public immutable creator;
    uint256 public immutable goal;
    uint256 public immutable deadline;
    string public cid;

    // Mutable state variables
    uint256 public totalRaised;
    bool public withdrawn;
    mapping(address => uint256) public contributions;
    mapping(address => bool) public refunded;

    // Events for indexer
    event DonationReceived(
        address indexed campaign,
        address indexed donor,
        uint256 amount,
        uint256 newTotalRaised,
        uint256 timestamp
    );

    event Withdrawn(
        address indexed campaign,
        address indexed creator,
        uint256 amount,
        uint256 timestamp
    );

    event Refunded(
        address indexed campaign,
        address indexed donor,
        uint256 amount,
        uint256 timestamp
    );

    /**
     * @notice Creates a new campaign
     * @param _creator The address of the campaign creator
     * @param _goal The fundraising target in wei
     * @param _deadline The unix timestamp when the campaign ends
     * @param _cid The IPFS content identifier for campaign metadata
     */
    constructor(
        address _creator,
        uint256 _goal,
        uint256 _deadline,
        string memory _cid
    ) {
        creator = _creator;
        goal = _goal;
        deadline = _deadline;
        cid = _cid;
    }

    /**
     * @notice Accepts donations to the campaign
     * @dev Can only accept donations before deadline and when campaign is active
     */
    function donate() external payable nonReentrant {
        // Checks
        if (msg.value == 0) revert InvalidDonation();
        if (block.timestamp >= deadline) revert DeadlinePassed();
        if (withdrawn) revert CampaignClosed();

        // Effects
        contributions[msg.sender] += msg.value;
        totalRaised += msg.value;

        // Interactions (none - just receiving ETH)

        // Emit event
        emit DonationReceived(
            address(this),
            msg.sender,
            msg.value,
            totalRaised,
            block.timestamp
        );
    }

    /**
     * @notice Allows the creator to withdraw funds when goal is met
     * @dev Can only be called by creator, when goal is met, and only once
     */
    function withdraw() external nonReentrant {
        // Checks
        if (msg.sender != creator) revert NotCreator();
        if (totalRaised < goal) revert GoalNotMet();
        if (withdrawn) revert AlreadyWithdrawn();

        // Effects
        withdrawn = true;
        uint256 amount = address(this).balance;

        // Interactions
        (bool success, ) = creator.call{value: amount}("");
        require(success, "Withdrawal failed");

        // Emit event
        emit Withdrawn(address(this), creator, amount, block.timestamp);
    }

    /**
     * @notice Allows donors to refund their contributions when campaign fails
     * @dev Can only refund after deadline, if goal not met, and only once per donor
     */
    function refund() external nonReentrant {
        // Checks
        if (block.timestamp < deadline) revert DeadlineNotPassed();
        if (totalRaised >= goal) revert GoalMet();
        if (contributions[msg.sender] == 0) revert NoContribution();
        if (refunded[msg.sender]) revert AlreadyRefunded();

        // Effects
        uint256 amount = contributions[msg.sender];
        contributions[msg.sender] = 0;
        refunded[msg.sender] = true;

        // Interactions
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Refund failed");

        // Emit event
        emit Refunded(address(this), msg.sender, amount, block.timestamp);
    }

    /**
     * @notice Returns campaign summary information
     * @return _creator The campaign creator address
     * @return _goal The fundraising goal
     * @return _deadline The campaign deadline timestamp
     * @return _totalRaised The total amount raised
     * @return _withdrawn Whether funds have been withdrawn
     * @return _cid The IPFS content identifier
     */
    function getSummary()
        external
        view
        returns (
            address _creator,
            uint256 _goal,
            uint256 _deadline,
            uint256 _totalRaised,
            bool _withdrawn,
            string memory _cid
        )
    {
        return (creator, goal, deadline, totalRaised, withdrawn, cid);
    }

    /**
     * @notice Returns the contribution amount for a given address
     * @param contributor The address to check
     * @return The contribution amount in wei
     */
    function contributionOf(address contributor) external view returns (uint256) {
        return contributions[contributor];
    }

    /**
     * @notice Checks if the campaign is currently active
     * @return True if campaign is accepting donations
     */
    function isActive() external view returns (bool) {
        return block.timestamp < deadline && !withdrawn;
    }

    /**
     * @notice Checks if the campaign has met its goal
     * @return True if totalRaised >= goal
     */
    function isSuccessful() external view returns (bool) {
        return totalRaised >= goal;
    }

    /**
     * @notice Checks if the campaign has failed (deadline passed and goal not met)
     * @return True if deadline passed and goal not met
     */
    function isFailed() external view returns (bool) {
        return block.timestamp >= deadline && totalRaised < goal;
    }
}

