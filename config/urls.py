from django.contrib import admin
from django.urls import include, path
from rest_framework.schemas import get_schema_view

from accounts import views as account_views
from applications import views as application_views
from matching import api as matching_api
from opportunities import api as opportunity_api
from profiles import api as profile_api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("opportunities/", include("opportunities.urls")),
    path("matches/", include("matching.urls")),
    path("saved/", application_views.saved_list, name="saved"),
    path("applications/", application_views.application_list, name="applications"),
    path("applications/<int:application_id>/status/", application_views.update_status, name="application-status"),
    path("api/auth/register/", account_views.RegisterAPIView.as_view(), name="api-register"),
    path("api/auth/login/", account_views.LoginAPIView.as_view(), name="api-login"),
    path("api/auth/logout/", account_views.LogoutAPIView.as_view(), name="api-logout"),
    path("api/profile/", profile_api.ProfileAPIView.as_view(), name="api-profile"),
    path("api/profile/update/", profile_api.ProfileAPIView.as_view(), name="api-profile-update"),
    path("api/opportunities/", opportunity_api.OpportunityListAPIView.as_view(), name="api-opportunities"),
    path("api/opportunities/<int:pk>/", opportunity_api.OpportunityDetailAPIView.as_view(), name="api-opportunity-detail"),
    path("api/matches/", matching_api.MatchListAPIView.as_view(), name="api-matches"),
    path("api/matches/<int:pk>/", matching_api.MatchDetailAPIView.as_view(), name="api-match-detail"),
    path("api/matches/explanations/", matching_api.ExplanationAPIView.as_view(), name="api-explanation"),
    path("api/saved-opportunities/", application_views.SavedOpportunityAPIView.as_view(), name="api-saved"),
    path("api/saved-opportunities/<int:pk>/", application_views.SavedOpportunityDetailAPIView.as_view(), name="api-saved-detail"),
    path("api/applications/", application_views.ApplicationAPIView.as_view(), name="api-applications"),
    path("api/applications/<int:pk>/", application_views.ApplicationDetailAPIView.as_view(), name="api-application-detail"),
    path("api/schema/", get_schema_view(title="OpenDoors AI API", version="1.0.0"), name="api-schema"),
]
