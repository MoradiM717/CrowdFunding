"""Publisher module for sending event messages to RabbitMQ."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from config import Config
from log import get_logger
from messaging.rabbitmq import RabbitMQConnection, RabbitMQPublisher
from messaging.routing import RoutingKey, get_routing_key_for_event
from messaging.schema import EventMessage, RollbackMessage, ReconciliationMessage

logger = get_logger(__name__)


class EventPublisher:
    """Publisher for blockchain events to RabbitMQ."""

    def __init__(self, config: Config):
        """Initialize event publisher.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self._connection: Optional[RabbitMQConnection] = None
        self._publisher: Optional[RabbitMQPublisher] = None
        self._events_published = 0

    def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        self._connection = RabbitMQConnection(
            host=self.config.rabbitmq_host,
            port=self.config.rabbitmq_port,
            user=self.config.rabbitmq_user,
            password=self.config.rabbitmq_password,
            vhost=self.config.rabbitmq_vhost,
        )
        self._connection.connect()
        self._publisher = RabbitMQPublisher(self._connection)
        self._publisher.enable_confirm_delivery()
        logger.info("Event publisher connected to RabbitMQ")

    def close(self) -> None:
        """Close the connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            self._publisher = None
        logger.info(f"Event publisher closed. Total events published: {self._events_published}")

    def ensure_connected(self) -> None:
        """Ensure publisher is connected."""
        if self._connection is None or self._publisher is None:
            self.connect()

    def publish_event(
        self,
        event_type: str,
        chain_id: int,
        block_number: int,
        block_hash: str,
        tx_hash: str,
        log_index: int,
        address: str,
        timestamp: int,
        event_data: Dict[str, Any],
    ) -> bool:
        """Publish a blockchain event to RabbitMQ.
        
        Args:
            event_type: Type of event (CampaignCreated, DonationReceived, etc.)
            chain_id: Blockchain chain ID
            block_number: Block number
            block_hash: Block hash
            tx_hash: Transaction hash
            log_index: Log index
            address: Contract address
            timestamp: Block timestamp
            event_data: Decoded event data
            
        Returns:
            True if published successfully
        """
        self.ensure_connected()
        
        message = EventMessage(
            event_type=event_type,
            chain_id=chain_id,
            block_number=block_number,
            block_hash=block_hash,
            tx_hash=tx_hash,
            log_index=log_index,
            address=address,
            timestamp=timestamp,
            event_data=event_data,
            published_at=datetime.now(timezone.utc),
        )
        
        routing_key = get_routing_key_for_event(event_type)
        success = self._publisher.publish(message, routing_key)
        
        if success:
            self._events_published += 1
            logger.debug(f"Published {event_type} event: tx={tx_hash}, log_index={log_index}")
        else:
            logger.error(f"Failed to publish {event_type} event: tx={tx_hash}")
        
        return success

    def publish_rollback(
        self,
        chain_id: int,
        from_block: int,
        to_block: int,
        reason: str = "reorg_detected",
    ) -> bool:
        """Publish a rollback message for reorg handling.
        
        Args:
            chain_id: Blockchain chain ID
            from_block: Starting block of rollback range
            to_block: Ending block of rollback range
            reason: Reason for rollback
            
        Returns:
            True if published successfully
        """
        self.ensure_connected()
        
        message = RollbackMessage(
            chain_id=chain_id,
            from_block=from_block,
            to_block=to_block,
            reason=reason,
            published_at=datetime.now(timezone.utc),
        )
        
        success = self._publisher.publish(message, RoutingKey.ROLLBACK.value)
        
        if success:
            logger.info(f"Published rollback message: blocks {from_block}-{to_block}")
        else:
            logger.error(f"Failed to publish rollback message")
        
        return success

    def publish_reconciliation(
        self,
        chain_id: int,
        reconciliation_type: str = "mark_expired_campaigns",
    ) -> bool:
        """Publish a reconciliation message.
        
        Args:
            chain_id: Blockchain chain ID
            reconciliation_type: Type of reconciliation
            
        Returns:
            True if published successfully
        """
        self.ensure_connected()
        
        message = ReconciliationMessage(
            chain_id=chain_id,
            reconciliation_type=reconciliation_type,
            published_at=datetime.now(timezone.utc),
        )
        
        success = self._publisher.publish(message, RoutingKey.RECONCILIATION.value)
        
        if success:
            logger.info(f"Published reconciliation message: {reconciliation_type}")
        else:
            logger.error(f"Failed to publish reconciliation message")
        
        return success

    @property
    def events_published_count(self) -> int:
        """Get the number of events published."""
        return self._events_published
