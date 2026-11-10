# OpenDoors AI

**Breaking barriers. Unlocking opportunities.**

OpenDoors AI is an accessible opportunity-discovery MVP for scholarships, internships, entry-level jobs, fellowships, educational programs, and training. It helps people organize their goals, compare published opportunities with their profile, understand what is known or missing, and track their own next steps.

## Problem and approach

Opportunity information is often scattered and difficult to compare. OpenDoors brings listings into one searchable catalogue and provides a deterministic, explainable profile comparison. Match scores are not eligibility decisions: missing information remains unknown, and only explicit unmet mandatory requirements are identified as potential disqualifiers.

## Features

- Email-based registration and session login/logout with Django password validation.
- Private seeker profiles, preferences, and optional CV upload (PDF/DOC/DOCX, maximum 5 MB).
- Searchable, filterable, paginated opportunity directory and Django Admin management.
- Deterministic, ranked matching with dimension-level scores, reasons, missing information, eligibility concerns, and next steps.
- Rule-based plain-language eligibility explanations when no AI provider is configured.
- Optional OpenAI-compatible explanation provider behind a dedicated service; provider output supplements but does not replace the listed requirements.
- User-scoped saved opportunities and application status tracking.
- Responsive, keyboard-accessible pages, visible focus, skip link, live feedback, semantic headings, and reduced-motion support.
- Clearly labeled synthetic demo data with no fabricated live organizations, deadlines, or application links.
- Session-authenticated REST API and generated OpenAPI schema.

## Architecture

| Area | Responsibility |
| --- | --- |
| `accounts` | Registration, session authentication, dashboard, profile/settings pages |
| `profiles` | Seeker profile model and private profile API |
| `opportunities` | Published opportunity catalogue, discovery UI, Admin, demo seed command |
| `matching` | Explainable scoring, optional AI abstraction, match/explanation APIs |
| `applications` | User-owned bookmarks and application tracking |
| `config` | Django settings, database/static deployment, URLs, WSGI/ASGI |
| `templates`, `static` | Server-rendered accessible frontend and responsive styles |

### Matching weights

Scores use the weighted average of available dimensions; missing dimensions are excluded rather than counted as zero. Current weights are skills 30, education 25, field of study 20, experience 15, location 10, and preferred category 10. The five suggested core dimensions retain their requested weights; category alignment is included as an additional preference signal, so all six known dimensions together have a total weight of 110 before normalization. Results are rounded to an integer from 0 to 100. Update `MATCH_WEIGHTS` in `matching/services.py` to tune them.

Education and experience are compared using ordered levels. Skills score the proportion of listed required skills present in the profile. Field and location comparisons are case-insensitive. An explicit requirement only disqualifies a profile when an opportunity administrator records a supported mandatory rule (`in` or `equals`) and the profile value conflicts. Unknown values request confirmation. A passed match never establishes legal or provider eligibility.

## Technology

- Python 3.11+ recommended; Django 5.2 LTS and Django REST Framework.
- SQLite for local development; PostgreSQL through `DATABASE_URL` for deployment.
- Django templates, HTML, CSS, and vanilla browser behavior.
- WhiteNoise and Gunicorn for a Render-compatible web service.
- Optional OpenAI-compatible chat-completions API via Python's standard library.

## Local setup

1. Install Python 3.11 or later and create/activate a virtual environment.
2. Install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and set a unique `SECRET_KEY`. Export variables in your shell or use your preferred environment-file loader; Django intentionally does not read `.env` automatically.
4. Initialize the database and create sample records:

   ```powershell
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py seed_demo
   ```

5. Start the development server:

   ```powershell
   python manage.py runserver
   ```

Open `http://127.0.0.1:8000/`. Admin is at `/admin/`; all seeded opportunities are marked **Demonstration** and use no external application links or deadlines.

## Environment

| Variable | Required | Description |
| --- | --- | --- |
| `SECRET_KEY` | Production | Unique, private Django signing key. Production startup fails if the development fallback is used. |
| `DEBUG` | No | Defaults to `true` locally. Set `false` in production. |
| `ALLOWED_HOSTS` | Production | Comma-separated hostnames. |
| `DATABASE_URL` | Production | PostgreSQL URL; empty uses `db.sqlite3`. |
| `CSRF_TRUSTED_ORIGINS` | Sometimes | Comma-separated trusted HTTPS origins when needed by a proxy/custom domain. |
| `SECURE_SSL_REDIRECT` | No | Defaults to `true` when `DEBUG=false`. |
| `AI_ENABLED` | No | Defaults to `false`; deterministic explanations remain available. |
| `AI_PROVIDER` | AI use | Currently `openai_compatible`. |
| `AI_API_KEY` | AI use | Secret API token; never commit it. |
| `AI_MODEL` | AI use | Provider model identifier. |
| `AI_BASE_URL` | No | OpenAI-compatible API base, defaults to `https://api.openai.com/v1`. |
| `AI_TIMEOUT_SECONDS` | No | Provider request timeout; defaults to 15. |

