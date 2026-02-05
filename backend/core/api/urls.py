"""API URL configuration."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from core.api.views import (
    ChainViewSet,
    SyncStateView,
    CampaignViewSet,
    CreatorCampaignsView,
    DonorContributionsView,
    EventViewSet
)
from core.api.stats_views import (
    PlatformStatsView,
    TrendingCampaignsView,
    CampaignLeaderboardView,
    DonorLeaderboardView,
    CreatorStatsView,
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
    
    # Statistics endpoints
    path('stats/platform/', PlatformStatsView.as_view(), name='platform-stats'),
    path('stats/trending/', TrendingCampaignsView.as_view(), name='trending-campaigns'),
    path('stats/leaderboard/campaigns/', CampaignLeaderboardView.as_view(), name='campaign-leaderboard'),
    path('stats/leaderboard/donors/', DonorLeaderboardView.as_view(), name='donor-leaderboard'),
    path('stats/creator/<str:creator_address>/', CreatorStatsView.as_view(), name='creator-stats'),
    
    # JWT Authentication endpoints
    path('auth/token/', TokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token-verify'),
]

