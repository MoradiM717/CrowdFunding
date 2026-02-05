"""Factory indexer - indexes CampaignCreated events from Factory contract."""

from typing import List

from web3.types import LogReceipt

from config import Config
from db.session import get_session
from eth.client import EthereumClient
from eth.decoder import decode_factory_event
from eth.topics import get_campaign_created_topic
from log import get_logger
from services.state_updater import apply_event_state_update, insert_event

logger = get_logger(__name__)


class FactoryIndexer:
    """Indexer for CampaignFactory contract events."""

    def __init__(self, config: Config, eth_client: EthereumClient):
        """Initialize factory 

        Args:
            config: Configuration object
            eth_client: Ethereum client instance
        """
        self.config = config
        self.eth_client = eth_client
        self.factory_address = config.factory_address.lower()

    def index_block_range(self, from_block: int, to_block: int) -> int:
        """Index CampaignCreated events in a block range.

        Args:
            from_block: Starting block number
            to_block: Ending block number (inclusive)

        Returns:
            Number of events indexed
        """
        logger.info(f"Indexing Factory events from block {from_block} to {to_block}")
        logger.debug(f"Factory address: {self.factory_address}")

        # Get logs for CampaignCreated events
        topic = get_campaign_created_topic()
        logger.debug(f"Looking for CampaignCreated topic: {topic}")
        logs = self.eth_client.get_logs(
            address=self.factory_address,
            from_block=from_block,
            to_block=to_block,
            topics=[topic],  # First topic must match event signature
        )

        if not logs:
            logger.debug(f"No Factory events found in blocks {from_block}-{to_block}")
            return 0

        logger.info(f"Found {len(logs)} Factory events in blocks {from_block}-{to_block}")

        # Process events in a transaction
        events_indexed = 0
        with get_session() as session:
            for log in logs:
                try:
                    logger.debug(f"Processing log: tx={log['transactionHash'].hex()}, address={log['address']}, topics={[t.hex() if hasattr(t, 'hex') else t for t in log.get('topics', [])]}")
                    
                    # Decode event
                    decoded = decode_factory_event(log)
                    if not decoded:
                        logger.warning(f"Failed to decode Factory event: tx={log['transactionHash'].hex()}, address={log['address']}, topics={[t.hex() if hasattr(t, 'hex') else t for t in log.get('topics', [])]}")
                        continue
                    
                    logger.debug(f"Decoded event: {decoded['event_name']}, args={decoded['args']}")

                    # Get block hash
                    block_hash = self.eth_client.get_block_hash(log["blockNumber"])

                    # Insert event (idempotent)
                    event_inserted = insert_event(
                        session=session,
                        chain_id=self.config.chain_id,
                        tx_hash=decoded["tx_hash"],
                        log_index=decoded["log_index"],
                        block_number=decoded["block_number"],
                        block_hash=block_hash,
                        address=decoded["address"],
                        event_name=decoded["event_name"],
                        event_data=decoded,
                    )

                    if event_inserted:
                        logger.debug(f"Event inserted, applying state update for {decoded['event_name']}")
                        # Apply state update
                        apply_event_state_update(
                            session=session,
                            chain_id=self.config.chain_id,
                            event_name=decoded["event_name"],
                            event_data=decoded,
                            block_number=decoded["block_number"],
                            block_hash=block_hash,
                            tx_hash=decoded["tx_hash"],
                            log_index=decoded["log_index"],
                        )
                        events_indexed += 1
                        logger.info(
                            f"✅ Indexed {decoded['event_name']}: campaign={decoded['args'].get('campaign', 'N/A')}"
                        )
                    else:
                        logger.debug(f"Event already exists (idempotent): tx={decoded['tx_hash']}, log_index={decoded['log_index']}")

                except Exception as e:
                    logger.error(f"Error processing Factory event: {e}", exc_info=True)
                    # Continue with next event

        logger.info(f"Indexed {events_indexed} Factory events from blocks {from_block}-{to_block}")
        return events_indexed

