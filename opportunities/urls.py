from django.urls import path

from opportunities import views

app_name = "opportunities"
urlpatterns = [
    path("", views.opportunity_list, name="list"),
    path("<int:pk>/", views.opportunity_detail, name="detail"),
    path("<int:pk>/save/", views.toggle_saved, name="toggle-saved"),
    path("<int:pk>/track/", views.track_application, name="track"),
]
