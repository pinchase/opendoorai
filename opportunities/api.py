from django.db.models import Q
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import AllowAny

from matching.serializers import OpportunitySerializer
from opportunities.models import Opportunity


class OpportunityListAPIView(generics.ListAPIView):
    serializer_class = OpportunitySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Opportunity.objects.filter(is_published=True)
        search = self.request.query_params.get("q", "").strip()
        category = self.request.query_params.get("category", "").strip()
        location = self.request.query_params.get("location", "").strip()
        ordering = self.request.query_params.get("ordering", "")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(organization__icontains=search)
                | Q(description__icontains=search)
            )
        if category:
            queryset = queryset.filter(category=category)
        if location:
            queryset = queryset.filter(location__icontains=location)
        if ordering == "deadline":
            queryset = queryset.order_by(F("application_deadline").asc(nulls_last=True), "-date_created")
        return queryset


class OpportunityDetailAPIView(generics.RetrieveAPIView):
    serializer_class = OpportunitySerializer
    permission_classes = [AllowAny]
    queryset = Opportunity.objects.filter(is_published=True)
