"""Django-filter FilterSet classes for API filtering."""

import django_filters
from django.db import models
from django.db.models import Q
from core.models import Campaign, Event, CampaignMetadata


class CampaignFilter(django_filters.FilterSet):
    """FilterSet for Campaign model."""
    
    # Status filter
    status = django_filters.ChoiceFilter(choices=Campaign.STATUS_CHOICES)
    
    # Address filters
    creator_address = django_filters.CharFilter(
        field_name='creator_address',
        lookup_expr='iexact'  # Case-insensitive
    )
    factory_address = django_filters.CharFilter(
        field_name='factory_address',
        lookup_expr='iexact'
    )
    
    # Goal filters (range)
    min_goal = django_filters.NumberFilter(field_name='goal_wei', lookup_expr='gte')
    max_goal = django_filters.NumberFilter(field_name='goal_wei', lookup_expr='lte')
    
    # Raised filters
    min_raised = django_filters.NumberFilter(field_name='total_raised_wei', lookup_expr='gte')
    
    # Withdrawn filter
    has_withdrawn = django_filters.BooleanFilter(field_name='withdrawn')
    
    # Deadline filters
    deadline_before = django_filters.NumberFilter(field_name='deadline_ts', lookup_expr='lte')
    deadline_after = django_filters.NumberFilter(field_name='deadline_ts', lookup_expr='gte')
    
    # Metadata-based filters
    category = django_filters.ChoiceFilter(
        field_name='metadata__category',
        choices=CampaignMetadata.CATEGORY_CHOICES,
        method='filter_by_category'
    )
    
    # Full-text search on metadata name and description
    q = django_filters.CharFilter(method='filter_search')
    
    # Has metadata filter
    has_metadata = django_filters.BooleanFilter(method='filter_has_metadata')
    
    class Meta:
        model = Campaign
        fields = [
            'status',
            'creator_address',
            'factory_address',
            'min_goal',
            'max_goal',
            'min_raised',
            'has_withdrawn',
            'deadline_before',
            'deadline_after',
            'category',
            'q',
            'has_metadata',
        ]
    
    def filter_by_category(self, queryset, name, value):
        """Filter campaigns by metadata category."""
        if not value:
            return queryset
        return queryset.filter(metadata__category__iexact=value)
    
    def filter_search(self, queryset, name, value):
        """Full-text search across campaign fields and metadata.
        
        Searches:
        - Campaign address
        - Campaign CID
        - Metadata name (case-insensitive)
        - Metadata description (case-insensitive)
        - Metadata short_description (case-insensitive)
        - Creator name (case-insensitive)
        """
        if not value:
            return queryset
        
        search_query = Q(address__icontains=value) | Q(cid__icontains=value)
        
        # Search in metadata fields
        search_query |= Q(metadata__name__icontains=value)
        search_query |= Q(metadata__description__icontains=value)
        search_query |= Q(metadata__short_description__icontains=value)
        search_query |= Q(metadata__creator_name__icontains=value)
        search_query |= Q(metadata__location__icontains=value)
        
        return queryset.filter(search_query).distinct()
    
    def filter_has_metadata(self, queryset, name, value):
        """Filter campaigns that have/don't have cached metadata."""
        if value is None:
            return queryset
        if value:
            return queryset.filter(metadata__isnull=False)
        return queryset.filter(metadata__isnull=True)


class EventFilter(django_filters.FilterSet):
    """FilterSet for Event model."""
    
    # Chain filter
    chain_id = django_filters.NumberFilter(field_name='chain_id')
    
    # Event name filter
    event_name = django_filters.CharFilter(field_name='event_name', lookup_expr='iexact')
    
    # Address filter (campaign address)
    address = django_filters.CharFilter(
        field_name='address__address',
        lookup_expr='iexact'
    )
    
    # Block number filters
    block_number_gte = django_filters.NumberFilter(field_name='block_number', lookup_expr='gte')
    block_number_lte = django_filters.NumberFilter(field_name='block_number', lookup_expr='lte')
    
    # Transaction hash filter
    tx_hash = django_filters.CharFilter(field_name='tx_hash', lookup_expr='iexact')
    
    # Removed filter
    removed = django_filters.BooleanFilter(field_name='removed')
    
    class Meta:
        model = Event
        fields = [
            'chain_id',
            'event_name',
            'address',
            'block_number_gte',
            'block_number_lte',
            'tx_hash',
            'removed'
        ]

