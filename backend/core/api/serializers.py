"""DRF serializers for blockchain models."""

import json
from django.conf import settings
from rest_framework import serializers
from core.models import Chain, SyncState, Campaign, Contribution, Event, CampaignMetadata
from core.utils.formatting import wei_to_eth, timestamp_to_datetime, format_address


class ChainSerializer(serializers.ModelSerializer):
    """Serializer for Chain model."""
    
    class Meta:
        model = Chain
        fields = ['id', 'name', 'chain_id', 'rpc_url', 'created_at', 'updated_at']
        read_only_fields = fields


class SyncStateSerializer(serializers.ModelSerializer):
    """Serializer for SyncState model."""
    
    chain_name = serializers.CharField(source='chain.name', read_only=True)
    
    class Meta:
        model = SyncState
        fields = ['chain_id', 'chain_name', 'last_block', 'last_block_hash', 'updated_at']
        read_only_fields = fields


class CampaignSerializer(serializers.ModelSerializer):
    """Serializer for Campaign model."""
    
    # Computed fields
    goal_eth = serializers.SerializerMethodField()
    total_raised_eth = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()
    deadline_iso = serializers.SerializerMethodField()
    withdrawn_amount_eth = serializers.SerializerMethodField()
    
    # Normalize addresses to lowercase
    address = serializers.SerializerMethodField()
    factory_address = serializers.SerializerMethodField()
    creator_address = serializers.SerializerMethodField()
    
    class Meta:
        model = Campaign
        fields = [
            'address',
            'factory_address',
            'creator_address',
            'goal_wei',
            'goal_eth',
            'deadline_ts',
            'deadline_iso',
            'cid',
            'status',
            'total_raised_wei',
            'total_raised_eth',
            'progress_percent',
            'withdrawn',
            'withdrawn_amount_wei',
            'withdrawn_amount_eth',
            'created_at',
            'updated_at'
        ]
        read_only_fields = fields
    
    def get_address(self, obj):
        return format_address(obj.address)
    
    def get_factory_address(self, obj):
        return format_address(obj.factory_address)
    
    def get_creator_address(self, obj):
        return format_address(obj.creator_address)
    
    def get_goal_eth(self, obj):
        return str(wei_to_eth(obj.goal_wei))
    
    def get_total_raised_eth(self, obj):
        return str(wei_to_eth(obj.total_raised_wei))
    
    def get_progress_percent(self, obj):
        if obj.goal_wei and obj.goal_wei > 0:
            return round((obj.total_raised_wei / obj.goal_wei) * 100, 2)
        return 0.0
    
    def get_deadline_iso(self, obj):
        dt = timestamp_to_datetime(obj.deadline_ts)
        if dt:
            return dt.isoformat()
        return None
    
    def get_withdrawn_amount_eth(self, obj):
        if obj.withdrawn_amount_wei:
            return str(wei_to_eth(obj.withdrawn_amount_wei))
        return None


class ContributionSerializer(serializers.ModelSerializer):
    """Serializer for Contribution model."""
    
    # Computed fields
    contributed_eth = serializers.SerializerMethodField()
    refunded_eth = serializers.SerializerMethodField()
    net_contributed_eth = serializers.SerializerMethodField()
    
    # Normalize addresses
    campaign_address = serializers.SerializerMethodField()
    donor_address = serializers.SerializerMethodField()
    
    class Meta:
        model = Contribution
        fields = [
            'id',
            'campaign_address',
            'donor_address',
            'contributed_wei',
            'contributed_eth',
            'refunded_wei',
            'refunded_eth',
            'net_contributed_eth',
            'created_at',
            'updated_at'
        ]
        read_only_fields = fields
    
    def get_campaign_address(self, obj):
        return format_address(obj.campaign_address.address)
    
    def get_donor_address(self, obj):
        return format_address(obj.donor_address)
    
    def get_contributed_eth(self, obj):
        return str(wei_to_eth(obj.contributed_wei))
    
    def get_refunded_eth(self, obj):
        return str(wei_to_eth(obj.refunded_wei))
    
    def get_net_contributed_eth(self, obj):
        net_wei = obj.contributed_wei - obj.refunded_wei
        return str(wei_to_eth(net_wei))


class ContributionWithCampaignSerializer(ContributionSerializer):
    """Serializer for Contribution with nested campaign info."""
    
    campaign = CampaignSerializer(source='campaign_address', read_only=True)
    
    class Meta(ContributionSerializer.Meta):
        fields = ContributionSerializer.Meta.fields + ['campaign']


