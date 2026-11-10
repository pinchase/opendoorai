import re
import time
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.rate_limits import allow_sensitive_action


@override_settings(
    EMAIL_ENABLED=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="OpenDoors AI <no-reply@example.test>",
)
class AccountEmailTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_registration_requires_email_verification_and_token_expires(self):
        response = self.client.post(reverse("accounts:register"), {
            "full_name": "Avery Learner",
            "email": "avery@example.test",
            "password1": "StrongPass!4092",
            "password2": "StrongPass!4092",
        })
        self.assertRedirects(response, reverse("accounts:verification-sent"))
        user = get_user_model().objects.get(email="avery@example.test")
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        verification_url = re.search(
            r"http://testserver/accounts/verify/\S+",
            mail.outbox[0].body,
        ).group(0)
        self.assertEqual(self.client.post(reverse("accounts:login"), {
            "username": user.email,
            "password": "StrongPass!4092",
        }).status_code, 200)

        with override_settings(PASSWORD_RESET_TIMEOUT=1):
            time.sleep(1.1)
            response = self.client.get(urlparse(verification_url).path)
        self.assertContains(response, "invalid or expired")
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_valid_verification_activates_and_allows_login(self):
        response = self.client.post(reverse("accounts:register"), {
            "full_name": "Avery Learner",
            "email": "avery@example.test",
            "password1": "StrongPass!4092",
            "password2": "StrongPass!4092",
        })
        self.assertEqual(response.status_code, 302)
        verification_url = re.search(
            r"http://testserver/accounts/verify/\S+",
            mail.outbox[0].body,
        ).group(0)
        response = self.client.get(urlparse(verification_url).path)
        self.assertContains(response, "Your account is ready")
        user = get_user_model().objects.get(email="avery@example.test")
        self.assertTrue(user.is_active)
        self.assertRedirects(
            self.client.post(reverse("accounts:login"), {
                "username": user.email,
                "password": "StrongPass!4092",
            }),
            reverse("accounts:dashboard"),
        )

    def test_password_reset_changes_password_and_uses_generic_response(self):
        user = get_user_model().objects.create_user(
            username="member@example.test",
            email="member@example.test",
            password="OriginalPass!8192",
        )
        response = self.client.post(reverse("accounts:password-reset"), {"email": user.email})
        self.assertRedirects(response, reverse("accounts:password-reset-done"))
        self.assertEqual(len(mail.outbox), 1)
        reset_url = re.search(
            r"http://testserver/accounts/password-reset/\S+",
            mail.outbox[0].body,
        ).group(0)
        response = self.client.get(urlparse(reset_url).path, follow=True)
        self.assertContains(response, "Choose a new password")
        response = self.client.post(response.request["PATH_INFO"], {
            "new_password1": "UpdatedPass!3847",
            "new_password2": "UpdatedPass!3847",
        })
        self.assertRedirects(response, reverse("accounts:password-reset-complete"))
        user.refresh_from_db()
        self.assertTrue(user.check_password("UpdatedPass!3847"))

    def test_password_reset_is_generic_for_unknown_email(self):
        response = self.client.post(reverse("accounts:password-reset"), {
            "email": "unknown@example.test",
        })
        self.assertRedirects(response, reverse("accounts:password-reset-done"))
        self.assertEqual(mail.outbox, [])

    @override_settings(ACCOUNT_RATE_LIMIT_ATTEMPTS=1)
    def test_sensitive_email_actions_are_rate_limited_by_email_and_ip(self):
        self.assertTrue(allow_sensitive_action(
            "password-reset", "member@example.test", "192.0.2.10"
        ))
        self.assertFalse(allow_sensitive_action(
            "password-reset", "member@example.test", "192.0.2.10"
        ))
        self.assertFalse(allow_sensitive_action(
            "password-reset", "another@example.test", "192.0.2.10"
        ))
