from django.urls import path

from matching import views

app_name = "matching"
urlpatterns = [path("", views.matches, name="list")]
