"""Producer main module - blockchain event polling and publishing."""

import signal
import sys
import time
from datetime import datetime, timezone
from typing import Optional

from config import Config
from db.healthcheck import check_tables_exist
from db.models import Chain, SyncState
from db.session import get_session, init_db
from eth.client import EthereumClient
from log import get_logger, setup_logging
from producer.campaign_indexer import ProducerCampaignIndexer
from producer.factory_indexer import ProducerFactoryIndexer
from producer.publisher import EventPublisher
from producer.reorg_detector import ReorgDetector

logger = get_logger(__name__)

# Global flag for graceful shutdown
_shutdown = False


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global _shutdown
    logger.info("Shutdown signal received, stopping producer...")
    _shutdown = True


def ensure_chain_exists(config: Config) -> None:
    """Ensure chain record exists in database.

    Args:
        config: Configuration object
    """
    with get_session() as session:
        chain = session.query(Chain).filter(Chain.chain_id == config.chain_id).first()

        if not chain:
            chain = Chain(
                chain_id=config.chain_id,
                name=f"Hardhat Localhost" if config.chain_id == 31337 else f"Chain {config.chain_id}",
                rpc_url=config.rpc_url,
            )
            session.add(chain)
            logger.info(f"Created chain record: {config.chain_id}")

        # Ensure sync_state exists
        sync_state = (
            session.query(SyncState)
            .filter(SyncState.chain_id == config.chain_id)
            .first()
        )

        if not sync_state:
            sync_state = SyncState(
                chain_id=config.chain_id,
                last_block=0,
                last_block_hash=None,
            )
            session.add(sync_state)
            logger.info(f"Created sync_state for chain: {config.chain_id}")


def get_sync_state(config: Config) -> SyncState:
    """Get current sync state.

    Args:
        config: Configuration object

    Returns:
        SyncState object
    """
    with get_session() as session:
        sync_state = (
            session.query(SyncState)
            .filter(SyncState.chain_id == config.chain_id)
            .first()
        )
        if not sync_state:
            raise RuntimeError(f"Sync state not found for chain {config.chain_id}")
        # Detach from session by accessing attributes
        last_block = sync_state.last_block
        last_block_hash = sync_state.last_block_hash
        
    # Return a simple object with the values
    class SyncStateData:
        def __init__(self, lb, lbh):
            self.last_block = lb
            self.last_block_hash = lbh
    
    return SyncStateData(last_block, last_block_hash)


def update_sync_state(config: Config, block_number: int, block_hash: str) -> None:
    """Update sync state.

    Args:
        config: Configuration object
        block_number: Last processed block number
        block_hash: Last processed block hash
    """
    with get_session() as session:
        sync_state = (
            session.query(SyncState)
            .filter(SyncState.chain_id == config.chain_id)
            .first()
        )
        if sync_state:
            sync_state.last_block = block_number
            sync_state.last_block_hash = block_hash
        session.commit()


def index_block_range(
    config: Config,
    factory_indexer: ProducerFactoryIndexer,
    campaign_indexer: ProducerCampaignIndexer,
    reorg_detector: ReorgDetector,
    from_block: int,
    to_block: int,
) -> int:
    """Index a range of blocks and publish events.

    Args:
        config: Configuration object
        factory_indexer: Factory indexer instance
        campaign_indexer: Campaign indexer instance
        reorg_detector: Reorg detector instance
        from_block: Starting block
        to_block: Ending block

    Returns:
        Total number of events published
    """
    logger.info(f"Processing blocks {from_block} to {to_block}")

    total_events = 0
    batch_size = config.block_batch_size
    current = from_block

    while current <= to_block and not _shutdown:
        batch_end = min(current + batch_size - 1, to_block)

        try:
            # Check for reorg
            if reorg_detector.check_and_handle_reorg(current):
                # Reorg detected and handled, restart from updated sync state
                sync_state = get_sync_state(config)
                current = sync_state.last_block + 1
                continue

            # Fetch and publish Factory events
            factory_events = factory_indexer.index_block_range(current, batch_end)
            total_events += factory_events

            # Fetch and publish Campaign events
            campaign_events = campaign_indexer.index_block_range(current, batch_end)
            total_events += campaign_events

            # Update sync state
            try:
                block = factory_indexer.eth_client.get_block(batch_end)
                block_hash = block["hash"].hex() if hasattr(block["hash"], "hex") else block["hash"]
                update_sync_state(config, batch_end, block_hash)
            except Exception as e:
                logger.warning(f"Could not get block hash for {batch_end}: {e}")
                update_sync_state(config, batch_end, "")

            logger.info(f"Processed blocks {current} to {batch_end}, published {factory_events + campaign_events} events")
            current = batch_end + 1

        except Exception as e:
            logger.error(f"Error processing blocks {current}-{batch_end}: {e}", exc_info=True)
            current = batch_end + 1

    return total_events


