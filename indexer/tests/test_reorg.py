"""Tests for reorg handling."""

import pytest

from config import Config
from db.models import Campaign, Event, SyncState
from db.session import get_session, init_db
from pipeline.reorg import ReorgHandler


@pytest.fixture
def test_config():
    """Test configuration."""
    import os
    db_url = os.getenv("TEST_DB_URL", "postgresql://crowdfunding:crowdfunding_pass@localhost:5437/crowdfunding_app")
    
    config = Config(
        factory_address="0x5FbDB2315678afecb367f032d93F642f64180aa3",
        db_url=db_url,
        chain_id=31337,
        reorg_rollback_blocks=50,
    )
    return config


@pytest.fixture
def mock_eth_client():
    """Mock Ethereum client."""
    from unittest.mock import Mock
    client = Mock()
    client.get_block_hash = Mock(return_value="0xnewhash")
    return client


def test_reorg_detection(test_config, mock_eth_client):
    """Test reorg detection via block hash mismatch."""
    init_db(test_config)
    
    # Setup sync state with a block hash
    with get_session() as session:
        sync_state = SyncState(
            chain_id=31337,
            last_block=100,
            last_block_hash="0xoldhash",
        )
        session.add(sync_state)
        session.commit()
    
    # Simulate reorg: stored hash doesn't match current hash
    handler = ReorgHandler(test_config, mock_eth_client)
    
    # Mock get_block_hash to return different hash
    mock_eth_client.get_block_hash.return_value = "0xdifferenthash"
    
    # Check should detect reorg
    reorg_detected = handler.check_reorg(100)
    assert reorg_detected is True


def test_no_reorg_when_hash_matches(test_config, mock_eth_client):
    """Test no reorg detected when block hash matches."""
    init_db(test_config)
    
    # Setup sync state
    with get_session() as session:
        sync_state = SyncState(
            chain_id=31337,
            last_block=100,
            last_block_hash="0xsamehash",
        )
        session.add(sync_state)
        session.commit()
    
    handler = ReorgHandler(test_config, mock_eth_client)
    mock_eth_client.get_block_hash.return_value = "0xsamehash"
    
    reorg_detected = handler.check_reorg(100)
    assert reorg_detected is False


def test_reorg_rollback_marks_events_removed(test_config, mock_eth_client):
    """Test reorg rollback marks affected events as removed."""
    init_db(test_config)
    
    # Create some events in the rollback range
    with get_session() as session:
        for i in range(5):
            event = Event(
                chain_id=31337,
                tx_hash=f"0x{i:064x}",
                log_index=i,
                block_number=50 + i,
                block_hash="0xoldhash",
                address="0xe7f1725e7734ce288f8367e1bb143e90bb3f0512",
                event_name="DonationReceived",
                event_data='{"test": "data"}',
                removed=False,
            )
            session.add(event)
        
        sync_state = SyncState(
            chain_id=31337,
            last_block=100,
            last_block_hash="0xoldhash",
        )
        session.add(sync_state)
        session.commit()
    
    handler = ReorgHandler(test_config, mock_eth_client)
    mock_eth_client.get_block_hash.return_value = "0xnewhash"
    
    # Rollback from block 50 to 100
    handler.handle_reorg(50, 100)
    
    # Check events are marked as removed
    with get_session() as session:
        events = session.query(Event).filter(
            Event.chain_id == 31337,
            Event.block_number >= 50,
            Event.block_number <= 100,
        ).all()
        
        assert len(events) == 5
        for event in events:
            assert event.removed is True

