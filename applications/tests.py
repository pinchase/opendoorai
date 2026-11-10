from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from applications.models import Application, SavedOpportunity
from opportunities.models import Opportunity


class SavedAndApplicationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="first@example.test",
            email="first@example.test",
            password="SecurePass!5840",
        )
        self.other = user_model.objects.create_user(
            username="second@example.test",
            email="second@example.test",
            password="SecurePass!5840",
        )
        self.opportunity = Opportunity.objects.create(
            title="Sample Fellowship",
            organization="Demo Data",
            description="Example.",
            category="fellowship",
            is_published=True,
        )
        self.client.force_login(self.user)

    def test_save_and_remove_opportunity(self):
        response = self.client.post(reverse("opportunities:toggle-saved", args=[self.opportunity.pk]))
        self.assertRedirects(response, reverse("opportunities:detail", args=[self.opportunity.pk]))
        self.assertTrue(SavedOpportunity.objects.filter(user=self.user, opportunity=self.opportunity).exists())
        self.client.post(reverse("opportunities:toggle-saved", args=[self.opportunity.pk]))
        self.assertFalse(SavedOpportunity.objects.filter(user=self.user, opportunity=self.opportunity).exists())

    def test_application_tracking_and_status_validation(self):
        self.client.post(reverse("opportunities:track", args=[self.opportunity.pk]))
        application = Application.objects.get(user=self.user, opportunity=self.opportunity)
        self.assertEqual(application.status, "interested")
        response = self.client.post(reverse("application-status", args=[application.pk]), {"status": "applied"})
        self.assertRedirects(response, reverse("applications"))
        application.refresh_from_db()
        self.assertEqual(application.status, "applied")
        self.client.post(reverse("application-status", args=[application.pk]), {"status": "unknown"})
        application.refresh_from_db()
        self.assertEqual(application.status, "applied")

    def test_user_cannot_access_another_users_application(self):
        application = Application.objects.create(user=self.other, opportunity=self.opportunity)
        response = self.client.post(reverse("application-status", args=[application.pk]), {"status": "applied"})
        self.assertEqual(response.status_code, 404)
        application.refresh_from_db()
        self.assertEqual(application.status, "interested")

    def test_user_cannot_delete_another_users_saved_record_through_api(self):
        saved = SavedOpportunity.objects.create(user=self.other, opportunity=self.opportunity)
        response = self.client.delete(f"/api/saved-opportunities/{saved.pk}/")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(SavedOpportunity.objects.filter(pk=saved.pk).exists())

    def test_saved_and_application_apis_are_user_scoped(self):
        self.client.post("/api/saved-opportunities/", {"opportunity": self.opportunity.pk})
        self.client.post("/api/applications/", {"opportunity": self.opportunity.pk})
        self.assertTrue(SavedOpportunity.objects.filter(user=self.user).exists())
        self.assertTrue(Application.objects.filter(user=self.user).exists())
        self.assertFalse(SavedOpportunity.objects.filter(user=self.other).exists())
        self.assertFalse(Application.objects.filter(user=self.other).exists())
