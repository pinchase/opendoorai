import io
import json
import urllib.error
from unittest.mock import patch
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from matching.ai import explain_eligibility
from matching.services import rank_opportunities, score_opportunity
from opportunities.models import Opportunity
from profiles.models import Profile


@override_settings(
    AI_ENABLED=True,
    AI_PROVIDER="openrouter",
    AI_API_KEY="test-secret-not-for-logs",
    AI_MODEL="test/model",
    AI_BASE_URL="https://openrouter.ai/api/v1",
    AI_TIMEOUT_SECONDS=30,
    AI_SITE_URL="https://opendoors.example",
    AI_SITE_NAME="OpenDoors AI Tests",
)
class MatchingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="learner@example.test",
            email="learner@example.test",
            password="SecurePass!5840",
        )
        self.profile = Profile.objects.create(
            user=self.user,
            full_name="Learner",
            education_level="undergraduate",
            field_of_study="Computer Science",
            skills="Python, research, writing",
            experience_level="beginner",
            preferred_location="Remote",
            preferred_categories=["internship", "scholarship"],
        )
        self.opportunity = Opportunity.objects.create(
            title="Data Internship",
            organization="Demo Data",
            description="An internship.",
            category="internship",
            location="Remote",
            required_skills=["python", "research"],
            required_education="undergraduate",
            required_field="computer science",
            required_experience="beginner",
            is_published=True,
        )

    def test_scores_are_deterministic_explainable_and_bounded(self):
        first = score_opportunity(self.profile, self.opportunity)
        second = score_opportunity(self.profile, self.opportunity)
        self.assertEqual(first, second)
        self.assertGreaterEqual(first["score"], 0)
        self.assertLessEqual(first["score"], 100)
        self.assertEqual(first["score"], 100)
        self.assertTrue(first["reasons"])
        self.assertIn("python", " ".join(first["relevant_qualifications"]))

    def test_missing_profile_information_is_unknown_not_a_mismatch(self):
        self.profile.skills = ""
        self.profile.education_level = ""
        self.profile.save()
        result = score_opportunity(self.profile, self.opportunity)
        self.assertNotIn("skills", result["dimension_scores"])
        self.assertNotIn("education", result["dimension_scores"])
        self.assertTrue(any("skills" in item.lower() for item in result["missing_information"]))
        self.assertEqual(result["eligibility_status"], "review_requirements")

    def test_explicit_mandatory_failure_is_reported_as_not_eligible(self):
        self.opportunity.mandatory_requirements = [{
            "profile_field": "education_level",
            "operator": "in",
            "values": ["postgraduate"],
            "label": "postgraduate study",
        }]
        self.opportunity.save()
        result = score_opportunity(self.profile, self.opportunity)
        self.assertEqual(result["eligibility_status"], "not_eligible")
        self.assertTrue(any("Mandatory requirement" in item for item in result["eligibility_concerns"]))

    def test_unknown_mandatory_value_requests_confirmation(self):
        self.profile.education_level = ""
        self.profile.save()
        self.opportunity.mandatory_requirements = [{
            "profile_field": "education_level",
            "operator": "in",
            "values": ["undergraduate"],
        }]
        self.opportunity.save()
        result = score_opportunity(self.profile, self.opportunity)
        self.assertEqual(result["eligibility_status"], "review_requirements")
        self.assertTrue(any("Confirm education level" in item for item in result["missing_information"]))

    def test_malformed_mandatory_rules_are_unknown_not_crashes_or_failures(self):
        self.opportunity.mandatory_requirements = {"unexpected": "shape"}
        self.opportunity.save()
        result = score_opportunity(self.profile, self.opportunity)
        self.assertEqual(result["eligibility_status"], "review_requirements")
        self.assertTrue(any("could not be checked" in item for item in result["missing_information"]))

    def test_deadline_is_a_concern_not_an_explicit_eligibility_failure(self):
        self.opportunity.application_deadline = date.today() - timedelta(days=1)
        self.opportunity.save()
        result = score_opportunity(self.profile, self.opportunity)
        self.assertEqual(result["eligibility_status"], "review_requirements")
        self.assertTrue(any("deadline has passed" in item for item in result["eligibility_concerns"]))

    def test_ranked_results_have_deterministic_order(self):
        results = rank_opportunities(self.profile, [self.opportunity])
        self.assertEqual(results[0]["opportunity"], self.opportunity)
        self.assertEqual(results[0]["score"], 100)

    def test_disabled_ai_returns_truthful_rule_based_explanation(self):
        with override_settings(AI_ENABLED=False):
            explanation = explain_eligibility(self.profile, self.opportunity)
        self.assertEqual(explanation["source"], "rule_based")
        self.assertIn("not a guarantee", explanation["summary"])
        self.assertNotIn("ai_explanation", explanation)

    def test_openrouter_request_auth_timeout_headers_and_response(self):
        response_body = json.dumps({
            "choices": [{"message": {"content": "Review the listed requirements carefully."}}]
        }).encode()
        with patch("matching.ai.urllib.request.urlopen", return_value=io.BytesIO(response_body)) as urlopen:
            explanation = explain_eligibility(self.profile, self.opportunity)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-secret-not-for-logs")
        self.assertEqual(request.get_header("Http-referer"), "https://opendoors.example")
        self.assertEqual(request.get_header("X-title"), "OpenDoors AI Tests")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 30)
        self.assertEqual(explanation["source"], "ai_assisted")
        self.assertEqual(explanation["ai_explanation"], "Review the listed requirements carefully.")

    def test_openrouter_errors_fall_back_without_exposing_credentials(self):
        for code, expected in (
            (401, "credentials are invalid"),
            (429, "rate limit or account quota"),
            (404, "model or endpoint"),
            (503, "temporarily unavailable"),
        ):
            error = urllib.error.HTTPError(
                "https://openrouter.ai/api/v1/chat/completions", code, "ignored", {}, None
            )
            with self.subTest(code=code), patch(
                "matching.ai.urllib.request.urlopen", side_effect=error
            ):
                explanation = explain_eligibility(self.profile, self.opportunity)
                self.assertEqual(explanation["source"], "rule_based_fallback")
                self.assertIn(expected, explanation["provider_warning"])
                self.assertNotIn("test-secret-not-for-logs", str(explanation))
                self.assertNotIn("ignored", str(explanation))

    def test_openrouter_timeout_and_malformed_response_fall_back(self):
        with patch("matching.ai.urllib.request.urlopen", side_effect=TimeoutError):
            timeout_result = explain_eligibility(self.profile, self.opportunity)
        self.assertEqual(timeout_result["source"], "rule_based_fallback")
        self.assertIn("timed out", timeout_result["provider_warning"])
        with patch("matching.ai.urllib.request.urlopen", return_value=io.BytesIO(b"not-json")):
            invalid_result = explain_eligibility(self.profile, self.opportunity)
        self.assertEqual(invalid_result["source"], "rule_based_fallback")
        self.assertIn("invalid response", invalid_result["provider_warning"])

    def test_explanation_api_validates_input_and_returns_rule_based_result(self):
        with override_settings(AI_ENABLED=False):
            self.client.force_login(self.user)
            invalid = self.client.post(
                "/api/matches/explanations/",
                {"opportunity_id": "not-an-id"},
                content_type="application/json",
            )
            self.assertEqual(invalid.status_code, 400)
            response = self.client.post(
                "/api/matches/explanations/",
                {"opportunity_id": self.opportunity.pk},
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "rule_based")
