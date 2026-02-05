"""API views for blockchain models."""

import logging
import re
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Q, Prefetch
from core.models import Chain, SyncState, Campaign, Contribution, Event, CampaignMetadata
from core.api.serializers import (
    ChainSerializer,
    SyncStateSerializer,
    CampaignSerializer,
    CampaignDetailSerializer,
    CampaignDetailWithMetadataSerializer,
    CampaignWithMetadataSerializer,
    ContributionSerializer,
    ContributionWithCampaignSerializer,
    EventSerializer,
    CampaignMetadataSerializer,
)
from core.api.filters import CampaignFilter, EventFilter
from core.services.metadata_resolver import (
    MetadataResolver,
    CampaignNotFoundError,
    MetadataFetchError,
)

logger = logging.getLogger(__name__)


# Ethereum address validation regex
ETH_ADDRESS_PATTERN = re.compile(r'^0x[a-fA-F0-9]{40}$')


def validate_ethereum_address(address: str) -> bool:
    """Validate Ethereum address format."""
    return bool(ETH_ADDRESS_PATTERN.match(address))


class ChainViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Chain model."""
    
    queryset = Chain.objects.all()
    serializer_class = ChainSerializer
    lookup_field = 'chain_id'


class SyncStateView(APIView):
    """API view for sync state by chain_id."""
    
    def get(self, request, chain_id):
        """Get sync state for a specific chain."""
        sync_state = get_object_or_404(SyncState, chain_id=chain_id)
        serializer = SyncStateSerializer(sync_state)
        return Response(serializer.data)


class CampaignViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Campaign model."""
    
    queryset = Campaign.objects.all().select_related()
    serializer_class = CampaignSerializer
    filterset_class = CampaignFilter
    search_fields = ['address', 'creator_address', 'factory_address', 'cid']
    ordering_fields = ['created_at', 'deadline_ts', 'goal_wei', 'total_raised_wei']
    ordering = ['-created_at']
    lookup_field = 'address'
    
    def get_serializer_class(self):
        """Use appropriate serializer based on action and query params."""
        include_metadata = self.request.query_params.get('include_metadata', '').lower() == 'true'
        
        if self.action == 'retrieve':
            if include_metadata:
                return CampaignDetailWithMetadataSerializer
            return CampaignDetailSerializer
        
        if self.action == 'list' and include_metadata:
            return CampaignWithMetadataSerializer
        
        return CampaignSerializer
    
    def get_queryset(self):
        """Optimize queryset with select_related and prefetch_related."""
        qs = Campaign.objects.all().select_related()
        
        # Prefetch metadata if requested
        include_metadata = self.request.query_params.get('include_metadata', '').lower() == 'true'
        if include_metadata:
            qs = qs.prefetch_related('metadata')
        
        return qs
    
    @action(detail=True, methods=['get'])
    def contributions(self, request, address=None):
        """Get contributions for a campaign."""
        campaign = self.get_object()
        contributions = Contribution.objects.filter(
            campaign_address=campaign
        ).select_related('campaign_address')
        
        # Pagination
        page = self.paginate_queryset(contributions)
        if page is not None:
            serializer = ContributionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ContributionSerializer(contributions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def events(self, request, address=None):
        """Get events for a campaign."""
        campaign = self.get_object()
        events = Event.objects.filter(
            address=campaign
        ).select_related('chain_id', 'address')
        
        # Filtering
        event_name = request.query_params.get('event_name')
        if event_name:
            events = events.filter(event_name__iexact=event_name)
        
        removed = request.query_params.get('removed')
        if removed is not None:
            events = events.filter(removed=removed.lower() == 'true')
        
        # Ordering
        events = events.order_by('-block_number', '-id')
        
        # Pagination
        page = self.paginate_queryset(events)
        if page is not None:
            serializer = EventSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='metadata')
    def metadata(self, request, address=None):
        """Get cached metadata for a campaign.
        
        Returns cached IPFS metadata if available.
        Does not fetch from IPFS - use metadata_refresh for that.
        """
        campaign = self.get_object()
        
        try:
            metadata = CampaignMetadata.objects.select_related('campaign').get(
                campaign=campaign
            )
            serializer = CampaignMetadataSerializer(metadata)
            return Response(serializer.data)
        except CampaignMetadata.DoesNotExist:
            return Response(
                {
                    'detail': 'Metadata not cached for this campaign.',
                    'has_cid': bool(campaign.cid),
                    'cid': campaign.cid,
                },
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'], url_path='metadata/refresh')
    def metadata_refresh(self, request, address=None):
        """Refresh metadata from IPFS.
        
        Fetches metadata from IPFS and updates the cache.
        This endpoint may be rate-limited or require authentication.
        """
        campaign = self.get_object()
        
        if not campaign.cid:
            return Response(
                {'detail': 'Campaign has no IPFS CID.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            resolver = MetadataResolver()
            metadata = resolver.refresh(campaign.address)
            
            if metadata:
                serializer = CampaignMetadataSerializer(metadata)
                return Response(serializer.data)
            
            return Response(
                {'detail': 'Failed to fetch metadata from IPFS.'},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except MetadataFetchError as e:
            logger.error(f"Failed to refresh metadata for {address}: {e}")
            return Response(
                {'detail': f'Failed to fetch metadata: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY
            )


class CreatorCampaignsView(APIView):
    """API view for campaigns by creator address."""
    
    def get(self, request, creator_address):
        """Get all campaigns created by an address."""
        # Validate address format
        if not validate_ethereum_address(creator_address):
            return Response(
                {'error': 'Invalid Ethereum address format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        campaigns = Campaign.objects.filter(
            creator_address__iexact=creator_address
        ).select_related()
        
        # Apply filters from CampaignFilter
        filterset = CampaignFilter(request.query_params, queryset=campaigns)
        campaigns = filterset.qs
        
        # Ordering
        ordering = request.query_params.get('ordering', '-created_at')
        if ordering:
            campaigns = campaigns.order_by(ordering)
        
        # Pagination
        page_size = 50
        page = int(request.query_params.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size
        
        serializer = CampaignSerializer(campaigns[start:end], many=True)
        
        return Response({
            'count': campaigns.count(),
            'next': f"?page={page + 1}" if end < campaigns.count() else None,
            'previous': f"?page={page - 1}" if page > 1 else None,
            'results': serializer.data
        })


class DonorContributionsView(APIView):
    """API view for contributions by donor address."""
    
    def get(self, request, donor_address):
        """Get all contributions made by an address."""
        # Validate address format
        if not validate_ethereum_address(donor_address):
            return Response(
                {'error': 'Invalid Ethereum address format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        contributions = Contribution.objects.filter(
            donor_address__iexact=donor_address
        ).select_related('campaign_address')
        
        # Ordering
        ordering = request.query_params.get('ordering', '-created_at')
        if ordering:
            contributions = contributions.order_by(ordering)
        
        # Pagination
        page_size = 50
        page = int(request.query_params.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size
        
        serializer = ContributionWithCampaignSerializer(contributions[start:end], many=True)
        
        return Response({
            'count': contributions.count(),
            'next': f"?page={page + 1}" if end < contributions.count() else None,
            'previous': f"?page={page - 1}" if page > 1 else None,
            'results': serializer.data
        })


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Event model."""
    
    queryset = Event.objects.all().select_related('chain_id', 'address')
    serializer_class = EventSerializer
    filterset_class = EventFilter
    search_fields = ['tx_hash', 'address__address', 'event_name']
    ordering_fields = ['block_number', 'id', 'created_at']
    ordering = ['-block_number', '-id']

