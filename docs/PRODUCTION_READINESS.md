# Production Readiness Audit

## Status

The repository is prepared for a controlled Render deployment, but it is **not deployed or production-verified**. Local checks and mocked integrations pass. Production PostgreSQL, outbound email, OpenRouter, and a real opportunity source still need external configuration and live verification.

## Findings and disposition

| Area | Finding during audit | Current disposition |
| --- | --- | --- |
| Django health/deployment | No database-backed health endpoint; the Render host was fixed in configuration; migrations were part of the build rather than a deploy step. | Added `/healthz/`, host/CSRF handling for Render's runtime hostname, and a pre-deploy migration/cache-table step. |
| Database/cache | SQLite is appropriate locally but does not prove PostgreSQL behavior; account throttles need a shared cache when scaled. | `DATABASE_URL` supports PostgreSQL; Render uses its database cache. Two additive migrations were applied to the local database. No live PostgreSQL test has been done. |
| Authentication/email | Verification and recovery mail were not present; sensitive account actions lacked shared throttling. | Added optional verification, expiring password reset, generic unknown-email response, and cache-backed limits. Email remains disabled by default and SMTP delivery is untested. |
| AI integration | OpenRouter-specific request handling and provider failure tests were missing. | Added OpenRouter/OpenAI-compatible requests, timeout/response bounds, safe error categories, and labeled rule-based fallback. Automated tests mock provider responses; no real key or live request was used. |
| Opportunity data | There was no ingestion workflow or distinction between sourced and synthetic listings. | Added an allowlisted HTTPS JSON importer, normalization, duplicate handling, collection metadata, verification flags, dry-run, and explicit publish control. No source is configured or live-verified. |
| CV upload | Extension checks alone were insufficient; uploaded files needed a private access path and safer filenames. | Added 5 MB limit, PDF/Word format checks, UUID/user-scoped names, authenticated non-cacheable downloads, and removal. There is no malware scanning, cloud object storage, independent backup, or automated retention policy. |
| Browser/accessibility | No browser journey or automated accessibility scan existed. | Added Playwright/axe coverage for the key signup-to-tracker journey and responsive/focus/reduced-motion checks. The browser test passes locally; this is not a manual audit or WCAG conformance claim. |
| Operations | There was no readiness endpoint or production alerting configuration. | Database health check and Render health path are configured. Error monitoring, metrics, alerting, uptime checks, and incident/recovery procedures remain unconfigured. |

## Verification performed

The following checks ran successfully in the local workspace:

- `python manage.py test` — 49 tests passed, including mocked AI/feed/email tests and the browser journey.
- `python manage.py test opportunities.test_ingestion` — 9 tests passed.
- `python manage.py test browser_tests` — 1 Playwright journey passed; axe reported no violations on the tested pages.
- `python manage.py migrate --noinput` — applied `opportunities.0002_opportunity_is_verified_and_more` and `profiles.0002_cv_upload_to_user_uuid` to the local SQLite database.
- `python manage.py makemigrations --check --dry-run` — no model changes pending.
- `python manage.py check` — no issues.
- `python manage.py check --deploy` with non-production test values (`DEBUG=false`, test-only secret, explicit host, HTTPS redirect) — no issues.

These results do not prove a Render deployment, live PostgreSQL, SMTP delivery, live AI provider, or live-feed availability.

## Deployment blockers and remaining risks

Before calling the service production-ready:

1. Deploy the Blueprint to a Render account and verify the external hostname, health endpoint, migration logs, registration, and private routes against the provisioned PostgreSQL database.
2. Configure a real SMTP provider if verification/password recovery are required; test delivery, expiry, resend behavior, and sender-domain alignment. With `EMAIL_ENABLED=false`, those flows are intentionally disabled and signup is immediate.
3. If demonstrating AI, configure server-side OpenRouter credentials/model and verify one successful request plus a failure path. Do not expose credentials in client code or logs.
4. Choose a permitted, trusted source, configure its exact host allowlist, inspect a dry run, review imported records, publish deliberately, and arrange recurring collection/freshness checks. The application does not supply or schedule a feed.
5. Decide on private object storage, encrypted independent backups, restore testing, document retention/deletion, and malware scanning before accepting real CVs. Render's persistent disk is service-local and unsuitable as shared storage for a multi-instance deployment.
6. Perform manual keyboard, screen-reader, zoom, contrast, and mobile testing. Automated axe checks are limited to exercised pages and cannot certify WCAG 2.2 AA.
7. Configure production error reporting, metrics, alerting, uptime monitoring, and an incident/recovery owner.

## Demonstration readiness

For a demo without external providers: deploy with AI and email disabled, register an account through the site, create a profile, and run `python manage.py seed_demo` to add synthetic listings. Demonstrate discovery, match explanations, bookmarks, and application tracking. Seed records are demonstration data, not verified live opportunities. Do not use shared demo credentials or real CVs.

See the [README](../README.md) for environment setup, trusted-feed schema, manual AI/email verification, Render setup, storage caveats, and the launch checklist.
