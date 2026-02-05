"""RabbitMQ connection, publish, and consume helpers."""

import json
import time
from typing import Any, Callable, Dict, List, Optional

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError, AMQPChannelError

from log import get_logger
from messaging.routing import (
    EXCHANGE_NAME,
    EXCHANGE_TYPE,
    DLX_EXCHANGE_NAME,
    DLX_QUEUE_NAME,
    QUEUE_BINDINGS,
    ALL_EVENT_QUEUES,
    get_queue_arguments,
)
from messaging.schema import BaseMessage

logger = get_logger(__name__)


class RabbitMQConnection:
    """RabbitMQ connection manager with automatic reconnection."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5672,
        user: str = "guest",
        password: str = "guest",
        vhost: str = "/",
        heartbeat: int = 60,
        max_retries: int = -1,  # -1 for infinite retries
        retry_delay: float = 1.0,
        max_retry_delay: float = 60.0,
    ):
        """Initialize RabbitMQ connection.
        
        Args:
            host: RabbitMQ host
            port: RabbitMQ port
            user: RabbitMQ username
            password: RabbitMQ password
            vhost: Virtual host
            heartbeat: Heartbeat interval in seconds
            max_retries: Maximum connection retries (-1 for infinite)
            retry_delay: Initial retry delay in seconds
            max_retry_delay: Maximum retry delay in seconds
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.vhost = vhost
        self.heartbeat = heartbeat
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_retry_delay = max_retry_delay
        
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[BlockingChannel] = None

    def _get_connection_params(self) -> pika.ConnectionParameters:
        """Get connection parameters."""
        credentials = pika.PlainCredentials(self.user, self.password)
        return pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.vhost,
            credentials=credentials,
            heartbeat=self.heartbeat,
            blocked_connection_timeout=300,
        )

    def connect(self) -> None:
        """Establish connection to RabbitMQ with retry logic."""
        retries = 0
        delay = self.retry_delay
        
        while True:
            try:
                params = self._get_connection_params()
                self._connection = pika.BlockingConnection(params)
                self._channel = self._connection.channel()
                logger.info(f"Connected to RabbitMQ at {self.host}:{self.port}")
                return
            except AMQPConnectionError as e:
                retries += 1
                if self.max_retries != -1 and retries > self.max_retries:
                    logger.error(f"Failed to connect to RabbitMQ after {retries} retries")
                    raise
                
                logger.warning(f"RabbitMQ connection failed (attempt {retries}): {e}")
                logger.info(f"Retrying in {delay:.1f} seconds...")
                time.sleep(delay)
                delay = min(delay * 2, self.max_retry_delay)

    def ensure_connected(self) -> None:
        """Ensure connection is established, reconnect if needed."""
        if self._connection is None or self._connection.is_closed:
            self.connect()
        elif self._channel is None or self._channel.is_closed:
            self._channel = self._connection.channel()

    @property
    def channel(self) -> BlockingChannel:
        """Get the channel, ensuring connection is established."""
        self.ensure_connected()
        return self._channel

    def close(self) -> None:
        """Close the connection."""
        try:
            if self._channel and self._channel.is_open:
                self._channel.close()
            if self._connection and self._connection.is_open:
                self._connection.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.warning(f"Error closing RabbitMQ connection: {e}")

    def setup_exchange_and_queues(self) -> None:
        """Set up exchanges and queues for the 
        
        This creates:
        - Main exchange (topic)
        - Dead letter exchange
        - All event queues with bindings
        - Dead letter queue
        """
        channel = self.channel
        
        # Declare main exchange
        channel.exchange_declare(
            exchange=EXCHANGE_NAME,
            exchange_type=EXCHANGE_TYPE,
            durable=True,
        )
        logger.info(f"Declared exchange: {EXCHANGE_NAME}")
        
        # Declare dead letter exchange
        channel.exchange_declare(
            exchange=DLX_EXCHANGE_NAME,
            exchange_type="direct",
            durable=True,
        )
        logger.info(f"Declared DLX exchange: {DLX_EXCHANGE_NAME}")
        
        # Declare dead letter queue
        channel.queue_declare(
            queue=DLX_QUEUE_NAME,
            durable=True,
        )
        channel.queue_bind(
            queue=DLX_QUEUE_NAME,
            exchange=DLX_EXCHANGE_NAME,
            routing_key="dlq",
        )
        logger.info(f"Declared DLQ: {DLX_QUEUE_NAME}")
        
        # Declare event queues and bind them
        queue_args = get_queue_arguments()
        
        for queue_name, routing_keys in QUEUE_BINDINGS.items():
            channel.queue_declare(
                queue=queue_name,
                durable=True,
                arguments=queue_args,
            )
            logger.info(f"Declared queue: {queue_name}")
            
            for routing_key in routing_keys:
                channel.queue_bind(
                    queue=queue_name,
                    exchange=EXCHANGE_NAME,
                    routing_key=routing_key,
                )
                logger.info(f"Bound {queue_name} to {routing_key}")

    def get_queue_status(self) -> Dict[str, Dict[str, int]]:
        """Get status of all queues.
        
        Returns:
            Dictionary of queue names to their message counts
        """
        channel = self.channel
        status = {}
        
        for queue_name in ALL_EVENT_QUEUES + [DLX_QUEUE_NAME]:
            try:
                result = channel.queue_declare(queue=queue_name, passive=True)
                status[queue_name] = {
                    "message_count": result.method.message_count,
                    "consumer_count": result.method.consumer_count,
                }
            except Exception as e:
                logger.warning(f"Failed to get status for queue {queue_name}: {e}")
                status[queue_name] = {"error": str(e)}
        
        return status

    def purge_queue(self, queue_name: str) -> int:
        """Purge all messages from a queue.
        
        Args:
            queue_name: Name of queue to purge
            
        Returns:
            Number of messages purged
        """
        channel = self.channel
        result = channel.queue_purge(queue_name)
        count = result.method.message_count
        logger.info(f"Purged {count} messages from {queue_name}")
        return count


