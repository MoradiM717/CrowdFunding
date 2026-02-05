# Crowdfunding Backend

Django REST Framework backend for the blockchain crowdfunding platform. This backend provides a read-only API and Django Admin interface for viewing blockchain-indexed data.

## ⚠️ IMPORTANT: Database Schema

**The database tables MUST already exist before running this backend.** The tables are created via `schema.sql` (not Django migrations). All blockchain models are unmanaged (`managed=False`) to prevent Django from creating or altering these tables.

If you see errors about missing tables, ensure you've run the schema.sql script against your PostgreSQL database first.

## Prerequisites

- Python 3.12+
- PostgreSQL 16+ (or use Docker Compose)
- Existing database with schema created from `schema.sql`

## Installation

1. **Create and activate a virtual environment:**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Set up environment variables:**

Copy `.env.example` to `.env` and update the values:

```bash
cp .env.example .env
```

Edit `.env` with your database credentials:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=crowdfunding_app
DB_USER=crowdfunding
DB_PASSWORD=crowdfunding_pass
DB_HOST=localhost
DB_PORT=5437
```

## Database Setup

### Option 1: Using Docker Compose

1. **Start PostgreSQL:**

```bash
cd ../stuff-crowd-funding
docker-compose up -d db
```

2. **Create database schema:**

```bash
# Connect to PostgreSQL and run schema.sql
psql -h localhost -p 5437 -U crowdfunding -d crowdfunding_app -f ../database-stuff/commands.sql
```

Or using Docker:

```bash
docker exec -i crowdfunding_db psql -U crowdfunding -d crowdfunding_app < ../database-stuff/commands.sql
```

### Option 2: Local PostgreSQL

1. **Create database:**

```bash
createdb -U postgres crowdfunding_app
```

2. **Run schema.sql:**

```bash
psql -U postgres -d crowdfunding_app -f ../database-stuff/commands.sql
```

## Running the Backend

1. **Run Django migrations (only for Django internal tables):**

```bash
python manage.py migrate
```

This will create Django's internal tables (auth, sessions, admin) but **NOT** the blockchain tables (those must exist already).

2. **Create a superuser for Django Admin:**

```bash
python manage.py createsuperuser
```

3. **Run the development server:**

```bash
python manage.py runserver
```

The server will start at `http://127.0.0.1:8000/`

## Access Points

- **Django Admin**: http://127.0.0.1:8000/admin/
- **API Root**: http://127.0.0.1:8000/api/v1/
- **Swagger UI**: http://127.0.0.1:8000/api/schema/swagger-ui/
- **API Schema (JSON)**: http://127.0.0.1:8000/api/schema/

## API Endpoints

### Campaigns

- `GET /api/v1/campaigns/` - List all campaigns (with filtering, pagination, ordering)
- `GET /api/v1/campaigns/{address}/` - Campaign details
- `GET /api/v1/campaigns/{address}/contributions/` - Campaign contributions
- `GET /api/v1/campaigns/{address}/events/` - Campaign events

**Campaign Filters:**
- `status` - Filter by status (ACTIVE, SUCCESS, FAILED, WITHDRAWN)
- `creator_address` - Filter by creator address
- `factory_address` - Filter by factory address
- `min_goal`, `max_goal` - Filter by goal range (in wei)
- `min_raised` - Filter by minimum raised amount (in wei)
- `has_withdrawn` - Filter by withdrawal status (true/false)
- `deadline_before`, `deadline_after` - Filter by deadline (Unix timestamp)

**Ordering:**
- `ordering=created_at` - Order by creation date
- `ordering=-deadline_ts` - Order by deadline (descending)
- `ordering=goal_wei` - Order by goal amount
- `ordering=-total_raised_wei` - Order by total raised (descending)

### Creators / Donors

- `GET /api/v1/creators/{creator_address}/campaigns/` - Campaigns by creator
- `GET /api/v1/donors/{donor_address}/contributions/` - Contributions by donor (with campaign info)

### Chains / Sync

- `GET /api/v1/chains/` - List all chains
- `GET /api/v1/chains/{chain_id}/sync-state/` - Sync state for a chain

### Events

- `GET /api/v1/events/` - List all events (with filtering)

