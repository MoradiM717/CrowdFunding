"""Reorg detector for producer - detects blockchain reorganizations."""

from config import Config
from db.models import SyncState
from db.session import get_session
from eth.client import EthereumClient
from log import get_logger
from producer.publisher import EventPublisher

logger = get_logger(__name__)


class ReorgDetector:
    """Detects blockchain reorganizations and publishes rollback messages."""

    def __init__(
        self,
        config: Config,
        eth_client: EthereumClient,
        publisher: EventPublisher,
    ):
        """Initialize reorg detector.

        Args:
            config: Configuration object
            eth_client: Ethereum client instance
            publisher: Event publisher for RabbitMQ
        """
        self.config = config
        self.eth_client = eth_client
        self.publisher = publisher
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
                    try:
                        current_hash = self.eth_client.get_block_hash(block_number)
                        if stored_hash.lower() != current_hash.lower():
                            logger.warning(
                                f"Reorg detected at block {block_number}: "
                                f"stored={stored_hash}, current={current_hash}"
                            )
                            return True
                    except Exception as e:
                        logger.error(f"Error checking block hash: {e}")

        return False

    def handle_reorg(self, from_block: int, to_block: int) -> bool:
        """Handle reorg by publishing a rollback message.

        In the new architecture, the producer only publishes a rollback message.
        The consumer handles the actual state rollback.

        Args:
            from_block: Starting block of rollback range
            to_block: Ending block of rollback range

        Returns:
            True if rollback message was published successfully
        """
        logger.warning(f"Handling reorg: publishing rollback for blocks {from_block} to {to_block}")

        # Publish rollback message
        success = self.publisher.publish_rollback(
            chain_id=self.config.chain_id,
            from_block=from_block,
            to_block=to_block,
            reason="reorg_detected",
        )

        if success:
            # Update sync state to before the reorg
            self._update_sync_state_for_rollback(from_block)

        return success

    def _update_sync_state_for_rollback(self, from_block: int) -> None:
        """Update sync state to before the rollback point.

        Args:
            from_block: Block to rollback to (exclusive - we go to from_block - 1)
        """
        with get_session() as session:
            sync_state = (
                session.query(SyncState)
                .filter(SyncState.chain_id == self.config.chain_id)
                .first()
            )

            if sync_state:
                new_last_block = max(0, from_block - 1)
                sync_state.last_block = new_last_block

                if new_last_block > 0:
                    try:
                        sync_state.last_block_hash = self.eth_client.get_block_hash(new_last_block)
                    except Exception as e:
                        logger.error(f"Error getting block hash for rollback: {e}")
                        sync_state.last_block_hash = None
                else:
                    sync_state.last_block_hash = None

                session.commit()
                logger.info(f"Updated sync state to block {new_last_block}")

    def check_and_handle_reorg(self, block_number: int) -> bool:
        """Check for reorg and handle if detected.

        Args:
            block_number: Block number to start checking from

        Returns:
            True if reorg was detected and handled
        """
        if self.check_reorg(block_number):
            # Calculate rollback range
            to_block = block_number
            from_block = max(0, block_number - self.rollback_blocks)

            return self.handle_reorg(from_block, to_block)

        return False
