from rest_framework import serializers

from applications.models import Application, SavedOpportunity
from opportunities.models import Opportunity
from profiles.models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    completion_percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = Profile
        exclude = ("user", "cv")

    def validate_preferred_categories(self, value):
        allowed = {choice[0] for choice in Profile.CATEGORY_CHOICES}
        if not isinstance(value, list) or any(
            not isinstance(category, str) or category not in allowed for category in value
        ):
            raise serializers.ValidationError("Choose valid opportunity categories.")
        return value


class OpportunitySerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Opportunity
        fields = "__all__"
        read_only_fields = ("date_created", "date_updated", "is_demo")


class SavedOpportunitySerializer(serializers.ModelSerializer):
    opportunity_detail = OpportunitySerializer(source="opportunity", read_only=True)

    class Meta:
        model = SavedOpportunity
        fields = ("id", "opportunity", "opportunity_detail", "created_at")
        read_only_fields = ("created_at",)

    def validate_opportunity(self, opportunity):
        if not opportunity.is_published:
            raise serializers.ValidationError("Only published opportunities can be saved.")
        return opportunity

    def create(self, validated_data):
        saved, _ = SavedOpportunity.objects.get_or_create(**validated_data)
        return saved


class ApplicationSerializer(serializers.ModelSerializer):
    opportunity_detail = OpportunitySerializer(source="opportunity", read_only=True)

    class Meta:
        model = Application
        fields = ("id", "opportunity", "opportunity_detail", "status", "notes", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")

    def validate_opportunity(self, opportunity):
        if not opportunity.is_published:
            raise serializers.ValidationError("Only published opportunities can be tracked.")
        return opportunity

    def create(self, validated_data):
        application, _ = Application.objects.get_or_create(
            user=validated_data["user"],
            opportunity=validated_data["opportunity"],
            defaults={"status": validated_data.get("status", "interested"), "notes": validated_data.get("notes", "")},
        )
        return application
