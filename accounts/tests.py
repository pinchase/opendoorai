from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from profiles.models import Profile


class AuthenticationAndProfileTests(TestCase):
    def test_registration_creates_user_and_profile_and_authenticates(self):
        response = self.client.post(reverse("accounts:register"), {
            "full_name": "Avery Learner",
            "email": "avery@example.test",
            "password1": "StrongPass!4092",
            "password2": "StrongPass!4092",
        })
        self.assertRedirects(response, reverse("accounts:dashboard"))
        user = get_user_model().objects.get(email="avery@example.test")
        self.assertTrue(user.check_password("StrongPass!4092"))
        self.assertEqual(user.profile.full_name, "Avery Learner")

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post(reverse("accounts:register"), {
            "full_name": "Avery",
            "email": "avery@example.test",
            "password1": "StrongPass!4092",
            "password2": "OtherPass!4092",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(email="avery@example.test").exists())

    def test_protected_pages_require_authentication(self):
        for url in (reverse("accounts:dashboard"), reverse("accounts:profile"), reverse("saved"), reverse("applications")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)

    def test_login_and_profile_update(self):
        user = get_user_model().objects.create_user(
            username="member@example.test",
            email="member@example.test",
            password="SecurePass!5840",
        )
        Profile.objects.create(user=user, full_name="Before")
        response = self.client.post(reverse("accounts:login"), {
            "username": "member@example.test",
            "password": "SecurePass!5840",
        })
        self.assertRedirects(response, reverse("accounts:dashboard"))
        response = self.client.post(reverse("accounts:profile"), {
            "full_name": "After",
            "education_level": "undergraduate",
            "institution": "Example University",
            "field_of_study": "Computer science",
            "graduation_year": "2027",
            "skills": "Python, research",
            "interests": "Accessible technology",
            "career_goals": "Build useful tools",
            "preferred_categories": ["internship", "scholarship"],
            "preferred_location": "Remote",
            "experience_level": "beginner",
        })
        self.assertRedirects(response, reverse("accounts:profile"))
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.full_name, "After")
        self.assertEqual(user.profile.preferred_categories, ["internship", "scholarship"])

    def test_profile_api_is_private_and_scoped_to_logged_in_user(self):
        user = get_user_model().objects.create_user(
            username="member@example.test",
            email="member@example.test",
            password="SecurePass!5840",
        )
        Profile.objects.create(user=user, full_name="Member")
        self.assertIn(self.client.get("/api/profile/").status_code, (401, 403))
        self.client.force_login(user)
        response = self.client.patch(
            "/api/profile/",
            {"full_name": "Updated"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.full_name, "Updated")
