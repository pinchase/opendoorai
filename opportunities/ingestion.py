import ipaddress
import json
import socket
import urllib.error
import urllib.request
from datetime import date
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from opportunities.models import Opportunity

MAX_FEED_BYTES = 2_000_000
MAX_FEED_RECORDS = 500
MAX_FEED_SECONDS = 15
APPLICATION_URL_VALIDATOR = URLValidator(schemes=["https"])
EDUCATION_LEVELS = {value for value, _ in Opportunity._meta.get_field("required_education").choices}
EXPERIENCE_LEVELS = {value for value, _ in Opportunity.EXPERIENCE_CHOICES}


class FeedError(Exception):
    pass


def load_configured_feeds():
    try:
        feeds = json.loads(settings.OPPORTUNITY_FEEDS_JSON)
    except json.JSONDecodeError as error:
        raise FeedError("OPPORTUNITY_FEEDS_JSON must be valid JSON.") from error
    if not isinstance(feeds, list):
        raise FeedError("OPPORTUNITY_FEEDS_JSON must be a JSON array.")
    result = {}
    for feed in feeds:
        if not isinstance(feed, dict):
            raise FeedError("Each configured feed must be a JSON object.")
        feed_id, name, url = feed.get("id"), feed.get("name"), feed.get("url")
        if not all(isinstance(value, str) and value.strip() for value in (feed_id, name, url)):
            raise FeedError("Each feed requires non-empty string id, name, and url fields.")
        if feed_id in result:
            raise FeedError("Configured feed ids must be unique.")
        parsed = urlparse(url)
        try:
            port = parsed.port
        except ValueError as error:
            raise FeedError(f"Feed {feed_id!r} URL contains an invalid port.") from error
        hostname = (parsed.hostname or "").casefold()
        if (
            parsed.scheme != "https"
            or not hostname
            or parsed.username
            or parsed.password
            or port not in (None, 443)
        ):
            raise FeedError(f"Feed {feed_id!r} must use a credential-free HTTPS URL on port 443.")
        if hostname not in settings.TRUSTED_OPPORTUNITY_SOURCE_HOSTS:
            raise FeedError(f"Feed {feed_id!r} host is not in TRUSTED_OPPORTUNITY_SOURCE_HOSTS.")
        result[feed_id] = {"id": feed_id, "name": name.strip(), "url": url, "host": hostname}
    return result


def _validate_public_host(host):
    try:
        addresses = {
            entry[4][0].split("%", 1)[0]
            for entry in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        }
    except OSError as error:
        raise FeedError("The configured opportunity source could not be resolved.") from error
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise FeedError("The configured opportunity source must resolve only to public IP addresses.")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def fetch_feed(feed):
    _validate_public_host(feed["host"])
    request = urllib.request.Request(
        feed["url"],
        headers={"Accept": "application/json", "User-Agent": "OpenDoorsAI-OpportunityImporter/1.0"},
    )
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=MAX_FEED_SECONDS) as response:
            content_type = response.headers.get("Content-Type", "").casefold()
            if content_type and "json" not in content_type:
                raise FeedError("The configured opportunity source did not return JSON.")
            payload = response.read(MAX_FEED_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise FeedError("The configured opportunity source is unavailable.") from error
    if len(payload) > MAX_FEED_BYTES:
        raise FeedError("The opportunity source feed is larger than the allowed 2 MB.")
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FeedError("The opportunity source returned invalid JSON.") from error
    if not isinstance(data, dict) or not isinstance(data.get("opportunities"), list):
        raise FeedError("The feed must contain an 'opportunities' JSON array.")
    records = data["opportunities"]
    if len(records) > MAX_FEED_RECORDS:
        raise FeedError(f"The feed exceeds the {MAX_FEED_RECORDS}-record limit.")
    return records


def normalize_record(record, feed, today=None):
    if not isinstance(record, dict):
        raise ValidationError("Record must be a JSON object.")
    external_id = record.get("id")
    if not isinstance(external_id, (str, int)) or not str(external_id).strip():
        raise ValidationError("Record requires a source id.")
    external_id = str(external_id).strip()
    if len(external_id) > 200:
        raise ValidationError("Source id exceeds 200 characters.")

    required_text = {}
    limits = {"title": 180, "organization": 180, "description": 50000}
    for field, max_length in limits.items():
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"Record requires a non-empty {field}.")
        if max_length and len(value.strip()) > max_length:
            raise ValidationError(f"{field.title()} exceeds {max_length} characters.")
        required_text[field] = value.strip()
    category = record.get("category")
    if not isinstance(category, str) or category not in {value for value, _ in Opportunity.CATEGORY_CHOICES}:
        raise ValidationError("Record category is not supported.")

    skills = record.get("required_skills", [])
    if not isinstance(skills, list) or any(
        not isinstance(skill, str) or not skill.strip() or len(skill.strip()) > 100
        for skill in skills
    ):
        raise ValidationError("Required skills must be a list of non-empty strings up to 100 characters.")

    required_education = record.get("required_education", "")
    required_experience = record.get("required_experience", "")
    if not isinstance(required_education, str) or required_education not in EDUCATION_LEVELS:
        raise ValidationError("Record education requirement is not supported.")
    if not isinstance(required_experience, str) or required_experience not in EXPERIENCE_LEVELS:
        raise ValidationError("Record experience requirement is not supported.")

    deadline_value = record.get("application_deadline")
    deadline = None
    if deadline_value:
        if not isinstance(deadline_value, str):
            raise ValidationError("Application deadline must use YYYY-MM-DD or be null.")
        try:
            deadline = date.fromisoformat(deadline_value)
        except ValueError as error:
            raise ValidationError("Application deadline must use YYYY-MM-DD or be null.") from error
        if deadline.isoformat() != deadline_value:
            raise ValidationError("Application deadline must use YYYY-MM-DD or be null.")
        if deadline < (today or timezone.localdate()):
            raise ValidationError("Application deadline has passed.")

    application_url = record.get("application_url", "")
    if application_url:
        if not isinstance(application_url, str):
            raise ValidationError("Application URL must be a string.")
        try:
            APPLICATION_URL_VALIDATOR(application_url)
        except ValidationError as error:
            raise ValidationError("Application URL must be a valid HTTPS URL.") from error
        parsed_url = urlparse(application_url)
        if not parsed_url.hostname or parsed_url.username or parsed_url.password:
            raise ValidationError("Application URL must not contain credentials.")

    source_url = record.get("source_url", feed["url"])
    if not isinstance(source_url, str):
        raise ValidationError("Source URL must be a string.")
    parsed_source_url = urlparse(source_url)
    try:
        URLValidator(schemes=["https"])(source_url)
    except ValidationError as error:
        raise ValidationError("Source URL must be a valid HTTPS URL.") from error
    if not parsed_source_url.hostname or parsed_source_url.username or parsed_source_url.password:
        raise ValidationError("Source URL must not contain credentials.")

    location = record.get("location", "")
    if not isinstance(location, str) or len(location) > 160:
        raise ValidationError("Location must be text up to 160 characters.")
    opportunity_type = record.get("opportunity_type", "")
    if not isinstance(opportunity_type, str) or len(opportunity_type) > 80:
        raise ValidationError("Opportunity type must be text up to 80 characters.")
    eligibility = record.get("eligibility_requirements", "")
    required_field = record.get("required_field", "")
    if not isinstance(eligibility, str) or len(eligibility) > 10000:
        raise ValidationError("Eligibility requirements must be text up to 10,000 characters.")
    if not isinstance(required_field, str) or len(required_field) > 160:
        raise ValidationError("Required field must be text up to 160 characters.")

    return external_id, {
        **required_text,
        "category": category,
        "location": location.strip(),
        "eligibility_requirements": eligibility,
        "required_skills": [skill.strip() for skill in skills],
        "required_education": required_education,
        "required_field": required_field,
        "required_experience": required_experience,
        "application_deadline": deadline,
        "application_url": application_url,
        "opportunity_type": opportunity_type.strip(),
        "source_url": source_url,
    }


