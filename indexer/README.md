# Blockchain Indexer

Pure Python blockchain indexer for crowdfunding smart contracts using a **message broker architecture**. This indexer decouples blockchain event reading from database writing using RabbitMQ for reliable, scalable event processing.

## ⚠️ IMPORTANT: Schema Management

**The indexer does NOT create tables or run migrations.** All database tables must be created by the backend migrations before running the  The indexer only performs CRUD operations on existing schema.

If you see an error like "DB schema missing. Run backend migrations first.", you need to run your backend database migrations before starting the 

## Architecture

The indexer uses a **Producer-Consumer architecture** with RabbitMQ as the message broker:

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  Blockchain │   -->   │   Producer  │   -->   │  RabbitMQ   │
│   (Events)  │         │  (Polling)  │         │  (Queues)   │
└─────────────┘         └─────────────┘         └─────────────┘
                                                       │
                                                       v
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  PostgreSQL │   <--   │  Consumer   │   <--   │  Workers    │
│  (Database) │         │  (Writers)  │         │  (N procs)  │
└─────────────┘         └─────────────┘         └─────────────┘
```

### Producer
- Polls blockchain for new blocks
- Decodes smart contract events
- Publishes events to RabbitMQ queues
- Detects and handles blockchain reorganizations
- Updates sync_state (only DB write by producer)

### Consumer
- Multiple worker processes for parallel processing
- Consumes messages from RabbitMQ queues
- Writes events to database (idempotently)
- Applies state updates to campaigns/contributions
- Handles rollback and reconciliation messages

### Benefits
- **Decoupling**: Blockchain reading and DB writing are independent
- **Scalability**: Scale consumers independently of producers
- **Reliability**: RabbitMQ provides message persistence and delivery guarantees
- **Resilience**: Failed messages go to Dead Letter Queue for inspection

## Features

- **Event Indexing**: Indexes `CampaignCreated`, `DonationReceived`, `Withdrawn`, and `Refunded` events
- **Message Broker**: RabbitMQ-based producer-consumer architecture
- **Idempotency**: Safe to re-run; duplicate events are skipped
- **Reorg Handling**: Detects and handles blockchain reorganizations via rollback messages
- **State Updates**: Automatically updates campaign and contribution state from events
- **Reconciliation**: Periodically marks expired campaigns as FAILED
- **Progress Tracking**: Tracks last indexed block in database
- **Dead Letter Queue**: Failed messages are preserved for debugging

## Prerequisites

- Python 3.9+
- PostgreSQL database with schema already created (via backend migrations)
- RabbitMQ 3.8+ with management plugin
- Hardhat node or Ethereum RPC endpoint
- CampaignFactory contract address

## Installation

1. Install dependencies:
```bash
cd indexer
pip install -r requirements.txt
```

2. Set up environment variables (see Configuration below)

3. Ensure database schema exists (run backend migrations)

4. Start RabbitMQ (see Docker Setup below)

## Configuration

Create a `.env` file or set environment variables (see `.env.example`):

```bash
# Blockchain Settings (required)
FACTORY_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
RPC_URL=http://127.0.0.1:8545
CHAIN_ID=31337

# Database Settings (required)
DB_URL=postgresql://crowd_user:crowd_pass@localhost:5433/crowdfunding

# Indexer Settings (optional, with defaults)
CONFIRMATIONS=1
BLOCK_BATCH_SIZE=2000
POLL_INTERVAL_SECONDS=2
REORG_ROLLBACK_BLOCKS=50
LOG_LEVEL=INFO

# RabbitMQ Settings
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VHOST=/
RABBITMQ_EXCHANGE=blockchain_events
RABBITMQ_PREFETCH_COUNT=10

# Consumer Settings
CONSUMER_WORKERS=4
MAX_RETRIES=3

# Reconciliation Settings
RECONCILIATION_INTERVAL_SECONDS=300
```

### Environment Variables Reference

#### Blockchain
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FACTORY_ADDRESS` | Yes | - | CampaignFactory contract address |
| `RPC_URL` | No | `http://127.0.0.1:8545` | Ethereum RPC endpoint |
| `CHAIN_ID` | No | `31337` | Chain ID (31337 for Hardhat) |

#### Database
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DB_URL` | Yes | - | PostgreSQL connection string |

#### Indexer
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CONFIRMATIONS` | No | `1` | Confirmations before indexing |
| `BLOCK_BATCH_SIZE` | No | `2000` | Blocks per batch |
| `POLL_INTERVAL_SECONDS` | No | `2` | Polling interval |
| `REORG_ROLLBACK_BLOCKS` | No | `50` | Blocks to rollback on reorg |
| `LOG_LEVEL` | No | `INFO` | Logging level |

