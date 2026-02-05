"""Reorg handler - detects and handles blockchain reorganizations."""

from typing import List

from config import Config
from db.models import Campaign, Contribution, Event, SyncState
from db.session import get_session
from eth.client import EthereumClient
from eth.decoder import decode_campaign_event, decode_factory_event
from log import get_logger
from services.state_updater import apply_event_state_update

logger = get_logger(__name__)


class ReorgHandler:
    """Handles blockchain reorganizations."""

    def __init__(self, config: Config, eth_client: EthereumClient):
        """Initialize reorg handler.

        Args:
            config: Configuration object
            eth_client: Ethereum client instance
        """
        self.config = config
        self.eth_client = eth_client
        self.rollback_blocks = config.reorg_rollback_blocks

    def check_reorg(self, block_number: int) -> bool:
        """Check if a reorg occurred at the given block.

        Args:
            block_number: Block number to check

        Returns:
            True if reorg detected, False otherwise
        """
        with get_session() as session:
            sync_state = (
                session.query(SyncState)
                .filter(SyncState.chain_id == self.config.chain_id)
                .first()
            )

            if not sync_state or sync_state.last_block < block_number:
                # No previous state or block is new, no reorg
                return False

            if sync_state.last_block == block_number:
                # Check block hash
                stored_hash = sync_state.last_block_hash
                if stored_hash:
                    current_hash = self.eth_client.get_block_hash(block_number)
                    if stored_hash.lower() != current_hash.lower():
                        logger.warning(
                            f"Reorg detected at block {block_number}: "
                            f"stored={stored_hash}, current={current_hash}"
                        )
                        return True

        return False

    def handle_reorg(self, from_block: int, to_block: int) -> None:
        """Handle reorg by rolling back and rebuilding state.

        Args:
            from_block: Starting block of rollback range
            to_block: Ending block of rollback range
        """
        logger.warning(f"Handling reorg: rolling back blocks {from_block} to {to_block}")

        with get_session() as session:
            # Mark affected events as removed
            affected_events = (
                session.query(Event)
                .filter(
                    Event.chain_id == self.config.chain_id,
                    Event.block_number >= from_block,
                    Event.block_number <= to_block,
                    Event.removed == False,
                )
                .all()
            )

            for event in affected_events:
                event.removed = True
                logger.debug(f"Marked event as removed: {event.tx_hash}:{event.log_index}")

            # Update sync state
            sync_state = (
                session.query(SyncState)
                .filter(SyncState.chain_id == self.config.chain_id)
                .first()
            )
            if sync_state:
                sync_state.last_block = from_block - 1
                if from_block > 0:
                    sync_state.last_block_hash = self.eth_client.get_block_hash(from_block - 1)
                else:
                    sync_state.last_block_hash = None

            session.commit()

        logger.info(f"Rolled back {len(affected_events)} events from blocks {from_block}-{to_block}")

        # Rebuild state by replaying events
        self._rebuild_state(from_block, to_block)

    def _rebuild_state(self, from_block: int, to_block: int) -> None:
        """Rebuild state by replaying events in the range.

        Args:
            from_block: Starting block
            to_block: Ending block
        """
        logger.info(f"Rebuilding state for blocks {from_block} to {to_block}")

        # Get all non-removed events in range, ordered by block and log index
        with get_session() as session:
            events = (
                session.query(Event)
                .filter(
                    Event.chain_id == self.config.chain_id,
                    Event.block_number >= from_block,
                    Event.block_number <= to_block,
                    Event.removed == False,
                )
                .order_by(Event.block_number, Event.log_index)
                .all()
            )

        if not events:
            logger.info("No events to replay")
            return

        logger.info(f"Replaying {len(events)} events")

        # Rebuild campaign and contribution state
        # First, reset affected campaigns to initial state
        with get_session() as session:
            # Get affected campaign addresses
            affected_campaigns = {e.address.lower() for e in events if e.address}

            # Reset campaign state for affected campaigns
            for campaign_address in affected_campaigns:
                campaign = (
                    session.query(Campaign)
                    .filter(Campaign.address == campaign_address)
                    .first()
                )
                if campaign:
                    # Reset to initial state (will be rebuilt by replaying events)
                    campaign.total_raised_wei = 0
                    campaign.withdrawn = False
                    campaign.withdrawn_amount_wei = None
                    if campaign.status not in ["WITHDRAWN"]:
                        campaign.status = "ACTIVE"

            # Reset contributions for affected campaigns
            contributions = (
                session.query(Contribution)
                .filter(Contribution.campaign_address.in_(affected_campaigns))
                .all()
            )
            for contribution in contributions:
                contribution.contributed_wei = 0
                contribution.refunded_wei = 0

            session.commit()

        # Replay events in order
        for event in events:
            try:
                # Parse event data
                import json
                event_data = json.loads(event.event_data)

                # Apply state update
                with get_session() as session:
                    apply_event_state_update(
                        session=session,
                        chain_id=self.config.chain_id,
                        event_name=event.event_name,
                        event_data=event_data,
                        block_number=event.block_number,
                        block_hash=event.block_hash,
                        tx_hash=event.tx_hash,
                        log_index=event.log_index,
                    )

            except Exception as e:
                logger.error(f"Error replaying event {event.tx_hash}:{event.log_index}: {e}")

        logger.info("State rebuild complete")

