"""IPFS Gateway client for fetching campaign metadata."""

import logging
from typing import Any, Optional
from django.conf import settings
import httpx

logger = logging.getLogger(__name__)


class IPFSGatewayError(Exception):
    """Base exception for IPFS gateway errors."""
    pass


class IPFSFetchError(IPFSGatewayError):
    """Raised when fetching from IPFS fails."""
    pass


class IPFSTimeoutError(IPFSGatewayError):
    """Raised when IPFS request times out."""
    pass


class IPFSGatewayClient:
    """Client for interacting with IPFS gateways.
    
    Fetches content from IPFS using HTTP gateways.
    Supports configurable gateway URLs and timeouts.
    
    Example usage:
        client = IPFSGatewayClient()
        data = await client.fetch_json("QmXxx...")
    """
    
    def __init__(
        self,
        gateway_url: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        """Initialize the IPFS gateway client.
        
        Args:
            gateway_url: IPFS gateway base URL. Defaults to settings.IPFS_GATEWAY_URL
            timeout: Request timeout in seconds. Defaults to settings.IPFS_FETCH_TIMEOUT
        """
        self.gateway_url = gateway_url or getattr(
            settings, 'IPFS_GATEWAY_URL', 'https://ipfs.io/ipfs/'
        )
        self.timeout = timeout or getattr(settings, 'IPFS_FETCH_TIMEOUT', 30)
        
        # Ensure gateway URL ends with /
        if not self.gateway_url.endswith('/'):
            self.gateway_url += '/'
    
    def _build_url(self, cid: str) -> str:
        """Build the full URL for an IPFS CID.
        
        Args:
            cid: The IPFS content identifier
            
        Returns:
            Full URL to fetch the content
        """
        # Handle ipfs:// URLs
        if cid.startswith('ipfs://'):
            cid = cid[7:]
        return f"{self.gateway_url}{cid}"
    
    def get_gateway_url(self, cid: str) -> str:
        """Get the public gateway URL for a CID.
        
        Useful for returning URLs to clients for direct access.
        
        Args:
            cid: The IPFS content identifier
            
        Returns:
            Full gateway URL for the CID
        """
        if cid.startswith('ipfs://'):
            cid = cid[7:]
        return f"{self.gateway_url}{cid}"
    
    async def fetch_json(self, cid: str) -> dict[str, Any]:
        """Fetch JSON content from IPFS.
        
        Args:
            cid: The IPFS content identifier
            
        Returns:
            Parsed JSON data as a dictionary
            
        Raises:
            IPFSFetchError: If the request fails
            IPFSTimeoutError: If the request times out
        """
        url = self._build_url(cid)
        logger.debug(f"Fetching IPFS content from: {url}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as e:
            logger.error(f"Timeout fetching IPFS content: {cid}")
            raise IPFSTimeoutError(f"Timeout fetching CID: {cid}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching IPFS content: {e.response.status_code}")
            raise IPFSFetchError(
                f"HTTP {e.response.status_code} fetching CID: {cid}"
            ) from e
        except Exception as e:
            logger.error(f"Error fetching IPFS content: {e}")
            raise IPFSFetchError(f"Failed to fetch CID: {cid}") from e
    
    def fetch_json_sync(self, cid: str) -> dict[str, Any]:
        """Synchronous version of fetch_json.
        
        Args:
            cid: The IPFS content identifier
            
        Returns:
            Parsed JSON data as a dictionary
            
        Raises:
            IPFSFetchError: If the request fails
            IPFSTimeoutError: If the request times out
        """
        url = self._build_url(cid)
        logger.debug(f"Fetching IPFS content (sync) from: {url}")
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as e:
            logger.error(f"Timeout fetching IPFS content: {cid}")
            raise IPFSTimeoutError(f"Timeout fetching CID: {cid}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching IPFS content: {e.response.status_code}")
            raise IPFSFetchError(
                f"HTTP {e.response.status_code} fetching CID: {cid}"
            ) from e
        except Exception as e:
            logger.error(f"Error fetching IPFS content: {e}")
            raise IPFSFetchError(f"Failed to fetch CID: {cid}") from e
    
    async def fetch_raw(self, cid: str) -> bytes:
        """Fetch raw bytes content from IPFS.
        
        Args:
            cid: The IPFS content identifier
            
        Returns:
            Raw bytes content
            
        Raises:
            IPFSFetchError: If the request fails
            IPFSTimeoutError: If the request times out
        """
        url = self._build_url(cid)
        logger.debug(f"Fetching raw IPFS content from: {url}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.content
        except httpx.TimeoutException as e:
            logger.error(f"Timeout fetching IPFS content: {cid}")
            raise IPFSTimeoutError(f"Timeout fetching CID: {cid}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching IPFS content: {e.response.status_code}")
            raise IPFSFetchError(
                f"HTTP {e.response.status_code} fetching CID: {cid}"
            ) from e
        except Exception as e:
            logger.error(f"Error fetching IPFS content: {e}")
            raise IPFSFetchError(f"Failed to fetch CID: {cid}") from e
