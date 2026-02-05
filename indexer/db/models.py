"""SQLAlchemy ORM models for existing database schema.

NOTE: These models map to EXISTING tables. The indexer does NOT create tables.
All tables must be created by backend migrations before running the 
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Chain(Base):
    """Chain model (maps to existing 'chains' table)."""

    __tablename__ = "chains"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    chain_id = Column(BigInteger, nullable=False, unique=True)
    rpc_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SyncState(Base):
    """Sync state model (maps to existing 'sync_state' table)."""

    __tablename__ = "sync_state"

    chain_id = Column(BigInteger, ForeignKey("chains.chain_id"), primary_key=True)
    last_block = Column(BigInteger, nullable=False, default=0)
    last_block_hash = Column(String(66), nullable=True)  # 0x + 64 hex chars
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    chain = relationship("Chain", backref="sync_states")


class Campaign(Base):
    """Campaign model (maps to existing 'campaigns' table)."""

    __tablename__ = "campaigns"

    address = Column(String(42), primary_key=True)  # Ethereum address (0x + 40 hex)
    factory_address = Column(String(42), nullable=False)
    creator_address = Column(String(42), nullable=False)
    goal_wei = Column(BigInteger, nullable=False)
    deadline_ts = Column(BigInteger, nullable=False)  # Unix timestamp
    cid = Column(String(255), nullable=True)  # IPFS CID
    status = Column(String(50), nullable=False, default="ACTIVE")  # ACTIVE, SUCCESS, FAILED, WITHDRAWN
    total_raised_wei = Column(BigInteger, nullable=False, default=0)
    withdrawn = Column(Boolean, nullable=False, default=False)
    withdrawn_amount_wei = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    contributions = relationship("Contribution", back_populates="campaign", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="campaign")


class Contribution(Base):
    """Contribution model (maps to existing 'contributions' table)."""

    __tablename__ = "contributions"
    __table_args__ = (
        UniqueConstraint("campaign_address", "donor_address", name="uq_contributions_campaign_donor"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_address = Column(String(42), ForeignKey("campaigns.address"), nullable=False)
    donor_address = Column(String(42), nullable=False)
    contributed_wei = Column(BigInteger, nullable=False, default=0)
    refunded_wei = Column(BigInteger, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    campaign = relationship("Campaign", back_populates="contributions")


class Event(Base):
    """Event model (maps to existing 'events' table)."""

    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("chain_id", "tx_hash", "log_index", name="uq_events_chain_tx_log"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    chain_id = Column(BigInteger, ForeignKey("chains.chain_id"), nullable=False)
    tx_hash = Column(String(66), nullable=False)  # 0x + 64 hex chars
    log_index = Column(Integer, nullable=False)
    block_number = Column(BigInteger, nullable=False)
    block_hash = Column(String(66), nullable=False)  # 0x + 64 hex chars
    address = Column(String(42), ForeignKey("campaigns.address"), nullable=True)  # Campaign or Factory address
    event_name = Column(String(100), nullable=False)  # CampaignCreated, DonationReceived, etc.
    event_data = Column(Text, nullable=True)  # JSON string of decoded event data
    removed = Column(Boolean, nullable=False, default=False)  # True if event was removed in reorg
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    chain = relationship("Chain", backref="events")
    campaign = relationship("Campaign", back_populates="events")

