"""Routing key constants and helpers for RabbitMQ."""

from enum import Enum
from typing import Dict, List, Tuple


# Exchange configuration
EXCHANGE_NAME = "blockchain_events"
EXCHANGE_TYPE = "topic"

# Dead letter exchange
DLX_EXCHANGE_NAME = "blockchain_events.dlx"
DLX_QUEUE_NAME = "dlq.events"


class RoutingKey(str, Enum):
    """Routing key enumeration."""
    # Event routing keys
    CAMPAIGN_CREATED = "event.campaign_created"
    DONATION_RECEIVED = "event.donation_received"
    WITHDRAWN = "event.withdrawn"
    REFUNDED = "event.refunded"
    
    # Control routing keys
    ROLLBACK = "control.rollback"
    RECONCILIATION = "control.reconciliation"


class QueueName(str, Enum):
    """Queue name enumeration."""
    CAMPAIGN_CREATED = "queue.campaign_created"
    DONATION_RECEIVED = "queue.donation_received"
    WITHDRAWAL_REFUND = "queue.withdrawal_refund"
    CONTROL = "queue.control"


# Queue bindings: queue_name -> list of routing keys to bind
QUEUE_BINDINGS: Dict[str, List[str]] = {
    QueueName.CAMPAIGN_CREATED.value: [RoutingKey.CAMPAIGN_CREATED.value],
    QueueName.DONATION_RECEIVED.value: [RoutingKey.DONATION_RECEIVED.value],
    QueueName.WITHDRAWAL_REFUND.value: [
        RoutingKey.WITHDRAWN.value,
        RoutingKey.REFUNDED.value,
    ],
    QueueName.CONTROL.value: [
        RoutingKey.ROLLBACK.value,
        RoutingKey.RECONCILIATION.value,
    ],
}

# All queues that consumers should subscribe to
ALL_EVENT_QUEUES = [
    QueueName.CAMPAIGN_CREATED.value,
    QueueName.DONATION_RECEIVED.value,
    QueueName.WITHDRAWAL_REFUND.value,
    QueueName.CONTROL.value,
]

# Queue properties
QUEUE_MESSAGE_TTL = 604800000  # 7 days in milliseconds
QUEUE_MAX_LENGTH = 100000


def get_routing_key_for_event(event_type: str) -> str:
    """Get the routing key for a given event type.
    
    Args:
        event_type: Event type string (e.g., "CampaignCreated")
        
    Returns:
        Routing key string
    """
    routing_map = {
        "CampaignCreated": RoutingKey.CAMPAIGN_CREATED.value,
        "DonationReceived": RoutingKey.DONATION_RECEIVED.value,
        "Withdrawn": RoutingKey.WITHDRAWN.value,
        "Refunded": RoutingKey.REFUNDED.value,
    }
    return routing_map.get(event_type, "event.unknown")


def get_queue_arguments() -> Dict:
    """Get queue arguments for dead letter handling.
    
    Returns:
        Dictionary of queue arguments
    """
    return {
        "x-message-ttl": QUEUE_MESSAGE_TTL,
        "x-max-length": QUEUE_MAX_LENGTH,
        "x-dead-letter-exchange": DLX_EXCHANGE_NAME,
        "x-dead-letter-routing-key": "dlq",
    }
