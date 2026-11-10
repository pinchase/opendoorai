from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase


class HealthCheckTests(TestCase):
    def test_health_endpoint_checks_database(self):
        response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_endpoint_does_not_expose_database_errors(self):
        with patch("config.urls.connection.ensure_connection", side_effect=OperationalError("private detail")):
            response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertNotContains(response, "private detail", status_code=503)