def import_records(records, feed, *, publish=False, dry_run=False):
    if not isinstance(records, list):
        raise FeedError("Opportunity records must be a JSON array.")
    now = timezone.now()
    results = {"created": 0, "updated": 0, "skipped": 0, "errors": []}
    seen_ids = set()
    for index, record in enumerate(records, start=1):
        try:
            external_id, normalized = normalize_record(record, feed)
        except ValidationError as error:
            if not dry_run and isinstance(record, dict):
                source_id = record.get("id")
                deadline_value = record.get("application_deadline")
                try:
                    expired = (
                        isinstance(source_id, (str, int))
                        and bool(str(source_id).strip())
                        and isinstance(deadline_value, str)
                        and date.fromisoformat(deadline_value) < timezone.localdate()
                    )
                except ValueError:
                    expired = False
                if expired:
                    stale = Opportunity.objects.filter(
                        source=feed["name"],
                        source_identifier=str(source_id).strip(),
                        source_managed=True,
                        is_published=True,
                    ).first()
                    if stale:
                        stale.is_published = False
                        stale.source_collected_at = now
                        stale.save(update_fields=["is_published", "source_collected_at", "date_updated"])
            results["skipped"] += 1
            results["errors"].append({"record": index, "reason": error.messages[0]})
            continue
        if external_id in seen_ids:
            results["skipped"] += 1
            results["errors"].append({"record": index, "reason": "Duplicate source id in feed."})
            continue
        seen_ids.add(external_id)

        matching_source = Opportunity.objects.filter(
            source=feed["name"],
            source_identifier=external_id,
        )
        existing = matching_source.filter(source_managed=True).first()
        if dry_run:
            duplicate = Opportunity.objects.filter(
                title__iexact=normalized["title"],
                organization__iexact=normalized["organization"],
                is_demo=False,
            ).exists()
            if existing:
                results["updated"] += 1
            elif matching_source.exists() or duplicate:
                results["skipped"] += 1
                results["errors"].append({
                    "record": index,
                    "reason": "Matching curated record or source identifier already exists.",
                })
            else:
                results["created"] += 1
            continue

        with transaction.atomic():
            existing = matching_source.select_for_update().filter(source_managed=True).first()
            if existing is None:
                identifier_taken = matching_source.select_for_update().exists()
                duplicate = Opportunity.objects.filter(
                    Q(title__iexact=normalized["title"]),
                    Q(organization__iexact=normalized["organization"]),
                    is_demo=False,
                ).exists()
                if identifier_taken or duplicate:
                    results["skipped"] += 1
                    results["errors"].append({
                        "record": index,
                        "reason": "Matching curated record or source identifier already exists.",
                    })
                    continue
                opportunity = Opportunity(
                    **normalized,
                    source=feed["name"],
                    source_identifier=external_id,
                    source_collected_at=now,
                    source_managed=True,
                    is_verified=True,
                    is_demo=False,
                    is_published=publish,
                )
                opportunity.save()
                results["created"] += 1
                continue

            for field, value in normalized.items():
                setattr(existing, field, value)
            existing.source_collected_at = now
            existing.is_verified = True
            if publish:
                existing.is_published = True
            existing.save()
            results["updated"] += 1
    return results
