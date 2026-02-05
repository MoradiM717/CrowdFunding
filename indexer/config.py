"""Configuration management for """

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


@dataclass
class Config:
    """Indexer configuration."""

    # Required
    factory_address: str
    db_url: str

    # Blockchain settings
    rpc_url: str = "http://127.0.0.1:8545"
    confirmations: int = 1
    block_batch_size: int = 2000
    poll_interval_seconds: int = 15
    reorg_rollback_blocks: int = 50
    log_level: str = "INFO"
    chain_id: int = 31337  # Hardhat default

    # RabbitMQ settings
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_vhost: str = "/"
    rabbitmq_exchange: str = "blockchain_events"
    rabbitmq_prefetch_count: int = 10

    # Consumer settings
    consumer_workers: int = 4
    max_retries: int = 3

    # Reconciliation settings
    reconciliation_interval_seconds: int = 300

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        factory_address = os.getenv("FACTORY_ADDRESS")
        if not factory_address:
            raise ValueError("FACTORY_ADDRESS environment variable is required")

        db_url = os.getenv("DB_URL")
        if not db_url:
            raise ValueError("DB_URL environment variable is required")

        return cls(
            factory_address=factory_address,
            db_url=db_url,
            # Blockchain settings
            rpc_url=os.getenv("RPC_URL", "http://127.0.0.1:8545"),
            confirmations=int(os.getenv("CONFIRMATIONS", "1")),
            block_batch_size=int(os.getenv("BLOCK_BATCH_SIZE", "2000")),
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "2")),
            reorg_rollback_blocks=int(os.getenv("REORG_ROLLBACK_BLOCKS", "50")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            chain_id=int(os.getenv("CHAIN_ID", "31337")),
            # RabbitMQ settings
            rabbitmq_host=os.getenv("RABBITMQ_HOST", "localhost"),
            rabbitmq_port=int(os.getenv("RABBITMQ_PORT", "5672")),
            rabbitmq_user=os.getenv("RABBITMQ_USER", "guest"),
            rabbitmq_password=os.getenv("RABBITMQ_PASSWORD", "guest"),
            rabbitmq_vhost=os.getenv("RABBITMQ_VHOST", "/"),
            rabbitmq_exchange=os.getenv("RABBITMQ_EXCHANGE", "blockchain_events"),
            rabbitmq_prefetch_count=int(os.getenv("RABBITMQ_PREFETCH_COUNT", "10")),
            # Consumer settings
            consumer_workers=int(os.getenv("CONSUMER_WORKERS", "4")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            # Reconciliation settings
            reconciliation_interval_seconds=int(os.getenv("RECONCILIATION_INTERVAL_SECONDS", "300")),
        )

    def validate(self) -> None:
        """Validate configuration values."""
        if not self.factory_address:
            raise ValueError("factory_address is required")
        if not self.db_url:
            raise ValueError("db_url is required")
        if self.confirmations < 0:
            raise ValueError("confirmations must be >= 0")
        if self.block_batch_size <= 0:
            raise ValueError("block_batch_size must be > 0")
        if self.poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be > 0")
        if self.reorg_rollback_blocks <= 0:
            raise ValueError("reorg_rollback_blocks must be > 0")
        if self.rabbitmq_port <= 0:
            raise ValueError("rabbitmq_port must be > 0")
        if self.rabbitmq_prefetch_count <= 0:
            raise ValueError("rabbitmq_prefetch_count must be > 0")
        if self.consumer_workers <= 0:
            raise ValueError("consumer_workers must be > 0")
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")

    def get_rabbitmq_connection_params(self) -> dict:
        """Get RabbitMQ connection parameters as a dictionary."""
        return {
            "host": self.rabbitmq_host,
            "port": self.rabbitmq_port,
            "user": self.rabbitmq_user,
            "password": self.rabbitmq_password,
            "vhost": self.rabbitmq_vhost,
        }

