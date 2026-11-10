from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from matching.ai import ExplanationServiceError, explain_eligibility
from matching.serializers import OpportunitySerializer
from matching.services import rank_opportunities
from opportunities.models import Opportunity
from profiles.models import Profile


class ExplanationRequestSerializer(serializers.Serializer):
    opportunity_id = serializers.IntegerField(min_value=1)


class MatchListAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OpportunitySerializer

    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        results = rank_opportunities(profile, Opportunity.objects.filter(is_published=True))
        page = self.paginate_queryset(results)
        payload = [
            {
                "opportunity": OpportunitySerializer(result["opportunity"]).data,
                **{key: value for key, value in result.items() if key != "opportunity"},
            }
            for result in (page if page is not None else results)
        ]
        if page is not None:
            return self.get_paginated_response(payload)
        return Response(payload)


class MatchDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        opportunity = get_object_or_404(Opportunity, pk=pk, is_published=True)
        from matching.services import score_opportunity

        return Response({
            "opportunity": OpportunitySerializer(opportunity).data,
            **score_opportunity(profile, opportunity),
        })


class ExplanationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ExplanationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        opportunity = get_object_or_404(
            Opportunity, pk=serializer.validated_data["opportunity_id"], is_published=True
        )
        profile, _ = Profile.objects.get_or_create(user=request.user)
        try:
            return Response(explain_eligibility(profile, opportunity))
        except ExplanationServiceError as error:
            return Response({"detail": str(error)}, status=status.HTTP_502_BAD_GATEWAY)