#### RabbitMQ
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RABBITMQ_HOST` | No | `localhost` | RabbitMQ hostname |
| `RABBITMQ_PORT` | No | `5672` | RabbitMQ AMQP port |
| `RABBITMQ_USER` | No | `guest` | RabbitMQ username |
| `RABBITMQ_PASSWORD` | No | `guest` | RabbitMQ password |
| `RABBITMQ_VHOST` | No | `/` | RabbitMQ virtual host |
| `RABBITMQ_EXCHANGE` | No | `blockchain_events` | Exchange name |
| `RABBITMQ_PREFETCH_COUNT` | No | `10` | Messages per consumer |

#### Consumer
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CONSUMER_WORKERS` | No | `4` | Number of worker processes |
| `MAX_RETRIES` | No | `3` | Max retries before DLQ |
| `RECONCILIATION_INTERVAL_SECONDS` | No | `300` | Reconciliation interval |

## Docker Setup

Start PostgreSQL and RabbitMQ from the `stuff-crowd-funding` directory:

```bash
cd stuff-crowd-funding
docker compose up -d
```

This starts:
- PostgreSQL on port `5437` (user: `crowdfunding`, pass: `crowdfunding_pass`, db: `crowdfunding_app`)
- RabbitMQ on port `5672` (AMQP) and `15672` (Management UI)
- pgAdmin on port `5050`

Access RabbitMQ Management UI at http://localhost:15672 (guest/guest).

## Usage

### Quick Start

1. Start infrastructure:
```bash
docker compose up -d
```

2. Set up RabbitMQ exchanges and queues:
```bash
python -m indexer broker setup
```

3. Start the consumer (in one terminal):
```bash
python -m indexer consumer run
```

4. Start the producer (in another terminal):
```bash
python -m indexer producer run
```

### CLI Commands

#### Broker Commands

Set up RabbitMQ exchanges and queues:
```bash
python -m indexer broker setup
```

Check broker status and queue depths:
```bash
python -m indexer broker status
```

Purge a specific queue:
```bash
python -m indexer broker purge queue.campaign_created
```

#### Producer Commands

Run producer in continuous polling mode:
```bash
python -m indexer producer run
```

Backfill historical blocks:
```bash
python -m indexer producer backfill --from-block 0 --to-block 1000
```

Check producer status:
```bash
python -m indexer producer status
```

#### Consumer Commands

Run consumer with default workers (from config):
```bash
python -m indexer consumer run
```

Run with specific number of workers:
```bash
python -m indexer consumer run --workers 8
```

Check consumer status (queue depths):
```bash
python -m indexer consumer status
```

#### Legacy Commands (backward compatibility)

These commands still work for backward compatibility:

```bash
# Run both producer and consumer (not recommended for production)
python -m indexer run

# Backfill (producer-only)
python -m indexer backfill --from-block 0 --to-block 1000

# Status (producer status)
python -m indexer status
```

## Running Against Hardhat Localhost

### 1. Start Hardhat Node

In one terminal:
```bash
cd smartcontract
npx hardhat node
```

### 2. Deploy Contracts

In another terminal:
```bash
cd smartcontract
npx hardhat run scripts/deploy.ts --network localhost
```

Note the Factory address from the output.

### 3. Start Infrastructure

```bash
cd indexer
docker compose up -d
```

### 4. Configure Environment

```bash
export FACTORY_ADDRESS=<factory_address_from_deploy>
export DB_URL=postgresql://crowd_user:crowd_pass@localhost:5433/crowdfunding
export RPC_URL=http://127.0.0.1:8545
export CHAIN_ID=31337
```

### 5. Set Up Broker

```bash
python -m indexer broker setup
```

### 6. Start Consumer

In one terminal:
```bash
python -m indexer consumer run
```

### 7. Start Producer

In another terminal:
```bash
python -m indexer producer run
```

## Message Flow

### Event Messages

When the producer detects a blockchain event:

1. Producer decodes event from blockchain
2. Producer publishes `EventMessage` to RabbitMQ
3. Consumer receives message from appropriate queue
4. Consumer inserts event to `events` table
5. Consumer applies state update (campaign/contribution)
6. Consumer ACKs message

### Rollback Messages

When the producer detects a blockchain reorg:

1. Producer detects block hash mismatch
2. Producer publishes `RollbackMessage` to control queue
3. Producer updates sync_state to pre-reorg block
4. Consumer receives rollback message
5. Consumer marks affected events as removed
6. Consumer rebuilds state from remaining events

### Reconciliation Messages

Periodically:

1. Producer publishes `ReconciliationMessage` to control queue
2. Consumer receives reconciliation message
3. Consumer marks expired campaigns as FAILED

## RabbitMQ Topology

### Exchange

- **Name**: `blockchain_events` (topic type)
- **Dead Letter Exchange**: `blockchain_events.dlx`

### Queues

| Queue | Routing Keys | Purpose |
|-------|--------------|---------|
| `queue.campaign_created` | `event.campaign_created` | New campaigns |
| `queue.donation_received` | `event.donation_received` | Donations |
| `queue.withdrawal_refund` | `event.withdrawn`, `event.refunded` | Withdrawals & refunds |
| `queue.control` | `control.rollback`, `control.reconciliation` | Control messages |
| `dlq.events` | `#` (from DLX) | Failed messages |

