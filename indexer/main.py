"""Main indexer service with CLI."""

import argparse
import signal
import sys
import time
from typing import Optional

from config import Config
from db.healthcheck import check_chain_exists, check_tables_exist
from db.models import Chain, SyncState
from db.session import get_session, init_db
from eth.client import EthereumClient
from log import get_logger, setup_logging
from pipeline.campaign_indexer import CampaignIndexer
from pipeline.factory_indexer import FactoryIndexer
from pipeline.reconciler import Reconciler
from pipeline.reorg import ReorgHandler

logger = get_logger(__name__)

# Global flag for graceful shutdown
_shutdown = False


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global _shutdown
    logger.info("Shutdown signal received, stopping ..")
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
                name=f"Chain {config.chain_id}",
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
        return sync_state


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
    factory_indexer: FactoryIndexer,
    campaign_indexer: CampaignIndexer,
    from_block: int,
    to_block: int,
) -> None:
    """Index a range of blocks.

    Args:
        config: Configuration object
        factory_indexer: Factory indexer instance
        campaign_indexer: Campaign indexer instance
        from_block: Starting block
        to_block: Ending block
    """
    logger.info(f"Indexing blocks {from_block} to {to_block}")

    # Process in batches
    batch_size = config.block_batch_size
    current = from_block

    while current <= to_block and not _shutdown:
        batch_end = min(current + batch_size - 1, to_block)

        try:
            # Check for reorg
            reorg_handler = ReorgHandler(config, factory_eth_client)
            if reorg_handler.check_reorg(current):
                rollback_to = max(0, current - config.reorg_rollback_blocks)
                reorg_handler.handle_reorg(rollback_to, current)
                current = rollback_to
                continue

            # Index factory events
            factory_index_block_range(current, batch_end)

            # Index campaign events
            campaign_index_block_range(current, batch_end)

            # Update sync state
            block_hash = factory_eth_client.get_block_hash(batch_end)
            update_sync_state(config, batch_end, block_hash)

            logger.info(f"Indexed blocks {current} to {batch_end}")
            current = batch_end + 1

        except Exception as e:
            logger.error(f"Error indexing blocks {current}-{batch_end}: {e}", exc_info=True)
            # Continue with next batch
            current = batch_end + 1


def run_indexer(config: Config) -> None:
    """Run the indexer in polling mode.

    Args:
        config: Configuration object
    """
    logger.info("Starting indexer in polling mode")
    logger.info(f"Factory address: {config.factory_address}")

    # Initialize components
    eth_client = EthereumClient(config)
    factory_indexer = FactoryIndexer(config, eth_client)
    campaign_indexer = CampaignIndexer(config, eth_client)
    reconciler = Reconciler(config)

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
                    last_block + 1,
                    latest_block,
                )
            else:
                logger.debug(f"No new blocks (latest={latest_block}, last={last_block})")

            # Periodic reconciliation
            if reconciler.should_reconcile():
                reconciler.reconcile()

            # Sleep before next poll
            if not _shutdown:
                time.sleep(config.poll_interval_seconds)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            break
        except Exception as e:
            logger.error(f"Error in polling loop: {e}", exc_info=True)
            time.sleep(config.poll_interval_seconds)

    logger.info("Indexer stopped")


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
    factory_indexer = FactoryIndexer(config, eth_client)
    campaign_indexer = CampaignIndexer(config, eth_client)

    # Index the range
    index_block_range(config, factory_indexer, campaign_indexer, from_block, to_block)

    logger.info("Backfill complete")


def show_status(config: Config) -> None:
    """Show indexer status.

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
        print(f"Last Indexed Block: {sync_state.last_block}")
        print(f"Latest Block (with confirmations): {latest_block}")
        print(f"Blocks Behind: {max(0, latest_block - sync_state.last_block)}")
        print(f"Last Block Hash: {sync_state.last_block_hash}")

        # Count campaigns
        with get_session() as session:
            from db.models import Campaign
            campaign_count = session.query(Campaign).count()
            print(f"Total Campaigns: {campaign_count}")

    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Blockchain indexer for crowdfunding contracts")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command
    run_parser = subparsers.add_parser("run", help="Start polling indexer")

    # Backfill command
    backfill_parser = subparsers.add_parser("backfill", help="Backfill historical blocks")
    backfill_parser.add_argument("--from-block", type=int, required=True, help="Starting block number")
    backfill_parser.add_argument("--to-block", type=int, required=True, help="Ending block number")

    # Status command
    subparsers.add_parser("status", help="Show indexer status")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

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
        if args.command == "run":
            run_indexer(config)
        elif args.command == "backfill":
            backfill(config, args.from_block, args.to_block)
        elif args.command == "status":
            show_status(config)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

