"""Event topic hash computation."""

from web3 import Web3

from eth.abi_loader import get_campaign_abi, get_factory_abi

# Cache topic hashes
_TOPIC_CACHE: dict[str, str] = {}


def _compute_topic(event_signature: str) -> str:
    """Compute keccak256 hash of event signature.

    Args:
        event_signature: Event signature (e.g., "CampaignCreated(address,address,address,uint256,uint256,string)")

    Returns:
        Topic hash (0x-prefixed hex string)
    """
    hash_bytes = Web3.keccak(text=event_signature)
    # Ensure 0x prefix - hash_bytes.hex() may not include it
    hex_str = hash_bytes.hex()
    if not hex_str.startswith('0x'):
        hex_str = '0x' + hex_str
    return hex_str


def get_campaign_created_topic() -> str:
    """Get CampaignCreated event topic hash.

    Returns:
        Topic hash for CampaignCreated event
    """
    if "CampaignCreated" not in _TOPIC_CACHE:
        # CampaignCreated(address indexed factory, address indexed campaign, address indexed creator, uint256 goal, uint256 deadline, string cid)
        signature = "CampaignCreated(address,address,address,uint256,uint256,string)"
        _TOPIC_CACHE["CampaignCreated"] = _compute_topic(signature)
    return _TOPIC_CACHE["CampaignCreated"]


def get_donation_received_topic() -> str:
    """Get DonationReceived event topic hash.

    Returns:
        Topic hash for DonationReceived event
    """
    if "DonationReceived" not in _TOPIC_CACHE:
        # DonationReceived(address indexed campaign, address indexed donor, uint256 amount, uint256 newTotalRaised, uint256 timestamp)
        signature = "DonationReceived(address,address,uint256,uint256,uint256)"
        _TOPIC_CACHE["DonationReceived"] = _compute_topic(signature)
    return _TOPIC_CACHE["DonationReceived"]


def get_withdrawn_topic() -> str:
    """Get Withdrawn event topic hash.

    Returns:
        Topic hash for Withdrawn event
    """
    if "Withdrawn" not in _TOPIC_CACHE:
        # Withdrawn(address indexed campaign, address indexed creator, uint256 amount, uint256 timestamp)
        signature = "Withdrawn(address,address,uint256,uint256)"
        _TOPIC_CACHE["Withdrawn"] = _compute_topic(signature)
    return _TOPIC_CACHE["Withdrawn"]


def get_refunded_topic() -> str:
    """Get Refunded event topic hash.

    Returns:
        Topic hash for Refunded event
    """
    if "Refunded" not in _TOPIC_CACHE:
        # Refunded(address indexed campaign, address indexed donor, uint256 amount, uint256 timestamp)
        signature = "Refunded(address,address,uint256,uint256)"
        _TOPIC_CACHE["Refunded"] = _compute_topic(signature)
    return _TOPIC_CACHE["Refunded"]


def get_all_campaign_topics() -> list[str]:
    """Get all Campaign event topic hashes.

    Returns:
        List of topic hashes for Campaign events
    """
    return [
        get_donation_received_topic(),
        get_withdrawn_topic(),
        get_refunded_topic(),
    ]

