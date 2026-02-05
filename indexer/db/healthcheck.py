"""Database health check - verify required tables exist."""

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from db.session import get_engine, get_session
from log import get_logger

logger = get_logger(__name__)

# Required tables that must exist
REQUIRED_TABLES = [
    "chains",
    "sync_state",
    "campaigns",
    "contributions",
    "events",
]


def check_tables_exist() -> None:
    """Verify all required tables exist in the database.

    Raises:
        RuntimeError: If any required table is missing
    """
    logger.info("Checking database schema...")

    with get_session() as session:
        for table_name in REQUIRED_TABLES:
            try:
                # Try to query the table (will fail if table doesn't exist)
                session.execute(text(f"SELECT 1 FROM {table_name} LIMIT 1"))
                logger.debug(f"Table '{table_name}' exists")
            except ProgrammingError as e:
                error_msg = str(e).lower()
                if "does not exist" in error_msg or "relation" in error_msg:
                    raise RuntimeError(
                        f"DB schema missing. Table '{table_name}' does not exist. "
                        "Run backend migrations first."
                    ) from e
                # Re-raise if it's a different error
                raise

    logger.info("All required tables exist")


def check_chain_exists(chain_id: int) -> bool:
    """Check if chain record exists in database.

    Args:
        chain_id: Chain ID to check

    Returns:
        True if chain exists, False otherwise
    """
    from db.models import Chain

    with get_session() as session:
        chain = session.query(Chain).filter(Chain.chain_id == chain_id).first()
        return chain is not None