## Database Schema Assumptions

The indexer assumes these tables exist (created by backend migrations):

### chains
- `id`, `name`, `chain_id`, `rpc_url`, `created_at`, `updated_at`

### sync_state
- `chain_id`, `last_block`, `last_block_hash`, `updated_at`

### campaigns
- `address`, `factory_address`, `creator_address`, `goal_wei`, `deadline_ts`, `cid`, `status`, `total_raised_wei`, `withdrawn`, `withdrawn_amount_wei`, `created_at`, `updated_at`

### contributions
- `id`, `campaign_address`, `donor_address`, `contributed_wei`, `refunded_wei`, `created_at`, `updated_at`
- Unique constraint: `(campaign_address, donor_address)`

### events
- `id`, `chain_id`, `tx_hash`, `log_index`, `block_number`, `block_hash`, `address`, `event_name`, `event_data`, `removed`, `created_at`
- Unique constraint: `(chain_id, tx_hash, log_index)`

## Monitoring

### RabbitMQ Management UI

Access at http://localhost:15672 (guest/guest) to:
- Monitor queue depths
- Check message rates
- Inspect dead letter queue
- View consumer connections

### CLI Status Commands

```bash
# Producer status (sync state, blocks behind)
python -m indexer producer status

# Consumer status (queue depths)
python -m indexer consumer status

# Broker status (detailed queue info)
python -m indexer broker status
```

### Log Files

The indexer logs to stdout. Configure `LOG_LEVEL` for verbosity:
- `DEBUG`: All operations including message details
- `INFO`: Normal operations
- `WARNING`: Potential issues
- `ERROR`: Errors only

## Troubleshooting

### "DB schema missing. Run backend migrations first."
- **Solution**: Run your backend database migrations to create the required tables.

### "Failed to connect to RabbitMQ"
- **Solution**: Ensure RabbitMQ is running (`docker compose up -d`)
- Check RABBITMQ_HOST and RABBITMQ_PORT settings
- Verify credentials (RABBITMQ_USER/RABBITMQ_PASSWORD)

### "Failed to connect to RPC"
- **Solution**: Ensure Hardhat node is running or RPC_URL is correct.

### Messages stuck in Dead Letter Queue
- Check `dlq.events` in RabbitMQ Management UI
- Inspect message headers for error details
- Fix the issue and republish messages

### Consumer not processing messages
- Check consumer is running: `python -m indexer consumer status`
- Verify queues exist: `python -m indexer broker status`
- Check for errors in consumer logs

### High queue depth
- Increase `CONSUMER_WORKERS` for more parallelism
- Check database connection pool
- Monitor consumer processing rate

### Events not being indexed
- Check RPC connection
- Verify Factory address is correct
- Check producer logs for errors
- Verify messages are being published to RabbitMQ

## Project Structure

```
indexer/
├── __init__.py
├── __main__.py              # Entry point for python -m indexer
├── cli.py                   # CLI with producer/consumer/broker commands
├── config.py                # Configuration management
├── log.py                   # Logging setup
├── requirements.txt         # Python dependencies
├── .env.example             # Example environment variables
│
├── messaging/               # RabbitMQ integration
│   ├── __init__.py
│   ├── schema.py            # Pydantic message schemas
│   ├── routing.py           # Exchange/queue/routing definitions
│   └── rabbitmq.py          # RabbitMQ connection/publisher/consumer
│
├── producer/                # Blockchain event producer
│   ├── __init__.py
│   ├── main.py              # Producer main loop
│   ├── publisher.py         # Event publishing to RabbitMQ
│   ├── factory_py   # Factory event indexing
│   ├── campaign_py  # Campaign event indexing
│   └── reorg_detector.py    # Reorg detection and rollback
│
├── consumer/                # Database event consumer
│   ├── __init__.py
│   ├── main.py              # Consumer worker pool
│   ├── event_handler.py     # Message dispatch and error handling
│   ├── state_updater.py     # Database state updates
│   ├── rollback_handler.py  # Reorg rollback processing
│   └── reconciliation_handler.py  # Periodic reconciliation
│
├── db/                      # Database layer
│   ├── session.py           # Database session management
│   ├── models.py            # ORM models (read-only, no create_all)
│   └── healthcheck.py       # Schema validation
│
├── eth/                     # Ethereum client
│   ├── client.py            # Web3 client
│   ├── abi_loader.py        # ABI file loading
│   ├── topics.py            # Event topic hashes
│   └── decoder.py           # Event decoding
│
├── pipeline/                # Legacy pipeline (deprecated)
│   ├── factory_py
│   ├── campaign_py
│   ├── reorg.py
│   └── reconciler.py
│
├── services/                # Legacy services (deprecated)
│   └── state_updater.py
│
└── abi/                     # Contract ABIs
    ├── CampaignFactory.json
    └── Campaign.json
```

## License

MIT
