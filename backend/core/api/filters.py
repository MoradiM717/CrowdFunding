"""Django-filter FilterSet classes for API filtering."""

import django_filters
from django.db import models
from core.models import Campaign, Event


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
            'deadline_after'
        ]


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

