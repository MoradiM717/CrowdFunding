"""Tests for idempotency behavior."""

import pytest
from sqlalchemy.exc import IntegrityError

from db.models import Event
from db.session import get_session, init_db
from config import Config
from services.state_updater import insert_event


@pytest.fixture
def test_config():
    """Test configuration."""
    # Use test database URL from environment or default
    import os
    db_url = os.getenv("TEST_DB_URL", "postgresql://crowdfunding:crowdfunding_pass@localhost:5437/crowdfunding_app")
    
    config = Config(
        factory_address="0x5FbDB2315678afecb367f032d93F642f64180aa3",
        db_url=db_url,
        chain_id=31337,
    )
    return config


def test_duplicate_event_insertion(test_config):
    """Test that duplicate event insertion is idempotent."""
    init_db(test_config)
    
    chain_id = 31337
    tx_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    log_index = 0
    
    with get_session() as session:
        # Insert first event
        inserted1 = insert_event(
            session=session,
            chain_id=chain_id,
            tx_hash=tx_hash,
            log_index=log_index,
            block_number=1,
            block_hash="0xabcd",
            address="0x5FbDB2315678afecb367f032d93F642f64180aa3",
            event_name="CampaignCreated",
            event_data={"test": "data"},
        )
        assert inserted1 is True
        
        # Try to insert duplicate
        inserted2 = insert_event(
            session=session,
            chain_id=chain_id,
            tx_hash=tx_hash,
            log_index=log_index,
            block_number=1,
            block_hash="0xabcd",
            address="0x5FbDB2315678afecb367f032d93F642f64180aa3",
            event_name="CampaignCreated",
            event_data={"test": "data"},
        )
        assert inserted2 is False  # Should return False (already exists)
        
        # Verify only one event exists
        count = session.query(Event).filter(
            Event.chain_id == chain_id,
            Event.tx_hash == tx_hash,
            Event.log_index == log_index,
        ).count()
        assert count == 1


def test_unique_constraint_enforced(test_config):
    """Test that unique constraint is enforced at database level."""
    init_db(test_config)
    
    chain_id = 31337
    tx_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    log_index = 0
    
    with get_session() as session:
        # Insert first event
        event1 = Event(
            chain_id=chain_id,
            tx_hash=tx_hash,
            log_index=log_index,
            block_number=1,
            block_hash="0xabcd",
            address="0x5FbDB2315678afecb367f032d93F642f64180aa3",
            event_name="CampaignCreated",
            event_data='{"test": "data"}',
        )
        session.add(event1)
        session.commit()
        
        # Try to insert duplicate directly (bypassing insert_event)
        event2 = Event(
            chain_id=chain_id,
            tx_hash=tx_hash,
            log_index=log_index,
            block_number=2,  # Different block, but same tx_hash:log_index
            block_hash="0xefgh",
            address="0x5FbDB2315678afecb367f032d93F642f64180aa3",
            event_name="CampaignCreated",
            event_data='{"test": "data2"}',
        )
        session.add(event2)
        
        # Should raise IntegrityError
        with pytest.raises(IntegrityError):
            session.commit()