class RabbitMQPublisher:
    """Publisher for sending messages to RabbitMQ."""

    def __init__(self, connection: RabbitMQConnection):
        """Initialize publisher.
        
        Args:
            connection: RabbitMQ connection instance
        """
        self.connection = connection
        self._confirm_delivery_enabled = False

    def enable_confirm_delivery(self) -> None:
        """Enable publisher confirms for reliable delivery."""
        if not self._confirm_delivery_enabled:
            self.connection.channel.confirm_delivery()
            self._confirm_delivery_enabled = True
            logger.info("Publisher confirms enabled")

    def publish(
        self,
        message: BaseMessage,
        routing_key: str,
        exchange: str = EXCHANGE_NAME,
        retry_on_failure: bool = True,
    ) -> bool:
        """Publish a message to RabbitMQ.
        
        Args:
            message: Message to publish (Pydantic model)
            routing_key: Routing key for the message
            exchange: Exchange to publish to
            retry_on_failure: Whether to retry on publish failure
            
        Returns:
            True if message was published successfully
        """
        body = message.model_dump_json()
        properties = pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,  # Persistent
        )
        
        max_attempts = 3 if retry_on_failure else 1
        
        for attempt in range(max_attempts):
            try:
                self.connection.ensure_connected()
                self.connection.channel.basic_publish(
                    exchange=exchange,
                    routing_key=routing_key,
                    body=body,
                    properties=properties,
                )
                logger.debug(f"Published message to {routing_key}: {message.message_type}")
                return True
            except (AMQPConnectionError, AMQPChannelError) as e:
                logger.warning(f"Publish failed (attempt {attempt + 1}): {e}")
                if attempt < max_attempts - 1:
                    self.connection.connect()
                else:
                    logger.error(f"Failed to publish message after {max_attempts} attempts")
                    return False
        
        return False

    def publish_event(self, message: "EventMessage") -> bool:
        """Publish an event message with automatic routing.
        
        Args:
            message: Event message to publish
            
        Returns:
            True if published successfully
        """
        routing_key = message.to_routing_key()
        return self.publish(message, routing_key)


class RabbitMQConsumer:
    """Consumer for receiving messages from RabbitMQ."""

    def __init__(
        self,
        connection: RabbitMQConnection,
        prefetch_count: int = 10,
    ):
        """Initialize consumer.
        
        Args:
            connection: RabbitMQ connection instance
            prefetch_count: Number of messages to prefetch
        """
        self.connection = connection
        self.prefetch_count = prefetch_count
        self._consuming = False
        self._handlers: Dict[str, Callable] = {}

    def setup(self) -> None:
        """Set up the consumer channel."""
        self.connection.ensure_connected()
        self.connection.channel.basic_qos(prefetch_count=self.prefetch_count)

    def register_handler(self, queue_name: str, handler: Callable) -> None:
        """Register a message handler for a queue.
        
        Args:
            queue_name: Queue to consume from
            handler: Callback function(ch, method, properties, body)
        """
        self._handlers[queue_name] = handler

    def start_consuming(self, queues: Optional[List[str]] = None) -> None:
        """Start consuming messages from registered queues.
        
        Args:
            queues: List of queue names to consume from (defaults to all event queues)
        """
        self.setup()
        queues = queues or ALL_EVENT_QUEUES
        
        for queue_name in queues:
            handler = self._handlers.get(queue_name)
            if handler is None:
                logger.warning(f"No handler registered for queue {queue_name}")
                continue
            
            self.connection.channel.basic_consume(
                queue=queue_name,
                on_message_callback=handler,
                auto_ack=False,
            )
            logger.info(f"Started consuming from {queue_name}")
        
        self._consuming = True
        logger.info("Consumer started, waiting for messages...")
        
        try:
            self.connection.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Consumer stopped by user")
            self.stop_consuming()

    def stop_consuming(self) -> None:
        """Stop consuming messages gracefully."""
        if self._consuming:
            self.connection.channel.stop_consuming()
            self._consuming = False
            logger.info("Consumer stopped")

    def ack(self, delivery_tag: int) -> None:
        """Acknowledge a message.
        
        Args:
            delivery_tag: Delivery tag of the message to acknowledge
        """
        self.connection.channel.basic_ack(delivery_tag=delivery_tag)

    def nack(self, delivery_tag: int, requeue: bool = True) -> None:
        """Negative acknowledge a message.
        
        Args:
            delivery_tag: Delivery tag of the message
            requeue: Whether to requeue the message
        """
        self.connection.channel.basic_nack(delivery_tag=delivery_tag, requeue=requeue)

    def reject(self, delivery_tag: int, requeue: bool = False) -> None:
        """Reject a message.
        
        Args:
            delivery_tag: Delivery tag of the message
            requeue: Whether to requeue the message
        """
        self.connection.channel.basic_reject(delivery_tag=delivery_tag, requeue=requeue)