When AI is disabled, explanations are explicitly labeled **Rule-based explanation**. When enabled with valid provider settings, the UI labels the supplementary result **AI-assisted explanation**. Provider failure is reported rather than silently presented as AI output. The opportunity requirements remain the authority.

## Database and demo data

Migrations live in each model-owning app's `migrations/` folder. `seed_demo` is idempotent and creates six synthetic records. It does not create live deadlines, organizations, or application URLs.

```powershell
python manage.py migrate
python manage.py seed_demo
```

For production, set `DATABASE_URL` to PostgreSQL before running migrations. Do not use the demonstration records as live listings.

## Tests and checks

```powershell
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
```

Tests cover registration and login, profile updates and API access, discovery and filters, deadline ordering, deterministic matching, missing information, explicit eligibility mismatches, rule-based explanations, saved records, application statuses, and cross-user privacy.

## API

All API paths are under `/api/`. Session authentication is used for private endpoints; unsafe requests require a valid CSRF token. Opportunity list/detail endpoints are public and include only published records. Pagination uses page-number pagination (12 records by default).

| Method and path | Access | Purpose |
| --- | --- | --- |
| `POST /api/auth/register/` | Public, CSRF | Register and start a session |
| `POST /api/auth/login/` | Public, CSRF | Start a session |
| `POST /api/auth/logout/` | Authenticated, CSRF | End a session |
| `GET, PUT, PATCH /api/profile/` | Authenticated | Read/update current user's profile |
| `PUT, PATCH /api/profile/update/` | Authenticated | Alias for profile update |
| `GET /api/opportunities/?q=&category=&location=&ordering=deadline` | Public | Search/filter/paginate |
| `GET /api/opportunities/{id}/` | Public | Published opportunity details |
| `GET /api/matches/` | Authenticated | Ranked, paginated match results |
| `GET /api/matches/{opportunity_id}/` | Authenticated | One explainable match |
| `POST /api/matches/explanations/` | Authenticated | Explain with `{"opportunity_id": 1}` |
| `GET, POST /api/saved-opportunities/` | Authenticated | List/create current user's saved records |
| `DELETE /api/saved-opportunities/{id}/` | Authenticated | Remove an owned saved record |
| `GET, POST /api/applications/` | Authenticated | List/create application tracker records |
| `GET, PUT, PATCH, DELETE /api/applications/{id}/` | Authenticated | Manage an owned tracker record |
| `GET /api/schema/` | Public | OpenAPI schema |

Application statuses: `interested`, `preparing`, `applied`, `interview`, `accepted`, `rejected`, and `withdrawn`. User IDs are always assigned from the authenticated session, never accepted from API input.

## Deployment (Render)

The included `render.yaml` defines a Django web service and PostgreSQL database. Review its region/plan choices before use. Configure the generated `SECRET_KEY`, set `DEBUG=false`, and verify `ALLOWED_HOSTS`/CSRF origins for your service and custom domain. Render runs migrations during the build and collects static assets; review logs after deployment. Create an admin user through a one-off shell or the Render shell:

```sh
python manage.py createsuperuser
python manage.py seed_demo
```

For other hosts, install requirements, set the environment above, run `python manage.py migrate` and `collectstatic --no-input`, then serve `config.wsgi:application` with Gunicorn behind HTTPS. Configure private media storage and backups before accepting real CV uploads.

## Screenshots

No screenshots are included yet. Add reviewed screenshots here when the app is running.

## Future improvements

- Add verified opportunity ingestion with source freshness and moderation workflows.
- Add private object storage, malware scanning, retention controls, and user-directed CV deletion.
- Add password reset, email verification, and account deletion flows.
- Add provider-specific structured eligibility rules and user research/usability testing.
- Add automated accessibility checks and browser-level end-to-end coverage.
- Add rate limiting, structured audit logging, and operational monitoring for production.