def run_producer(config: Config) -> None:
    """Run the producer in polling mode.

    Args:
        config: Configuration object
    """
    logger.info("Starting producer in polling mode")
    logger.info(f"Factory address: {config.factory_address}")
    logger.info(f"RabbitMQ: {config.rabbitmq_host}:{config.rabbitmq_port}")

    # Initialize components
    eth_client = EthereumClient(config)
    publisher = EventPublisher(config)
    publisher.connect()

    factory_indexer = ProducerFactoryIndexer(config, eth_client, publisher)
    campaign_indexer = ProducerCampaignIndexer(config, eth_client, publisher)
    reorg_detector = ReorgDetector(config, eth_client, publisher)

    # Track reconciliation
    last_reconciliation = datetime.now(timezone.utc)

    try:
        # Main polling loop
        while not _shutdown:
            try:
                # Get latest block with confirmations
                latest_block = eth_client.get_latest_block()
                sync_state = get_sync_state(config)
                last_block = sync_state.last_block

                if latest_block > last_block:
                    # Index new blocks
                    logger.info(f"New blocks detected: {last_block + 1} to {latest_block}")
                    index_block_range(
                        config,
                        factory_indexer,
                        campaign_indexer,
                        reorg_detector,
                        last_block + 1,
                        latest_block,
                    )
                else:
                    logger.debug(f"No new blocks (latest={latest_block}, last={last_block})")

                # Periodic reconciliation
                now = datetime.now(timezone.utc)
                if (now - last_reconciliation).total_seconds() >= config.reconciliation_interval_seconds:
                    publisher.publish_reconciliation(config.chain_id)
                    last_reconciliation = now

                # Sleep before next poll
                if not _shutdown:
                    time.sleep(config.poll_interval_seconds)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}", exc_info=True)
                time.sleep(config.poll_interval_seconds)

    finally:
        publisher.close()
        logger.info("Producer stopped")


def backfill(config: Config, from_block: int, to_block: int) -> None:
    """Backfill historical blocks.

    Args:
        config: Configuration object
        from_block: Starting block number
        to_block: Ending block number
    """
    logger.info(f"Backfilling blocks {from_block} to {to_block}")

    # Initialize components
    eth_client = EthereumClient(config)
    publisher = EventPublisher(config)
    publisher.connect()

    factory_indexer = ProducerFactoryIndexer(config, eth_client, publisher)
    campaign_indexer = ProducerCampaignIndexer(config, eth_client, publisher)
    reorg_detector = ReorgDetector(config, eth_client, publisher)

    try:
        # Index the range
        total_events = index_block_range(
            config,
            factory_indexer,
            campaign_indexer,
            reorg_detector,
            from_block,
            to_block,
        )
        logger.info(f"Backfill complete. Total events published: {total_events}")
    finally:
        publisher.close()


def show_status(config: Config) -> None:
    """Show producer status.

    Args:
        config: Configuration object
    """
    try:
        sync_state = get_sync_state(config)
        eth_client = EthereumClient(config)
        latest_block = eth_client.get_latest_block()

        print(f"Chain ID: {config.chain_id}")
        print(f"RPC URL: {config.rpc_url}")
        print(f"Factory Address: {config.factory_address}")
        print(f"RabbitMQ: {config.rabbitmq_host}:{config.rabbitmq_port}")
        print(f"Last Indexed Block: {sync_state.last_block}")
        print(f"Latest Block (with confirmations): {latest_block}")
        print(f"Blocks Behind: {max(0, latest_block - sync_state.last_block)}")
        print(f"Last Block Hash: {sync_state.last_block_hash}")

    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        sys.exit(1)


def main(command: str, from_block: int = None, to_block: int = None) -> None:
    """Main entry point for producer.

    Args:
        command: Command to run (run, backfill, status)
        from_block: Starting block for backfill
        to_block: Ending block for backfill
    """
    # Load config
    try:
        config = Config.from_env()
        config.validate()
    except Exception as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Setup logging
    setup_logging(config)

    # Initialize database
    init_db(config)

    # Check database schema
    try:
        check_tables_exist()
    except RuntimeError as e:
        logger.error(str(e))
        sys.exit(1)

    # Ensure chain exists
    ensure_chain_exists(config)

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Execute command
    try:
        if command == "run":
            run_producer(config)
        elif command == "backfill":
            if from_block is None or to_block is None:
                print("Error: --from-block and --to-block are required for backfill", file=sys.stderr)
                sys.exit(1)
            backfill(config, from_block, to_block)
        elif command == "status":
            show_status(config)
        else:
            print(f"Unknown command: {command}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main("run")