class EventSerializer(serializers.ModelSerializer):
    """Serializer for Event model."""
    
    # Normalize addresses
    address = serializers.SerializerMethodField()
    event_data_parsed = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id',
            'chain_id',
            'tx_hash',
            'log_index',
            'block_number',
            'block_hash',
            'address',
            'event_name',
            'event_data',
            'event_data_parsed',
            'removed',
            'created_at'
        ]
        read_only_fields = fields
    
    def get_address(self, obj):
        if obj.address:
            return format_address(obj.address.address)
        return None
    
    def get_event_data_parsed(self, obj):
        """Parse JSON event_data if valid."""
        if not obj.event_data:
            return None
        try:
            return json.loads(obj.event_data)
        except json.JSONDecodeError:
            return None


class CampaignDetailSerializer(CampaignSerializer):
    """Extended serializer for campaign detail view with related data."""
    
    contributions_count = serializers.SerializerMethodField()
    events_count = serializers.SerializerMethodField()
    
    class Meta(CampaignSerializer.Meta):
        fields = CampaignSerializer.Meta.fields + ['contributions_count', 'events_count']
    
    def get_contributions_count(self, obj):
        return obj.contributions.count()
    
    def get_events_count(self, obj):
        return obj.events.count()


# =============================================================================
# Campaign Metadata Serializers
# =============================================================================

class CampaignMetadataSerializer(serializers.ModelSerializer):
    """Serializer for CampaignMetadata model."""
    
    # Computed IPFS gateway URLs
    image_url = serializers.SerializerMethodField()
    banner_url = serializers.SerializerMethodField()
    creator_avatar_url = serializers.SerializerMethodField()
    
    # Campaign address
    campaign_address = serializers.SerializerMethodField()
    
    class Meta:
        model = CampaignMetadata
        fields = [
            'id',
            'campaign_address',
            'cid',
            'name',
            'description',
            'short_description',
            'image_cid',
            'image_url',
            'banner_cid',
            'banner_url',
            'category',
            'tags',
            'location',
            'creator_name',
            'creator_avatar_cid',
            'creator_avatar_url',
            'website_url',
            'twitter_handle',
            'discord_url',
            'ipfs_fetched_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields
    
    def _get_gateway_url(self) -> str:
        """Get the IPFS gateway URL from settings."""
        gateway = getattr(settings, 'IPFS_GATEWAY_URL', 'https://ipfs.io/ipfs/')
        if not gateway.endswith('/'):
            gateway += '/'
        return gateway
    
    def _resolve_ipfs_url(self, cid: str) -> str | None:
        """Resolve an IPFS CID to a gateway URL."""
        if not cid:
            return None
        # Handle ipfs:// URLs
        if cid.startswith('ipfs://'):
            cid = cid[7:]
        return f"{self._get_gateway_url()}{cid}"
    
    def get_campaign_address(self, obj):
        return format_address(obj.campaign.address)
    
    def get_image_url(self, obj):
        return self._resolve_ipfs_url(obj.image_cid)
    
    def get_banner_url(self, obj):
        return self._resolve_ipfs_url(obj.banner_cid)
    
    def get_creator_avatar_url(self, obj):
        return self._resolve_ipfs_url(obj.creator_avatar_cid)


class CampaignMetadataSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for metadata when nested in campaign responses."""
    
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CampaignMetadata
        fields = [
            'name',
            'short_description',
            'image_url',
            'category',
        ]
        read_only_fields = fields
    
    def _get_gateway_url(self) -> str:
        gateway = getattr(settings, 'IPFS_GATEWAY_URL', 'https://ipfs.io/ipfs/')
        if not gateway.endswith('/'):
            gateway += '/'
        return gateway
    
    def get_image_url(self, obj):
        if not obj.image_cid:
            return None
        cid = obj.image_cid
        if cid.startswith('ipfs://'):
            cid = cid[7:]
        return f"{self._get_gateway_url()}{cid}"


class CampaignWithMetadataSerializer(CampaignSerializer):
    """Campaign serializer that includes nested metadata."""
    
    metadata = CampaignMetadataSummarySerializer(read_only=True)
    
    class Meta(CampaignSerializer.Meta):
        fields = CampaignSerializer.Meta.fields + ['metadata']


class CampaignDetailWithMetadataSerializer(CampaignDetailSerializer):
    """Campaign detail serializer that includes full metadata."""
    
    metadata = CampaignMetadataSerializer(read_only=True)
    
    class Meta(CampaignDetailSerializer.Meta):
        fields = CampaignDetailSerializer.Meta.fields + ['metadata']

