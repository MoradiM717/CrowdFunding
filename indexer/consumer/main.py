"""Consumer main module - message consumption and processing."""

import json
import multiprocessing
import signal
import sys
import time
from typing import Optional

from sqlalchemy.exc import IntegrityError

from config import Config
from db.healthcheck import check_tables_exist
from db.session import init_db
from log import get_logger, setup_logging
from messaging.rabbitmq import RabbitMQConnection, RabbitMQConsumer
from messaging.routing import ALL_EVENT_QUEUES, DLX_QUEUE_NAME
from consumer.event_handler import EventHandler, TransientError, get_retry_count

logger = get_logger(__name__)

# Global flag for graceful shutdown
_shutdown = False


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global _shutdown
    logger.info("Shutdown signal received, stopping consumer...")
    _shutdown = True


class ConsumerWorker:
    """Single consumer worker process."""

    def __init__(self, config: Config, worker_id: int):
        """Initialize consumer worker.
        
        Args:
            config: Configuration object
            worker_id: Worker ID for logging
        """
        self.config = config
        self.worker_id = worker_id
        self.connection: Optional[RabbitMQConnection] = None
        self.consumer: Optional[RabbitMQConsumer] = None
        self.event_handler: Optional[EventHandler] = None
        self._running = False

    def start(self) -> None:
        """Start the consumer worker."""
        logger.info(f"Worker {self.worker_id}: Starting")
        
        # Initialize database
        init_db(self.config)
        
        # Initialize RabbitMQ connection
        self.connection = RabbitMQConnection(
            host=self.config.rabbitmq_host,
            port=self.config.rabbitmq_port,
            user=self.config.rabbitmq_user,
            password=self.config.rabbitmq_password,
            vhost=self.config.rabbitmq_vhost,
        )
        self.connection.connect()
        
        # Initialize consumer
        self.consumer = RabbitMQConsumer(
            self.connection,
            prefetch_count=self.config.rabbitmq_prefetch_count,
        )
        
        # Initialize event handler
        self.event_handler = EventHandler(self.config)
        
        # Register message callback for all queues
        for queue_name in ALL_EVENT_QUEUES:
            self.consumer.register_handler(queue_name, self._on_message)
        
        self._running = True
        logger.info(f"Worker {self.worker_id}: Started, consuming from {len(ALL_EVENT_QUEUES)} queues")
        
        # Start consuming (blocks until stopped)
        try:
            self.consumer.start_consuming()
        except KeyboardInterrupt:
            logger.info(f"Worker {self.worker_id}: Interrupted")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the consumer worker."""
        self._running = False
        
        if self.consumer:
            self.consumer.stop_consuming()
        
        if self.connection:
            self.connection.close()
        
        logger.info(
            f"Worker {self.worker_id}: Stopped. "
            f"Processed: {self.event_handler.events_processed if self.event_handler else 0}, "
            f"Failed: {self.event_handler.events_failed if self.event_handler else 0}"
        )

    def _on_message(self, channel, method, properties, body):
        """Handle incoming message.
        
        Args:
            channel: RabbitMQ channel
            method: Delivery method
            properties: Message properties
            body: Message body
        """
        delivery_tag = method.delivery_tag
        
        try:
            # Process message
            success = self.event_handler.handle_message(body, properties)
            
            if success:
                # Acknowledge message
                channel.basic_ack(delivery_tag=delivery_tag)
            else:
                # Processing failed, check retry count
                retry_count = get_retry_count(properties)
                if retry_count >= self.config.max_retries:
                    # Max retries exceeded, send to DLQ (reject without requeue)
                    logger.warning(
                        f"Worker {self.worker_id}: Max retries exceeded, sending to DLQ"
                    )
                    channel.basic_reject(delivery_tag=delivery_tag, requeue=False)
                else:
                    # Retry by rejecting with requeue
                    channel.basic_nack(delivery_tag=delivery_tag, requeue=True)
                    
        except IntegrityError:
            # Event already exists (duplicate) - acknowledge and skip
            logger.debug(f"Worker {self.worker_id}: Duplicate event, acknowledging")
            channel.basic_ack(delivery_tag=delivery_tag)
            
        except TransientError as e:
            # Transient error - requeue for retry
            logger.warning(f"Worker {self.worker_id}: Transient error, requeuing: {e}")
            channel.basic_nack(delivery_tag=delivery_tag, requeue=True)
            time.sleep(1)  # Brief delay before processing next
            
        except Exception as e:
            # Unexpected error
            logger.error(f"Worker {self.worker_id}: Unexpected error: {e}", exc_info=True)
            retry_count = get_retry_count(properties)
            if retry_count >= self.config.max_retries:
                channel.basic_reject(delivery_tag=delivery_tag, requeue=False)
            else:
                channel.basic_nack(delivery_tag=delivery_tag, requeue=True)


def run_worker(config: Config, worker_id: int) -> None:
    """Run a single consumer worker (for multiprocessing).
    
    Args:
        config: Configuration object
        worker_id: Worker ID
    """
    # Setup logging for this process
    setup_logging(config)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    worker = ConsumerWorker(config, worker_id)
    worker.start()


def run_consumer(config: Config, num_workers: int = None) -> None:
    """Run the consumer with multiple workers.

    Args:
        config: Configuration object
        num_workers: Number of worker processes (default: from config)
    """
    num_workers = num_workers or config.consumer_workers
    logger.info(f"Starting consumer with {num_workers} workers")
    logger.info(f"RabbitMQ: {config.rabbitmq_host}:{config.rabbitmq_port}")

    if num_workers == 1:
        # Single worker - run in main process
        run_worker(config, 0)
    else:
        # Multiple workers - use multiprocessing
        processes = []
        
        for i in range(num_workers):
            p = multiprocessing.Process(
                target=run_worker,
                args=(config, i),
            )
            p.start()
            processes.append(p)
            logger.info(f"Started worker process {i} (pid={p.pid})")
        
        # Wait for all processes
        try:
            for p in processes:
                p.join()
        except KeyboardInterrupt:
            logger.info("Shutting down workers...")
            for p in processes:
                p.terminate()
            for p in processes:
                p.join(timeout=5)

    logger.info("Consumer stopped")


def show_status(config: Config) -> None:
    """Show consumer status.

    Args:
        config: Configuration object
    """
    try:
        # Connect to RabbitMQ to get queue status
        connection = RabbitMQConnection(
            host=config.rabbitmq_host,
            port=config.rabbitmq_port,
            user=config.rabbitmq_user,
            password=config.rabbitmq_password,
            vhost=config.rabbitmq_vhost,
        )
        connection.connect()
        
        status = connection.get_queue_status()
        
        print(f"RabbitMQ: {config.rabbitmq_host}:{config.rabbitmq_port}")
        print(f"Exchange: {config.rabbitmq_exchange}")
        print()
        print("Queue Status:")
        print("-" * 60)
        
        for queue_name, queue_status in status.items():
            if "error" in queue_status:
                print(f"  {queue_name}: ERROR - {queue_status['error']}")
            else:
                msg_count = queue_status.get("message_count", 0)
                consumer_count = queue_status.get("consumer_count", 0)
                print(f"  {queue_name}:")
                print(f"    Messages: {msg_count}")
                print(f"    Consumers: {consumer_count}")
        
        connection.close()
        
    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        sys.exit(1)


def main(command: str, workers: int = None) -> None:
    """Main entry point for consumer.

    Args:
        command: Command to run (run, status)
        workers: Number of worker processes
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

    # Check database schema
    if command == "run":
        init_db(config)
        try:
            check_tables_exist()
        except RuntimeError as e:
            logger.error(str(e))
            sys.exit(1)

    # Setup signal handlers for main process
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Execute command
    try:
        if command == "run":
            run_consumer(config, workers)
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
