"""Factory indexer for producer - fetches CampaignCreated events and publishes to RabbitMQ."""

from typing import List

from web3.types import LogReceipt

from config import Config
from eth.client import EthereumClient
from eth.decoder import decode_factory_event
from eth.topics import get_campaign_created_topic
from log import get_logger
from producer.publisher import EventPublisher

logger = get_logger(__name__)


class ProducerFactoryIndexer:
    """Indexer for CampaignFactory contract events - publishes to RabbitMQ."""

    def __init__(
        self,
        config: Config,
        eth_client: EthereumClient,
        publisher: EventPublisher,
    ):
        """Initialize factory 

        Args:
            config: Configuration object
            eth_client: Ethereum client instance
            publisher: Event publisher for RabbitMQ
        """
        self.config = config
        self.eth_client = eth_client
        self.publisher = publisher
        self.factory_address = config.factory_address.lower()

    def index_block_range(self, from_block: int, to_block: int) -> int:
        """Fetch CampaignCreated events and publish to RabbitMQ.

        Args:
            from_block: Starting block number
            to_block: Ending block number (inclusive)

        Returns:
            Number of events published
        """
        logger.info(f"Fetching Factory events from block {from_block} to {to_block}")
        logger.debug(f"Factory address: {self.factory_address}")

        # Get logs for CampaignCreated events
        topic = get_campaign_created_topic()
        logger.debug(f"Looking for CampaignCreated topic: {topic}")
        
        logs = self.eth_client.get_logs(
            address=self.factory_address,
            from_block=from_block,
            to_block=to_block,
            topics=[topic],
        )

        if not logs:
            logger.debug(f"No Factory events found in blocks {from_block}-{to_block}")
            return 0

        logger.info(f"Found {len(logs)} Factory events in blocks {from_block}-{to_block}")

        # Process and publish events
        events_published = 0
        for log in logs:
            try:
                # Decode event
                decoded = decode_factory_event(log)
                if not decoded:
                    logger.warning(
                        f"Failed to decode Factory event: tx={log['transactionHash'].hex()}"
                    )
                    continue

                logger.debug(f"Decoded event: {decoded['event_name']}, args={decoded['args']}")

                # Get block info for timestamp
                block = self.eth_client.get_block(log["blockNumber"])
                block_hash = block["hash"].hex() if hasattr(block["hash"], "hex") else block["hash"]
                timestamp = block.get("timestamp", 0)

                # Publish to RabbitMQ
                success = self.publisher.publish_event(
                    event_type=decoded["event_name"],
                    chain_id=self.config.chain_id,
                    block_number=decoded["block_number"],
                    block_hash=block_hash,
                    tx_hash=decoded["tx_hash"],
                    log_index=decoded["log_index"],
                    address=decoded["address"],
                    timestamp=timestamp,
                    event_data=decoded["args"],
                )

                if success:
                    events_published += 1
                    logger.info(
                        f"Published {decoded['event_name']}: "
                        f"campaign={decoded['args'].get('campaign', 'N/A')}"
                    )

            except Exception as e:
                logger.error(f"Error processing Factory event: {e}", exc_info=True)

        logger.info(f"Published {events_published} Factory events from blocks {from_block}-{to_block}")
        return events_published
