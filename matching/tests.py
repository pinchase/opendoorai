from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from matching.ai import explain_eligibility
from matching.services import rank_opportunities, score_opportunity
from opportunities.models import Opportunity
from profiles.models import Profile


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
        explanation = explain_eligibility(self.profile, self.opportunity)
        self.assertEqual(explanation["source"], "rule_based")
        self.assertIn("not a guarantee", explanation["summary"])
        self.assertNotIn("ai_explanation", explanation)
