"""Pydantic models for message schema validation."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class MessageType(str, Enum):
    """Message type enumeration."""
    EVENT = "event"
    ROLLBACK = "rollback"
    RECONCILIATION = "reconciliation"


class EventType(str, Enum):
    """Event type enumeration."""
    CAMPAIGN_CREATED = "CampaignCreated"
    DONATION_RECEIVED = "DonationReceived"
    WITHDRAWN = "Withdrawn"
    REFUNDED = "Refunded"


class BaseMessage(BaseModel):
    """Base message model with common fields."""
    published_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class EventMessage(BaseMessage):
    """Event message schema for blockchain events.
    
    Attributes:
        message_type: Always "event" for event messages
        event_type: Type of blockchain event
        chain_id: Blockchain chain ID
        block_number: Block number where event occurred
        block_hash: Hash of the block
        tx_hash: Transaction hash
        log_index: Log index within the transaction
        address: Contract address that emitted the event
        timestamp: Block timestamp (Unix epoch)
        event_data: Decoded event parameters
    """
    message_type: Literal["event"] = "event"
    event_type: Literal["CampaignCreated", "DonationReceived", "Withdrawn", "Refunded"]
    chain_id: int
    block_number: int
    block_hash: str
    tx_hash: str
    log_index: int
    address: str
    timestamp: int
    event_data: Dict[str, Any]

    @field_validator("address", "tx_hash", "block_hash")
    @classmethod
    def lowercase_hex(cls, v: str) -> str:
        """Ensure hex strings are lowercase."""
        return v.lower() if v else v

    def to_routing_key(self) -> str:
        """Get the routing key for this event."""
        event_routing_map = {
            "CampaignCreated": "event.campaign_created",
            "DonationReceived": "event.donation_received",
            "Withdrawn": "event.withdrawn",
            "Refunded": "event.refunded",
        }
        return event_routing_map.get(self.event_type, "event.unknown")


class RollbackMessage(BaseMessage):
    """Rollback message schema for reorg handling.
    
    Attributes:
        message_type: Always "rollback" for rollback messages
        chain_id: Blockchain chain ID
        from_block: Starting block of rollback range
        to_block: Ending block of rollback range
        reason: Reason for rollback (e.g., "reorg_detected")
    """
    message_type: Literal["rollback"] = "rollback"
    chain_id: int
    from_block: int
    to_block: int
    reason: str = "reorg_detected"


class ReconciliationMessage(BaseMessage):
    """Reconciliation message schema for periodic maintenance.
    
    Attributes:
        message_type: Always "reconciliation" for reconciliation messages
        chain_id: Blockchain chain ID
        reconciliation_type: Type of reconciliation to perform
    """
    message_type: Literal["reconciliation"] = "reconciliation"
    chain_id: int
    reconciliation_type: str = "mark_expired_campaigns"


def parse_message(data: Dict[str, Any]) -> BaseMessage:
    """Parse a message dictionary into the appropriate message type.
    
    Args:
        data: Message data dictionary
        
    Returns:
        Parsed message object
        
    Raises:
        ValueError: If message type is unknown
    """
    message_type = data.get("message_type")
    
    if message_type == "event":
        return EventMessage(**data)
    elif message_type == "rollback":
        return RollbackMessage(**data)
    elif message_type == "reconciliation":
        return ReconciliationMessage(**data)
    else:
        raise ValueError(f"Unknown message type: {message_type}")
