"""Metadata resolver for fetching and caching campaign metadata from IPFS."""

import logging
from datetime import timedelta
from typing import Any, Optional
from django.conf import settings
from django.utils import timezone
from core.models import Campaign, CampaignMetadata
from core.services.ipfs import IPFSGatewayClient, IPFSGatewayError

logger = logging.getLogger(__name__)


class MetadataResolverError(Exception):
    """Base exception for metadata resolver errors."""
    pass


class CampaignNotFoundError(MetadataResolverError):
    """Raised when a campaign is not found."""
    pass


class MetadataFetchError(MetadataResolverError):
    """Raised when metadata fetch fails."""
    pass


class MetadataResolver:
    """Resolves and caches campaign metadata from IPFS.
    
    This service fetches metadata from IPFS and stores it in the
    CampaignMetadata model. It includes caching logic to avoid
    frequent IPFS requests.
    
    Example usage:
        resolver = MetadataResolver()
        metadata = resolver.resolve("0x...")  # Returns cached or fetches new
        metadata = resolver.refresh("0x...")  # Force refresh from IPFS
    """
    
    # Default cache duration in hours
    DEFAULT_CACHE_DURATION_HOURS = 24
    
    def __init__(
        self,
        ipfs_client: Optional[IPFSGatewayClient] = None,
        cache_duration_hours: Optional[int] = None
    ):
        """Initialize the metadata resolver.
        
        Args:
            ipfs_client: IPFS gateway client instance. Created if not provided.
            cache_duration_hours: How long to cache metadata. Defaults to settings
                or DEFAULT_CACHE_DURATION_HOURS.
        """
        self.ipfs_client = ipfs_client or IPFSGatewayClient()
        self.cache_duration = timedelta(hours=cache_duration_hours or getattr(
            settings, 'METADATA_CACHE_DURATION_HOURS', self.DEFAULT_CACHE_DURATION_HOURS
        ))
    
    def _is_cache_valid(self, metadata: CampaignMetadata) -> bool:
        """Check if cached metadata is still valid.
        
        Args:
            metadata: The cached metadata instance
            
        Returns:
            True if cache is still valid, False if expired
        """
        if not metadata.ipfs_fetched_at:
            return False
        
        expiry_time = metadata.ipfs_fetched_at + self.cache_duration
        return timezone.now() < expiry_time
    
    def _parse_metadata(self, raw_json: dict[str, Any]) -> dict[str, Any]:
        """Parse raw IPFS JSON into model fields.
        
        Args:
            raw_json: Raw JSON data from IPFS
            
        Returns:
            Dictionary of model field values
        """
        # Extract fields with fallbacks for different JSON structures
        return {
            'name': raw_json.get('name') or raw_json.get('title'),
            'description': raw_json.get('description'),
            'short_description': (
                raw_json.get('short_description') or
                raw_json.get('shortDescription') or
                raw_json.get('summary')
            ),
            'image_cid': (
                raw_json.get('image') or
                raw_json.get('image_cid') or
                raw_json.get('imageCid')
            ),
            'banner_cid': (
                raw_json.get('banner') or
                raw_json.get('banner_cid') or
                raw_json.get('bannerCid') or
                raw_json.get('cover')
            ),
            'category': raw_json.get('category'),
            'tags': raw_json.get('tags', []),
            'location': raw_json.get('location'),
            'creator_name': (
                raw_json.get('creator_name') or
                raw_json.get('creatorName') or
                raw_json.get('author')
            ),
            'creator_avatar_cid': (
                raw_json.get('creator_avatar') or
                raw_json.get('creatorAvatar') or
                raw_json.get('avatar')
            ),
            'website_url': (
                raw_json.get('website') or
                raw_json.get('website_url') or
                raw_json.get('url')
            ),
            'twitter_handle': (
                raw_json.get('twitter') or
                raw_json.get('twitter_handle') or
                raw_json.get('twitterHandle')
            ),
            'discord_url': (
                raw_json.get('discord') or
                raw_json.get('discord_url') or
                raw_json.get('discordUrl')
            ),
        }
    
    def _get_campaign(self, campaign_address: str) -> Campaign:
        """Get campaign by address.
        
        Args:
            campaign_address: Ethereum address of the campaign
            
        Returns:
            Campaign instance
            
        Raises:
            CampaignNotFoundError: If campaign doesn't exist
        """
        try:
            return Campaign.objects.get(address__iexact=campaign_address)
        except Campaign.DoesNotExist:
            raise CampaignNotFoundError(f"Campaign not found: {campaign_address}")
    
    def resolve(self, campaign_address: str, force_refresh: bool = False) -> Optional[CampaignMetadata]:
        """Resolve metadata for a campaign.
        
        Returns cached metadata if valid, otherwise fetches from IPFS.
        
        Args:
            campaign_address: Ethereum address of the campaign
            force_refresh: If True, bypass cache and fetch from IPFS
            
        Returns:
            CampaignMetadata instance or None if no CID available
            
        Raises:
            CampaignNotFoundError: If campaign doesn't exist
            MetadataFetchError: If IPFS fetch fails
        """
        campaign = self._get_campaign(campaign_address)
        
        # Check if campaign has a CID
        if not campaign.cid:
            logger.debug(f"Campaign {campaign_address} has no CID")
            return None
        
        # Try to get existing metadata
        try:
            metadata = CampaignMetadata.objects.get(campaign=campaign)
            
            # Return cached if valid and not forcing refresh
            if not force_refresh and self._is_cache_valid(metadata):
                logger.debug(f"Returning cached metadata for {campaign_address}")
                return metadata
            
            # Refresh existing metadata
            logger.info(f"Refreshing metadata for {campaign_address}")
            return self._fetch_and_update(campaign, metadata)
            
        except CampaignMetadata.DoesNotExist:
            # Create new metadata
            logger.info(f"Creating new metadata for {campaign_address}")
            return self._fetch_and_create(campaign)
    
    def refresh(self, campaign_address: str) -> Optional[CampaignMetadata]:
        """Force refresh metadata from IPFS.
        
        Args:
            campaign_address: Ethereum address of the campaign
            
        Returns:
            Updated CampaignMetadata instance
            
        Raises:
            CampaignNotFoundError: If campaign doesn't exist
            MetadataFetchError: If IPFS fetch fails
        """
        return self.resolve(campaign_address, force_refresh=True)
    
    def _fetch_and_create(self, campaign: Campaign) -> CampaignMetadata:
        """Fetch from IPFS and create new metadata record.
        
        Args:
            campaign: Campaign instance
            
        Returns:
            New CampaignMetadata instance
            
        Raises:
            MetadataFetchError: If IPFS fetch fails
        """
        try:
            raw_json = self.ipfs_client.fetch_json_sync(campaign.cid)
        except IPFSGatewayError as e:
            raise MetadataFetchError(f"Failed to fetch metadata: {e}") from e
        
        parsed = self._parse_metadata(raw_json)
        
        metadata = CampaignMetadata.objects.create(
            campaign=campaign,
            cid=campaign.cid,
            raw_json=raw_json,
            ipfs_fetched_at=timezone.now(),
            **parsed
        )
        
        logger.info(f"Created metadata for campaign {campaign.address}")
        return metadata
    
    def _fetch_and_update(
        self,
        campaign: Campaign,
        metadata: CampaignMetadata
    ) -> CampaignMetadata:
        """Fetch from IPFS and update existing metadata record.
        
        Args:
            campaign: Campaign instance
            metadata: Existing metadata instance to update
            
        Returns:
            Updated CampaignMetadata instance
            
        Raises:
            MetadataFetchError: If IPFS fetch fails
        """
        try:
            raw_json = self.ipfs_client.fetch_json_sync(campaign.cid)
        except IPFSGatewayError as e:
            raise MetadataFetchError(f"Failed to fetch metadata: {e}") from e
        
        parsed = self._parse_metadata(raw_json)
        
        # Update all fields
        metadata.cid = campaign.cid
        metadata.raw_json = raw_json
        metadata.ipfs_fetched_at = timezone.now()
        
        for field, value in parsed.items():
            setattr(metadata, field, value)
        
        metadata.save()
        
        logger.info(f"Updated metadata for campaign {campaign.address}")
        return metadata
    
    def get_cached(self, campaign_address: str) -> Optional[CampaignMetadata]:
        """Get cached metadata without fetching from IPFS.
        
        Args:
            campaign_address: Ethereum address of the campaign
            
        Returns:
            CampaignMetadata instance or None if not cached
        """
        try:
            return CampaignMetadata.objects.select_related('campaign').get(
                campaign__address__iexact=campaign_address
            )
        except CampaignMetadata.DoesNotExist:
            return None
    
    def bulk_resolve(
        self,
        campaign_addresses: list[str],
        skip_errors: bool = True
    ) -> dict[str, Optional[CampaignMetadata]]:
        """Resolve metadata for multiple campaigns.
        
        Args:
            campaign_addresses: List of campaign addresses
            skip_errors: If True, continue on errors. If False, raise on first error.
            
        Returns:
            Dictionary mapping addresses to metadata (or None)
        """
        results = {}
        
        for address in campaign_addresses:
            try:
                results[address] = self.resolve(address)
            except MetadataResolverError as e:
                logger.warning(f"Error resolving metadata for {address}: {e}")
                if skip_errors:
                    results[address] = None
                else:
                    raise
        
        return results
