"""Utility functions for formatting blockchain data."""

from decimal import Decimal
from datetime import datetime
from typing import Optional


# Wei to ETH conversion factor (10^18)
WEI_TO_ETH = Decimal('1000000000000000000')


def wei_to_eth(wei: int) -> Decimal:
    """Convert wei to ETH.
    
    Args:
        wei: Amount in wei (smallest unit of ETH)
        
    Returns:
        Decimal: Amount in ETH
    """
    if wei is None:
        return Decimal('0')
    return Decimal(wei) / WEI_TO_ETH


def timestamp_to_datetime(ts: int) -> Optional[datetime]:
    """Convert Unix timestamp to datetime.
    
    Args:
        ts: Unix timestamp (seconds since epoch)
        
    Returns:
        datetime object or None if ts is None
    """
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=None)


def format_address(address: str) -> str:
    """Normalize Ethereum address to lowercase.
    
    Args:
        address: Ethereum address (0x + 40 hex chars)
        
    Returns:
        Lowercase address
    """
    if address is None:
        return None
    return address.lower() if address else None

