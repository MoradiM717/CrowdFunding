"""Tests for state update logic."""

import pytest

from config import Config
from db.models import Campaign, Contribution
from db.session import get_session, init_db
from services.state_updater import (
    apply_campaign_created,
    apply_donation_received,
    apply_refunded,
    apply_withdrawn,
)


@pytest.fixture
def test_config():
    """Test configuration."""
    import os
    db_url = os.getenv("TEST_DB_URL", "postgresql://crowdfunding:crowdfunding_pass@localhost:5437/crowdfunding_app")
    
    config = Config(
        factory_address="0x5FbDB2315678afecb367f032d93F642f64180aa3",
        db_url=db_url,
        chain_id=31337,
    )
    return config


def test_campaign_created_state_update(test_config):
    """Test CampaignCreated creates campaign with correct state."""
    init_db(test_config)
    
    event_data = {
        "event_name": "CampaignCreated",
        "args": {
            "factory": "0x5FbDB2315678afecb367f032d93F642f64180aa3",
            "campaign": "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512",
            "creator": "0x70997970c51812dc3a010c7d01b50e0d17dc79c8",
            "goal": 10000000000000000000,  # 10 ETH
            "deadline": 1735689600,  # Future timestamp
            "cid": "QmTest123",
        },
    }
    
    with get_session() as session:
        apply_campaign_created(
            session=session,
            chain_id=31337,
            event_data=event_data,
            block_number=1,
            block_hash="0xabcd",
            tx_hash="0x1234",
            log_index=0,
        )
        
        campaign = session.query(Campaign).filter(
            Campaign.address == "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512"
        ).first()
        
        assert campaign is not None
        assert campaign.status == "ACTIVE"
        assert campaign.total_raised_wei == 0
        assert campaign.withdrawn is False
        assert campaign.goal_wei == 10000000000000000000


def test_donation_received_state_update(test_config):
    """Test DonationReceived updates contribution and campaign totals."""
    init_db(test_config)
    
    # First create a campaign
    with get_session() as session:
        campaign = Campaign(
            address="0xe7f1725e7734ce288f8367e1bb143e90bb3f0512",
            factory_address="0x5FbDB2315678afecb367f032d93F642f64180aa3",
            creator_address="0x70997970c51812dc3a010c7d01b50e0d17dc79c8",
            goal_wei=10000000000000000000,  # 10 ETH
            deadline_ts=1735689600,
            cid="QmTest123",
            status="ACTIVE",
            total_raised_wei=0,
            withdrawn=False,
        )
        session.add(campaign)
        session.commit()
    
    # Apply donation
    event_data = {
        "event_name": "DonationReceived",
        "args": {
            "campaign": "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512",
            "donor": "0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc",
            "amount": 2000000000000000000,  # 2 ETH
            "newTotalRaised": 2000000000000000000,
            "timestamp": 1735603200,
        },
    }
    
    with get_session() as session:
        apply_donation_received(
            session=session,
            chain_id=31337,
            event_data=event_data,
            block_number=2,
            block_hash="0xefgh",
            tx_hash="0x5678",
            log_index=0,
        )
        
        # Check contribution
        contribution = session.query(Contribution).filter(
            Contribution.campaign_address == "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512",
            Contribution.donor_address == "0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc",
        ).first()
        
        assert contribution is not None
        assert contribution.contributed_wei == 2000000000000000000
        
        # Check campaign
        campaign = session.query(Campaign).filter(
            Campaign.address == "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512"
        ).first()
        
        assert campaign.total_raised_wei == 2000000000000000000
        assert campaign.status == "ACTIVE"  # Goal not met yet


