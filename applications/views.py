from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from applications.models import Application, SavedOpportunity
from matching.serializers import ApplicationSerializer, SavedOpportunitySerializer


@login_required
def saved_list(request):
    items = SavedOpportunity.objects.filter(user=request.user).select_related("opportunity")
    return render(request, "applications/saved.html", {"items": items})


@login_required
def application_list(request):
    items = Application.objects.filter(user=request.user).select_related("opportunity")
    return render(request, "applications/list.html", {"items": items, "statuses": Application.STATUS_CHOICES})


@login_required
@require_POST
def update_status(request, application_id):
    application = get_object_or_404(Application, pk=application_id, user=request.user)
    status_value = request.POST.get("status", "")
    if status_value not in dict(Application.STATUS_CHOICES):
        messages.error(request, "Choose a valid application status.")
    else:
        application.status = status_value
        application.save(update_fields=["status", "updated_at"])
        messages.success(request, "Application status updated.")
    return redirect("applications")


class SavedOpportunityAPIView(generics.ListCreateAPIView):
    serializer_class = SavedOpportunitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SavedOpportunity.objects.filter(user=self.request.user).select_related("opportunity")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SavedOpportunityDetailAPIView(generics.DestroyAPIView):
    serializer_class = SavedOpportunitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SavedOpportunity.objects.filter(user=self.request.user)


class ApplicationAPIView(generics.ListCreateAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Application.objects.filter(user=self.request.user).select_related("opportunity")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ApplicationDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Application.objects.filter(user=self.request.user).select_related("opportunity")
