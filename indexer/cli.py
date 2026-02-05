"""CLI module for the indexer with producer/consumer/broker subcommands."""

import argparse
import sys

from config import Config
from db.healthcheck import check_tables_exist
from db.session import init_db
from log import get_logger, setup_logging
from messaging.rabbitmq import RabbitMQConnection
from messaging.routing import ALL_EVENT_QUEUES, DLX_QUEUE_NAME

logger = get_logger(__name__)


def broker_setup(config: Config) -> None:
    """Set up RabbitMQ exchanges, queues, and bindings.
    
    Args:
        config: Configuration object
    """
    print(f"Setting up RabbitMQ broker at {config.rabbitmq_host}:{config.rabbitmq_port}")
    
    connection = RabbitMQConnection(
        host=config.rabbitmq_host,
        port=config.rabbitmq_port,
        user=config.rabbitmq_user,
        password=config.rabbitmq_password,
        vhost=config.rabbitmq_vhost,
    )
    
    try:
        connection.connect()
        connection.setup_exchange_and_queues()
        print("Broker setup complete!")
        print(f"  Exchange: {config.rabbitmq_exchange}")
        print(f"  Queues: {', '.join(ALL_EVENT_QUEUES)}")
        print(f"  DLQ: {DLX_QUEUE_NAME}")
    finally:
        connection.close()


def broker_status(config: Config) -> None:
    """Show RabbitMQ broker status.
    
    Args:
        config: Configuration object
    """
    print(f"RabbitMQ: {config.rabbitmq_host}:{config.rabbitmq_port}")
    
    connection = RabbitMQConnection(
        host=config.rabbitmq_host,
        port=config.rabbitmq_port,
        user=config.rabbitmq_user,
        password=config.rabbitmq_password,
        vhost=config.rabbitmq_vhost,
    )
    
    try:
        connection.connect()
        status = connection.get_queue_status()
        
        print(f"\nQueue Status:")
        print("-" * 50)
        
        total_messages = 0
        total_consumers = 0
        
        for queue_name in ALL_EVENT_QUEUES + [DLX_QUEUE_NAME]:
            queue_status = status.get(queue_name, {})
            if "error" in queue_status:
                print(f"  {queue_name}: ERROR - {queue_status['error']}")
            else:
                msg_count = queue_status.get("message_count", 0)
                consumer_count = queue_status.get("consumer_count", 0)
                total_messages += msg_count
                total_consumers += consumer_count
                print(f"  {queue_name}:")
                print(f"    Messages: {msg_count}")
                print(f"    Consumers: {consumer_count}")
        
        print("-" * 50)
        print(f"Total messages: {total_messages}")
        print(f"Total consumers: {total_consumers}")
        
    finally:
        connection.close()