def test_donation_received_goal_met(test_config):
    """Test DonationReceived updates status to SUCCESS when goal met."""
    init_db(test_config)
    
    # Create campaign with goal
    with get_session() as session:
        campaign = Campaign(
            address="0xe7f1725e7734ce288f8367e1bb143e90bb3f0512",
            factory_address="0x5FbDB2315678afecb367f032d93F642f64180aa3",
            creator_address="0x70997970c51812dc3a010c7d01b50e0d17dc79c8",
            goal_wei=10000000000000000000,  # 10 ETH
            deadline_ts=1735689600,
            cid="QmTest123",
            status="ACTIVE",
            total_raised_wei=8000000000000000000,  # 8 ETH already raised
            withdrawn=False,
        )
        session.add(campaign)
        session.commit()
    
    # Apply donation that meets goal
    event_data = {
        "event_name": "DonationReceived",
        "args": {
            "campaign": "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512",
            "donor": "0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc",
            "amount": 2000000000000000000,  # 2 ETH
            "newTotalRaised": 10000000000000000000,  # 10 ETH total (goal met)
            "timestamp": 1735603200,
        },
    }
    
    with get_session() as session:
        apply_donation_received(
            session=session,
            chain_id=31337,
            event_data=event_data,
            block_number=2,
            block_hash="0xefgh",
            tx_hash="0x5678",
            log_index=0,
        )
        
        campaign = session.query(Campaign).filter(
            Campaign.address == "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512"
        ).first()
        
        assert campaign.status == "SUCCESS"
        assert campaign.total_raised_wei == 10000000000000000000


def test_withdrawn_state_update(test_config):
    """Test Withdrawn updates campaign withdrawal status."""
    init_db(test_config)
    
    # Create campaign
    with get_session() as session:
        campaign = Campaign(
            address="0xe7f1725e7734ce288f8367e1bb143e90bb3f0512",
            factory_address="0x5FbDB2315678afecb367f032d93F642f64180aa3",
            creator_address="0x70997970c51812dc3a010c7d01b50e0d17dc79c8",
            goal_wei=10000000000000000000,
            deadline_ts=1735689600,
            cid="QmTest123",
            status="SUCCESS",
            total_raised_wei=10000000000000000000,
            withdrawn=False,
        )
        session.add(campaign)
        session.commit()
    
    # Apply withdrawal
    event_data = {
        "event_name": "Withdrawn",
        "args": {
            "campaign": "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512",
            "creator": "0x70997970c51812dc3a010c7d01b50e0d17dc79c8",
            "amount": 10000000000000000000,
            "timestamp": 1735603200,
        },
    }
    
    with get_session() as session:
        apply_withdrawn(
            session=session,
            chain_id=31337,
            event_data=event_data,
            block_number=3,
            block_hash="0xijkl",
            tx_hash="0x9abc",
            log_index=0,
        )
        
        campaign = session.query(Campaign).filter(
            Campaign.address == "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512"
        ).first()
        
        assert campaign.withdrawn is True
        assert campaign.withdrawn_amount_wei == 10000000000000000000
        assert campaign.status == "WITHDRAWN"


def test_refunded_state_update(test_config):
    """Test Refunded updates contribution refund amount."""
    init_db(test_config)
    
    # Create campaign and contribution
    with get_session() as session:
        campaign = Campaign(
            address="0xe7f1725e7734ce288f8367e1bb143e90bb3f0512",
            factory_address="0x5FbDB2315678afecb367f032d93F642f64180aa3",
            creator_address="0x70997970c51812dc3a010c7d01b50e0d17dc79c8",
            goal_wei=10000000000000000000,
            deadline_ts=1735689600,
            cid="QmTest123",
            status="ACTIVE",
            total_raised_wei=5000000000000000000,
            withdrawn=False,
        )
        session.add(campaign)
        
        contribution = Contribution(
            campaign_address="0xe7f1725e7734ce288f8367e1bb143e90bb3f0512",
            donor_address="0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc",
            contributed_wei=5000000000000000000,
            refunded_wei=0,
        )
        session.add(contribution)
        session.commit()
    
    # Apply refund
    event_data = {
        "event_name": "Refunded",
        "args": {
            "campaign": "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512",
            "donor": "0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc",
            "amount": 5000000000000000000,
            "timestamp": 1735603200,
        },
    }
    
    with get_session() as session:
        apply_refunded(
            session=session,
            chain_id=31337,
            event_data=event_data,
            block_number=4,
            block_hash="0xmnop",
            tx_hash="0xdef0",
            log_index=0,
        )
        
        contribution = session.query(Contribution).filter(
            Contribution.campaign_address == "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512",
            Contribution.donor_address == "0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc",
        ).first()
        
        assert contribution.refunded_wei == 5000000000000000000
        assert contribution.contributed_wei == 5000000000000000000  # Lifetime total preserved