**Event Filters:**
- `chain_id` - Filter by chain ID
- `event_name` - Filter by event name (CampaignCreated, DonationReceived, etc.)
- `address` - Filter by campaign address
- `block_number_gte`, `block_number_lte` - Filter by block number range
- `tx_hash` - Filter by transaction hash
- `removed` - Filter by removed status (true/false)

**Ordering:**
- `ordering=-block_number` - Order by block number (descending, default)
- `ordering=-id` - Order by ID (descending)

## API Response Format

All endpoints return JSON with pagination:

```json
{
  "count": 100,
  "next": "http://127.0.0.1:8000/api/v1/campaigns/?page=2",
  "previous": null,
  "results": [...]
}
```

### Campaign Response Example

```json
{
  "address": "0x1234...",
  "factory_address": "0x5678...",
  "creator_address": "0xabcd...",
  "goal_wei": 10000000000000000000,
  "goal_eth": "10.0",
  "deadline_ts": 1704067200,
  "deadline_iso": "2024-01-01T00:00:00",
  "status": "ACTIVE",
  "total_raised_wei": 5000000000000000000,
  "total_raised_eth": "5.0",
  "progress_percent": 50.0,
  "withdrawn": false,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

## Django Admin

The Django Admin provides a user-friendly interface for viewing blockchain data:

- **Campaigns**: View with computed fields (ETH amounts, progress percentage, deadline datetime)
- **Contributions**: View with ETH conversions and net contribution amounts
- **Events**: View with formatted JSON event data
- **Chains & Sync State**: View chain information and sync status

All admin views are **read-only** - you cannot edit blockchain data through the admin (data comes from the blockchain via the indexer).

## Development

### Project Structure

```
backend/
├── manage.py
├── requirements.txt
├── .env.example
├── README.md
├── _base/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── core/
    ├── models.py          # Unmanaged models (managed=False)
    ├── admin.py           # Admin configuration
    └── api/
        ├── serializers.py # DRF serializers
        ├── views.py       # API views
        ├── filters.py     # Django-filter FilterSets
        └── urls.py        # API URL routing
    └── utils/
        └── formatting.py  # Utility functions (wei→eth, etc.)
```

### Key Design Decisions

1. **Unmanaged Models**: All blockchain models have `managed=False` to prevent Django from creating/altering tables
2. **Read-Only API**: All endpoints are GET-only (no POST/PUT/DELETE) since data comes from blockchain
3. **Computed Fields**: Serializers add computed fields (wei→eth, timestamps→ISO) for frontend convenience
4. **Address Normalization**: All addresses are returned in lowercase for consistency
5. **Performance**: Uses `select_related()` and `prefetch_related()` for efficient queries

## Troubleshooting

### "Table does not exist" errors

**Solution**: Ensure you've run `schema.sql` against your database. The backend does not create these tables.

### "No module named django" error

**Solution**: Activate your virtual environment and install dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Database connection errors

**Solution**: 
- Verify PostgreSQL is running
- Check `.env` file has correct database credentials
- Ensure database exists: `psql -U crowdfunding -d crowdfunding_app -c "SELECT 1;"`

### CORS errors from frontend

**Solution**: The backend is configured to allow `localhost:3000` and `localhost:5173`. If using a different port, add it to `CORS_ALLOWED_ORIGINS` in `settings.py`.

## Testing the API

### Using curl

```bash
# List campaigns
curl http://127.0.0.1:8000/api/v1/campaigns/

# Get campaign details
curl http://127.0.0.1:8000/api/v1/campaigns/0x1234.../

# Filter campaigns by status
curl "http://127.0.0.1:8000/api/v1/campaigns/?status=ACTIVE"

# Get creator's campaigns
curl http://127.0.0.1:8000/api/v1/creators/0xabcd.../campaigns/
```

### Using Swagger UI

Visit http://127.0.0.1:8000/api/schema/swagger-ui/ to interact with the API through a web interface.

## Production Considerations

Before deploying to production:

1. **Set `DEBUG=False`** in `.env`
2. **Generate a secure `SECRET_KEY`**: `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
3. **Configure `ALLOWED_HOSTS`** with your domain
4. **Set up proper CORS origins** for your frontend domain
5. **Use a production WSGI server** (e.g., Gunicorn + Nginx)
6. **Set up static file serving** (collectstatic, CDN, etc.)
7. **Configure database connection pooling** for better performance
8. **Set up monitoring and logging**

## License

MIT

