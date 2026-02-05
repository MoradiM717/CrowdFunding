"""Event handler for consumer - dispatches messages to appropriate handlers."""

import json
from typing import Any, Dict, Optional

from sqlalchemy.exc import IntegrityError, OperationalError

from config import Config
from db.session import get_session
from log import get_logger
from messaging.schema import EventMessage, RollbackMessage, ReconciliationMessage, parse_message
from consumer.state_updater import ConsumerStateUpdater
from consumer.rollback_handler import RollbackHandler
from consumer.reconciliation_handler import ReconciliationHandler

logger = get_logger(__name__)


class TransientError(Exception):
    """Raised for transient errors that should be retried."""
    pass


class EventHandler:
    """Handles incoming messages from RabbitMQ."""

    def __init__(self, config: Config):
        """Initialize event handler.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.max_retries = config.max_retries
        self.state_updater = ConsumerStateUpdater(config.chain_id)
        self.rollback_handler = RollbackHandler(config.chain_id)
        self.reconciliation_handler = ReconciliationHandler(config.chain_id)
        
        # Stats
        self._events_processed = 0
        self._events_failed = 0

    def handle_message(
        self,
        body: bytes,
        properties: Any,
    ) -> bool:
        """Handle a message from RabbitMQ.

        Args:
            body: Message body (JSON bytes)
            properties: Message properties

        Returns:
            True if message was processed successfully, False otherwise

        Raises:
            TransientError: If a transient error occurred (should requeue)
            IntegrityError: If event already exists (should acknowledge)
        """
        try:
            # Parse message
            data = json.loads(body)
            message_type = data.get("message_type")

            logger.debug(f"Processing message: type={message_type}")

            if message_type == "event":
                return self._handle_event_message(data)
            elif message_type == "rollback":
                return self._handle_rollback_message(data)
            elif message_type == "reconciliation":
                return self._handle_reconciliation_message(data)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                return False

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message JSON: {e}")
            return False
        except IntegrityError:
            # Event already exists - this is expected for idempotency
            logger.debug("Event already exists (duplicate)")
            raise
        except OperationalError as e:
            # Database temporarily unavailable
            logger.warning(f"Database error (transient): {e}")
            raise TransientError(str(e))
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            self._events_failed += 1
            return False

    def _handle_event_message(self, data: Dict[str, Any]) -> bool:
        """Handle an event message.

        Args:
            data: Parsed message data

        Returns:
            True if processed successfully
        """
        event_type = data.get("event_type")
        chain_id = data.get("chain_id")
        block_number = data.get("block_number")
        block_hash = data.get("block_hash", "")
        tx_hash = data.get("tx_hash")
        log_index = data.get("log_index")
        address = data.get("address", "")
        event_data = data.get("event_data", {})

        # For CampaignCreated events, the address should be the campaign address
        # (not the Factory address that emitted the event)
        # because the events.address FK references campaigns.address
        if event_type == "CampaignCreated":
            campaign_address = event_data.get("campaign", "")
            if campaign_address:
                address = str(campaign_address).lower()
                logger.debug(f"CampaignCreated: using campaign address {address} instead of factory")

        logger.debug(
            f"Processing event: {event_type} at block {block_number}, "
            f"tx={tx_hash}, log_index={log_index}"
        )

        with get_session() as session:
            # For CampaignCreated, we must create the campaign BEFORE inserting
            # the event, because events.address has a FK to campaigns.address
            if event_type == "CampaignCreated":
                self.state_updater.apply_campaign_created(session, event_data)
                session.flush()  # Ensure campaign exists before event insert

            # Insert event into events table (idempotent)
            event_inserted = self.state_updater.insert_event(
                session=session,
                tx_hash=tx_hash,
                log_index=log_index,
                block_number=block_number,
                block_hash=block_hash,
                address=address,
                event_name=event_type,
                event_data=event_data,
            )

            if not event_inserted:
                # Event already exists, skip state update
                logger.debug(f"Event already exists, skipping: {tx_hash}:{log_index}")
                return True

            # Apply state update (skip CampaignCreated since we already did it above)
            if event_type != "CampaignCreated":
                self.state_updater.apply_event(
                    session=session,
                    event_type=event_type,
                    event_data=event_data,
                )

            # Commit transaction
            session.commit()

        self._events_processed += 1
        logger.info(f"Processed {event_type} event: tx={tx_hash}, log_index={log_index}")
        return True

    def _handle_rollback_message(self, data: Dict[str, Any]) -> bool:
        """Handle a rollback message.

        Args:
            data: Parsed message data

        Returns:
            True if processed successfully
        """
        chain_id = data.get("chain_id")
        from_block = data.get("from_block")
        to_block = data.get("to_block")
        reason = data.get("reason", "unknown")

        logger.info(f"Processing rollback: blocks {from_block}-{to_block}, reason={reason}")

        with get_session() as session:
            self.rollback_handler.handle_rollback(
                session=session,
                from_block=from_block,
                to_block=to_block,
                reason=reason,
            )
            session.commit()

        logger.info(f"Rollback complete: blocks {from_block}-{to_block}")
        return True

    def _handle_reconciliation_message(self, data: Dict[str, Any]) -> bool:
        """Handle a reconciliation message.

        Args:
            data: Parsed message data

        Returns:
            True if processed successfully
        """
        chain_id = data.get("chain_id")
        reconciliation_type = data.get("reconciliation_type", "mark_expired_campaigns")

        logger.info(f"Processing reconciliation: {reconciliation_type}")

        with get_session() as session:
            self.reconciliation_handler.handle_reconciliation(
                session=session,
                reconciliation_type=reconciliation_type,
            )
            session.commit()

        logger.info(f"Reconciliation complete: {reconciliation_type}")
        return True

    @property
    def events_processed(self) -> int:
        """Get number of events processed."""
        return self._events_processed

    @property
    def events_failed(self) -> int:
        """Get number of events failed."""
        return self._events_failed


def get_retry_count(properties: Any) -> int:
    """Get the retry count from message headers.

    Args:
        properties: Message properties

    Returns:
        Retry count (0 if not set)
    """
    if properties and properties.headers:
        return properties.headers.get("x-retry-count", 0)
    return 0


def increment_retry_count(properties: Any) -> Dict[str, Any]:
    """Increment retry count in message headers.

    Args:
        properties: Message properties

    Returns:
        Updated headers dictionary
    """
    headers = {}
    if properties and properties.headers:
        headers = dict(properties.headers)
    
    headers["x-retry-count"] = headers.get("x-retry-count", 0) + 1
    return headers
