"""API URL configuration."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.api.views import (
    ChainViewSet,
    SyncStateView,
    CampaignViewSet,
    CreatorCampaignsView,
    DonorContributionsView,
    EventViewSet
)

router = DefaultRouter()
router.register(r'chains', ChainViewSet, basename='chain')
router.register(r'campaigns', CampaignViewSet, basename='campaign')
router.register(r'events', EventViewSet, basename='event')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Custom endpoints
    path('chains/<int:chain_id>/sync-state/', SyncStateView.as_view(), name='chain-sync-state'),
    path('creators/<str:creator_address>/campaigns/', CreatorCampaignsView.as_view(), name='creator-campaigns'),
    path('donors/<str:donor_address>/contributions/', DonorContributionsView.as_view(), name='donor-contributions'),
]

