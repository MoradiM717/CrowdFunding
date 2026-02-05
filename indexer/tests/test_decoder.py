"""Tests for event decoder."""

import pytest
from web3 import Web3
from web3.types import LogReceipt

from eth.decoder import decode_campaign_event, decode_factory_event


@pytest.fixture
def sample_factory_log() -> LogReceipt:
    """Sample CampaignCreated log."""
    # This is a mock log structure - in real tests, you'd use actual log data
    return {
        "address": "0x5FbDB2315678afecb367f032d93F642f64180aa3",
        "topics": [
            Web3.keccak(text="CampaignCreated(address,address,address,uint256,uint256,string)").hex(),
            "0x0000000000000000000000005fbdb2315678afecb367f032d93f642f64180aa3",  # factory
            "0x000000000000000000000000e7f1725e7734ce288f8367e1bb143e90bb3f0512",  # campaign
            "0x00000000000000000000000070997970c51812dc3a010c7d01b50e0d17dc79c8",  # creator
        ],
        "data": "0x0000000000000000000000000000000000000000000000008ac7230489e8000000000000000000000000000000000000000000000000000000000065a5b0c70000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000e516d53616d706c6543696420313233000000000000000000000000000000000000",
        "blockNumber": 1,
        "transactionHash": Web3.to_bytes(hexstr="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"),
        "logIndex": 0,
        "blockHash": Web3.to_bytes(hexstr="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab"),
    }


def test_decode_factory_event(sample_factory_log):
    """Test decoding Factory event."""
    decoded = decode_factory_event(sample_factory_log)
    
    assert decoded is not None
    assert decoded["event_name"] == "CampaignCreated"
    assert "args" in decoded
    assert decoded["block_number"] == 1
    assert decoded["tx_hash"] == "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"


def test_decode_invalid_event():
    """Test decoding invalid event returns None."""
    invalid_log: LogReceipt = {
        "address": "0x5FbDB2315678afecb367f032d93F642f64180aa3",
        "topics": [Web3.keccak(text="InvalidEvent()").hex()],
        "data": "0x",
        "blockNumber": 1,
        "transactionHash": Web3.to_bytes(hexstr="0x1234"),
        "logIndex": 0,
        "blockHash": Web3.to_bytes(hexstr="0xabcd"),
    }
    
    decoded = decode_factory_event(invalid_log)
    assert decoded is None

