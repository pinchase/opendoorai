from django.test import TestCase
from django.urls import reverse
from datetime import date, timedelta

from opportunities.models import Opportunity


class OpportunityDiscoveryTests(TestCase):
    def setUp(self):
        self.python = Opportunity.objects.create(
            title="Python Training",
            organization="Demo Data",
            description="Learn Python foundations.",
            category="training",
            location="Remote",
            is_published=True,
            is_demo=True,
        )
        Opportunity.objects.create(
            title="Hidden Internship",
            organization="Demo Data",
            description="A hidden record.",
            category="internship",
            is_published=False,
        )
        Opportunity.objects.create(
            title="Local Research Fellowship",
            organization="Demo Data",
            description="A research opportunity.",
            category="fellowship",
            location="Nairobi",
            is_published=True,
        )

    def test_listing_shows_published_opportunities_only(self):
        response = self.client.get(reverse("opportunities:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Training")
        self.assertNotContains(response, "Hidden Internship")

    def test_listing_filters_by_search_category_location_and_deadline_order(self):
        response = self.client.get(reverse("opportunities:list"), {
            "q": "Python",
            "category": "training",
            "location": "remote",
        })
        self.assertEqual(len(response.context["page"].object_list), 1)
        self.assertEqual(response.context["page"].object_list[0], self.python)

    def test_public_api_supports_filters_and_pagination(self):
        response = self.client.get("/api/opportunities/?category=training")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.python.pk)

    def test_detail_and_unpublished_protection(self):
        self.assertEqual(self.client.get(reverse("opportunities:detail", args=[self.python.pk])).status_code, 200)
        hidden = Opportunity.objects.get(title="Hidden Internship")
        self.assertEqual(self.client.get(reverse("opportunities:detail", args=[hidden.pk])).status_code, 404)

    def test_deadline_order_puts_undated_records_last(self):
        soon = Opportunity.objects.create(
            title="Soon",
            organization="Demo Data",
            description="Deadline example.",
            category="scholarship",
            application_deadline=date.today() + timedelta(days=2),
            is_published=True,
        )
        later = Opportunity.objects.create(
            title="Later",
            organization="Demo Data",
            description="Deadline example.",
            category="scholarship",
            application_deadline=date.today() + timedelta(days=10),
            is_published=True,
        )
        response = self.client.get(reverse("opportunities:list"), {"sort": "deadline"})
        ordered = list(response.context["page"].object_list)
        self.assertEqual(ordered[:2], [soon, later])
        self.assertTrue(all(item.application_deadline is None for item in ordered[2:]))
