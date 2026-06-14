# Intel — Local Newspaper Intelligence Scraper

Scrape your local newspaper, extract people's names with AI, summarize articles, and push everything to a PostgreSQL database with a CRM-ready REST API.

## What it does

1. **Scrapes** configurable local newspaper sources (RSS feeds or HTML pages)
2. **Extracts people** mentioned in articles using OpenAI + spaCy NER
3. **Summarizes** article content with AI into concise local-news briefs
4. **Stores** everything in PostgreSQL with a schema designed for CRM integration
5. **Exposes a REST API** your custom CRM can poll, or receives webhook push notifications

## Quick start

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env — set OPENAI_API_KEY and API_KEY at minimum
```

### 2. Configure your newspaper sources

Edit `config/newspapers.yaml` to point at your local newspaper's RSS feed or HTML page:

```yaml
sources:
  - name: "Springfield Gazette"
    url: "https://www.springfieldgazette.com/rss"
    type: rss
    enabled: true
    region: "Springfield"
```

For HTML-based newspapers, use `type: html` with CSS selectors (see the commented example in the config file).

### 3. Run with Docker

```bash
docker compose up -d
```

This starts:
- **PostgreSQL** on port 5432
- **API server** on port 8000
- **Scheduled scraper** (runs every 6 hours by default)

### 4. Run locally (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Start PostgreSQL separately, then:
python -m src.main init
python -m src.main scrape    # one-time scrape
python -m src.main serve     # start API
```

## CRM integration

### REST API

All endpoints require the `X-API-Key` header set to your `API_KEY` from `.env`.

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/articles` | GET | List scraped articles with summaries |
| `/api/v1/articles/{id}` | GET | Get a single article |
| `/api/v1/people` | GET | List people mentioned in articles |
| `/api/v1/people/{id}` | GET | Get a single person with article context |
| `/api/v1/people?name=Smith` | GET | Search people by name |
| `/api/v1/export/people?format=csv` | GET | Bulk export for CRM import |
| `/api/v1/scrape` | POST | Trigger a manual scrape |
| `/api/v1/stats` | GET | Dashboard stats |
| `/health` | GET | Health check (no auth) |

Interactive API docs are available at `http://localhost:8000/docs`.

### Webhook push

Set `CRM_WEBHOOK_URL` in `.env` to receive real-time notifications when new articles are processed:

```json
{
  "event": "article.created",
  "data": {
    "id": 1,
    "title": "...",
    "summary": "...",
    "people": [{"full_name": "Jane Doe", "role_context": "City Mayor"}]
  }
}
```

If `CRM_WEBHOOK_SECRET` is set, requests include an `X-Intel-Signature` HMAC header for verification.

### Example CRM fetch

```python
import requests

headers = {"X-API-Key": "your-crm-api-key-here"}
people = requests.get("http://localhost:8000/api/v1/people?since=2026-06-01", headers=headers).json()

for person in people:
    crm.create_lead(
        name=person["full_name"],
        notes=person["role_context"],
        source=person["article_url"],
    )
```

## Database schema

**articles** — scraped articles with AI summaries
- `id`, `source_name`, `title`, `url`, `summary`, `published_at`, `scraped_at`, `region`

**people** — individuals mentioned in articles (CRM contact records)
- `id`, `article_id`, `full_name`, `role_context`, `mention_count`, `created_at`

**scrape_logs** — audit trail for each scrape run

## Project structure

```
config/newspapers.yaml   # Newspaper source configuration
src/
  scraper/               # RSS and HTML scrapers
  ai/                    # Name extraction and summarization
  database/              # SQLAlchemy models and CRUD
  api/                   # FastAPI REST server
  pipeline/              # Orchestration (scrape → AI → store)
  crm/                   # Webhook push to CRM
  main.py                # CLI entry point
```

## CLI commands

```bash
python -m src.main init        # Create database tables
python -m src.main scrape      # Run one scrape cycle
python -m src.main scheduler   # Run scraper on interval
python -m src.main serve       # Start API server
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `OPENAI_API_KEY` | — | Required for AI summarization |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model to use |
| `API_KEY` | `dev-api-key` | API key for CRM authentication |
| `SCRAPE_INTERVAL_HOURS` | `6` | Hours between scheduled scrapes |
| `CRM_WEBHOOK_URL` | — | Optional webhook for push notifications |
| `CRM_WEBHOOK_SECRET` | — | HMAC secret for webhook verification |
