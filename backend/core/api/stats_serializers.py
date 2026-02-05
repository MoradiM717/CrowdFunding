"""Serializers for statistics and analytics endpoints."""

from rest_framework import serializers
from core.models import Campaign
from core.api.serializers import CampaignSerializer
from core.utils.formatting import wei_to_eth, format_address


class PlatformStatsSerializer(serializers.Serializer):
    """Serializer for platform-wide statistics."""
    
    # Campaign counts
    total_campaigns = serializers.IntegerField()
    active_campaigns = serializers.IntegerField()
    successful_campaigns = serializers.IntegerField()
    failed_campaigns = serializers.IntegerField()
    withdrawn_campaigns = serializers.IntegerField()
    
    # Financial stats
    total_raised_wei = serializers.IntegerField()
    total_raised_eth = serializers.DecimalField(max_digits=30, decimal_places=18)
    total_goal_wei = serializers.IntegerField()
    total_goal_eth = serializers.DecimalField(max_digits=30, decimal_places=18)
    
    # Contributor stats
    total_contributions = serializers.IntegerField()
    unique_donors = serializers.IntegerField()
    
    # Success rate
    success_rate = serializers.FloatField()


class TrendingCampaignSerializer(CampaignSerializer):
    """Extended campaign serializer for trending endpoints."""
    
    # Additional computed fields for trending
    recent_contributions_count = serializers.IntegerField(read_only=True, default=0)
    recent_raised_wei = serializers.IntegerField(read_only=True, default=0)
    recent_raised_eth = serializers.SerializerMethodField()
    distance_to_goal_percent = serializers.SerializerMethodField()
    
    class Meta(CampaignSerializer.Meta):
        fields = CampaignSerializer.Meta.fields + [
            'recent_contributions_count',
            'recent_raised_wei',
            'recent_raised_eth',
            'distance_to_goal_percent',
        ]
    
    def get_recent_raised_eth(self, obj):
        recent_wei = getattr(obj, 'recent_raised_wei', 0) or 0
        return str(wei_to_eth(recent_wei))
    
    def get_distance_to_goal_percent(self, obj):
        """How close to goal (100% means at goal, >100% means exceeded)."""
        if obj.goal_wei and obj.goal_wei > 0:
            return round((obj.total_raised_wei / obj.goal_wei) * 100, 2)
        return 0.0


class CampaignLeaderboardSerializer(CampaignSerializer):
    """Campaign serializer for leaderboard with rank."""
    
    rank = serializers.IntegerField(read_only=True)
    contributions_count = serializers.IntegerField(read_only=True, default=0)
    
    class Meta(CampaignSerializer.Meta):
        fields = ['rank'] + CampaignSerializer.Meta.fields + ['contributions_count']


class DonorLeaderboardSerializer(serializers.Serializer):
    """Serializer for donor leaderboard entries."""
    
    rank = serializers.IntegerField()
    donor_address = serializers.SerializerMethodField()
    total_contributed_wei = serializers.IntegerField()
    total_contributed_eth = serializers.SerializerMethodField()
    total_refunded_wei = serializers.IntegerField()
    total_refunded_eth = serializers.SerializerMethodField()
    net_contributed_wei = serializers.IntegerField()
    net_contributed_eth = serializers.SerializerMethodField()
    campaigns_supported = serializers.IntegerField()
    
    def get_donor_address(self, obj):
        return format_address(obj.get('donor_address', ''))
    
    def get_total_contributed_eth(self, obj):
        return str(wei_to_eth(obj.get('total_contributed_wei', 0)))
    
    def get_total_refunded_eth(self, obj):
        return str(wei_to_eth(obj.get('total_refunded_wei', 0)))
    
    def get_net_contributed_eth(self, obj):
        return str(wei_to_eth(obj.get('net_contributed_wei', 0)))


class CreatorStatsSerializer(serializers.Serializer):
    """Serializer for creator statistics."""
    
    creator_address = serializers.SerializerMethodField()
    
    # Campaign stats
    total_campaigns = serializers.IntegerField()
    active_campaigns = serializers.IntegerField()
    successful_campaigns = serializers.IntegerField()
    failed_campaigns = serializers.IntegerField()
    
    # Financial stats
    total_raised_wei = serializers.IntegerField()
    total_raised_eth = serializers.SerializerMethodField()
    total_goal_wei = serializers.IntegerField()
    total_goal_eth = serializers.SerializerMethodField()
    total_withdrawn_wei = serializers.IntegerField()
    total_withdrawn_eth = serializers.SerializerMethodField()
    
    # Success metrics
    success_rate = serializers.FloatField()
    average_progress_percent = serializers.FloatField()
    
    def get_creator_address(self, obj):
        return format_address(obj.get('creator_address', ''))
    
    def get_total_raised_eth(self, obj):
        return str(wei_to_eth(obj.get('total_raised_wei', 0)))
    
    def get_total_goal_eth(self, obj):
        return str(wei_to_eth(obj.get('total_goal_wei', 0)))
    
    def get_total_withdrawn_eth(self, obj):
        return str(wei_to_eth(obj.get('total_withdrawn_wei', 0)))