def broker_purge(config: Config, queue_name: str) -> None:
    """Purge all messages from a queue.
    
    Args:
        config: Configuration object
        queue_name: Name of queue to purge
    """
    print(f"Purging queue: {queue_name}")
    
    connection = RabbitMQConnection(
        host=config.rabbitmq_host,
        port=config.rabbitmq_port,
        user=config.rabbitmq_user,
        password=config.rabbitmq_password,
        vhost=config.rabbitmq_vhost,
    )
    
    try:
        connection.connect()
        count = connection.purge_queue(queue_name)
        print(f"Purged {count} messages from {queue_name}")
    finally:
        connection.close()


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser.
    
    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Blockchain indexer with RabbitMQ message broker",
        prog="python -m indexer",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Producer commands
    producer_parser = subparsers.add_parser("producer", help="Producer commands")
    producer_subparsers = producer_parser.add_subparsers(dest="subcommand", help="Producer subcommands")
    
    # producer run
    producer_run = producer_subparsers.add_parser("run", help="Start producer in polling mode")
    
    # producer backfill
    producer_backfill = producer_subparsers.add_parser("backfill", help="Backfill historical blocks")
    producer_backfill.add_argument("--from-block", type=int, required=True, help="Starting block number")
    producer_backfill.add_argument("--to-block", type=int, required=True, help="Ending block number")
    
    # producer status
    producer_status = producer_subparsers.add_parser("status", help="Show producer status")
    
    # Consumer commands
    consumer_parser = subparsers.add_parser("consumer", help="Consumer commands")
    consumer_subparsers = consumer_parser.add_subparsers(dest="subcommand", help="Consumer subcommands")
    
    # consumer run
    consumer_run = consumer_subparsers.add_parser("run", help="Start consumer workers")
    consumer_run.add_argument("--workers", "-w", type=int, help="Number of worker processes")
    
    # consumer status
    consumer_status = consumer_subparsers.add_parser("status", help="Show consumer/queue status")
    
    # Broker commands
    broker_parser = subparsers.add_parser("broker", help="Broker management commands")
    broker_subparsers = broker_parser.add_subparsers(dest="subcommand", help="Broker subcommands")
    
    # broker setup
    broker_setup_parser = broker_subparsers.add_parser("setup", help="Set up exchanges and queues")
    
    # broker status
    broker_status_parser = broker_subparsers.add_parser("status", help="Show queue status")
    
    # broker purge
    broker_purge_parser = broker_subparsers.add_parser("purge", help="Purge a queue")
    broker_purge_parser.add_argument("--queue", "-q", type=str, required=True, help="Queue name to purge")
    
    # Legacy commands for backward compatibility
    subparsers.add_parser("run", help="(Legacy) Start producer - use 'producer run' instead")
    
    backfill_parser = subparsers.add_parser("backfill", help="(Legacy) Backfill - use 'producer backfill' instead")
    backfill_parser.add_argument("--from-block", type=int, required=True, help="Starting block number")
    backfill_parser.add_argument("--to-block", type=int, required=True, help="Ending block number")
    
    subparsers.add_parser("status", help="(Legacy) Status - use 'producer status' instead")
    
    return parser


def main() -> None:
    """Main entry point for CLI."""
    parser = create_parser()
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
    
    try:
        # Handle commands
        if args.command == "producer":
            if not args.subcommand:
                print("Usage: python -m indexer producer {run|backfill|status}")
                sys.exit(1)
            
            from producer.main import main as producer_main
            
            if args.subcommand == "run":
                producer_main("run")
            elif args.subcommand == "backfill":
                producer_main("backfill", args.from_block, args.to_block)
            elif args.subcommand == "status":
                producer_main("status")
                
        elif args.command == "consumer":
            if not args.subcommand:
                print("Usage: python -m indexer consumer {run|status}")
                sys.exit(1)
            
            from consumer.main import main as consumer_main
            
            if args.subcommand == "run":
                workers = getattr(args, "workers", None)
                consumer_main("run", workers)
            elif args.subcommand == "status":
                consumer_main("status")
                
        elif args.command == "broker":
            if not args.subcommand:
                print("Usage: python -m indexer broker {setup|status|purge}")
                sys.exit(1)
            
            if args.subcommand == "setup":
                broker_setup(config)
            elif args.subcommand == "status":
                broker_status(config)
            elif args.subcommand == "purge":
                broker_purge(config, args.queue)
                
        # Legacy commands (backward compatibility)
        elif args.command == "run":
            print("Note: 'run' is deprecated. Use 'producer run' instead.")
            from producer.main import main as producer_main
            producer_main("run")
            
        elif args.command == "backfill":
            print("Note: 'backfill' is deprecated. Use 'producer backfill' instead.")
            from producer.main import main as producer_main
            producer_main("backfill", args.from_block, args.to_block)
            
        elif args.command == "status":
            print("Note: 'status' is deprecated. Use 'producer status' or 'broker status' instead.")
            from producer.main import main as producer_main
            producer_main("status")
            
        else:
            parser.print_help()
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
