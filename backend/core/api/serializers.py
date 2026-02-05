"""DRF serializers for blockchain models."""

import json
from rest_framework import serializers
from core.models import Chain, SyncState, Campaign, Contribution, Event
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

