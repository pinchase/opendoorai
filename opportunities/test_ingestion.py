import io
import json
import urllib.error
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from opportunities.ingestion import FeedError, fetch_feed, import_records, load_configured_feeds, normalize_record
from opportunities.models import Opportunity


FEED = {
    "id": "public-demo",
    "name": "Trusted Public Dataset",
    "url": "https://opportunities.example.test/feed.json",
    "host": "opportunities.example.test",
}


def valid_record(**updates):
    record = {
        "id": "provider-123",
        "title": "Community Data Fellowship",
        "organization": "Community Learning Network",
        "description": "A verified public listing from the configured data provider.",
        "category": "fellowship",
        "location": "Remote",
        "eligibility_requirements": "Check the provider's source for current details.",
        "required_skills": ["research", "communication"],
        "required_education": "undergraduate",
        "required_experience": "beginner",
        "application_deadline": (date.today() + timedelta(days=30)).isoformat(),
        "application_url": "https://apply.example.test/fellowship",
        "source_url": "https://opportunities.example.test/listings/123",
    }
    return {**record, **updates}


@override_settings(
    OPPORTUNITY_FEEDS_JSON=(
        '[{"id":"public-demo","name":"Trusted Public Dataset",'
        '"url":"https://opportunities.example.test/feed.json"}]'
    ),
    TRUSTED_OPPORTUNITY_SOURCE_HOSTS={"opportunities.example.test"},
)
class OpportunityIngestionTests(TestCase):
    def test_feed_configuration_requires_exact_trusted_https_hosts(self):
        self.assertIn("public-demo", load_configured_feeds())
        with override_settings(TRUSTED_OPPORTUNITY_SOURCE_HOSTS={"other.example.test"}):
            with self.assertRaisesMessage(FeedError, "not in TRUSTED_OPPORTUNITY_SOURCE_HOSTS"):
                load_configured_feeds()
        with override_settings(
            OPPORTUNITY_FEEDS_JSON=(
                '[{"id":"bad","name":"Bad source","url":"http://opportunities.example.test/feed.json"}]'
            )
        ):
            with self.assertRaisesMessage(FeedError, "HTTPS URL"):
                load_configured_feeds()

    def test_fetch_checks_public_dns_and_handles_unavailable_sources(self):
        feed = load_configured_feeds()["public-demo"]
        private_dns = [(None, None, None, None, ("127.0.0.1", 443))]
        with patch("opportunities.ingestion.socket.getaddrinfo", return_value=private_dns):
            with self.assertRaisesMessage(FeedError, "public IP addresses"):
                fetch_feed(feed)

        with patch("opportunities.ingestion._validate_public_host"), patch(
            "opportunities.ingestion.urllib.request.build_opener",
        ) as build_opener:
            build_opener.return_value.open.side_effect = urllib.error.HTTPError(
                feed["url"], 503, "not logged", {}, None
            )
            with self.assertRaisesMessage(FeedError, "unavailable"):
                fetch_feed(feed)

    def test_fetch_parses_bounded_json_feed(self):
        feed = load_configured_feeds()["public-demo"]
        payload = json.dumps({"opportunities": [valid_record()]}).encode()
        response = MagicMock()
        response.headers = {"Content-Type": "application/json; charset=utf-8"}
        response.read.return_value = payload
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        with patch("opportunities.ingestion._validate_public_host"), patch(
            "opportunities.ingestion.urllib.request.build_opener"
        ) as build_opener:
            build_opener.return_value.open.return_value = response
            records = fetch_feed(feed)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["id"], "provider-123")
        self.assertEqual(response.read.call_args.args[0], 2_000_001)

    def test_normalization_rejects_bad_deadlines_and_urls(self):
        today = date.today()
        with self.assertRaisesMessage(ValidationError, "deadline has passed"):
            normalize_record(
                valid_record(application_deadline=(today - timedelta(days=1)).isoformat()),
                FEED,
                today=today,
            )
        with self.assertRaisesMessage(ValidationError, "valid HTTPS URL"):
            normalize_record(valid_record(application_url="javascript:alert(1)"), FEED, today=today)
        with self.assertRaisesMessage(ValidationError, "YYYY-MM-DD"):
            normalize_record(valid_record(application_deadline="2026-2-3"), FEED, today=today)

    def test_import_verifies_source_records_but_defaults_to_unpublished(self):
        now_before = timezone.now()
        result = import_records([valid_record()], FEED)
        opportunity = Opportunity.objects.get(source_identifier="provider-123")
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["skipped"], 0)
        self.assertFalse(opportunity.is_published)
        self.assertTrue(opportunity.is_verified)
        self.assertTrue(opportunity.source_managed)
        self.assertFalse(opportunity.is_demo)
        self.assertEqual(opportunity.source, FEED["name"])
        self.assertEqual(opportunity.source_url, valid_record()["source_url"])
        self.assertGreaterEqual(opportunity.source_collected_at, now_before)

    def test_import_is_idempotent_and_updates_only_source_managed_records(self):
        first = import_records([valid_record()], FEED)
        opportunity = Opportunity.objects.get(source_identifier="provider-123")
        original_created = opportunity.date_created
        second = import_records([valid_record(description="Updated description.")], FEED)
        opportunity.refresh_from_db()
        self.assertEqual(first["created"], 1)
        self.assertEqual(second["updated"], 1)
        self.assertEqual(Opportunity.objects.filter(source_identifier="provider-123").count(), 1)
        self.assertEqual(opportunity.description, "Updated description.")
        self.assertEqual(opportunity.date_created, original_created)

    def test_import_skips_manual_duplicates_without_overwriting_them(self):
        curated = Opportunity.objects.create(
            title=valid_record()["title"],
            organization=valid_record()["organization"],
            description="Curated listing that must not be overwritten.",
            category="fellowship",
            is_published=True,
        )
        result = import_records([valid_record()], FEED)
        curated.refresh_from_db()
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(curated.description, "Curated listing that must not be overwritten.")
        self.assertFalse(Opportunity.objects.filter(source_managed=True).exists())

    def test_dry_run_does_not_write_and_detects_existing_records(self):
        first = import_records([valid_record()], FEED, dry_run=True)
        self.assertEqual(first["created"], 1)
        self.assertFalse(Opportunity.objects.exists())
        import_records([valid_record()], FEED)
        duplicate = import_records([valid_record()], FEED, dry_run=True)
        self.assertEqual(duplicate["updated"], 1)
        self.assertEqual(Opportunity.objects.count(), 1)

    def test_publish_is_explicit_and_expired_feed_item_unpublishes_import(self):
        result = import_records([valid_record()], FEED, publish=True)
        opportunity = Opportunity.objects.get(source_identifier="provider-123")
        self.assertEqual(result["created"], 1)
        self.assertTrue(opportunity.is_published)
        import_records(
            [valid_record(application_deadline=(date.today() - timedelta(days=1)).isoformat())],
            FEED,
        )
        opportunity.refresh_from_db()
        self.assertFalse(opportunity.is_published)
