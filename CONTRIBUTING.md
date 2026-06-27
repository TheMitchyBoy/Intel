# Contributing to Intel

Thank you for helping improve Intel. This guide covers local setup, conventions, and how to submit changes.

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.12+ |
| Node.js | 20+ (22 recommended) |
| PostgreSQL | 15+ |
| OpenAI API key | Required for AI summarization and name extraction |

## Local development

```bash
# Backend
cp .env.example .env          # set OPENAI_API_KEY, API_KEY, DATABASE_URL
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -m src.main init

# Frontend (optional — API also serves the built dashboard)
cd frontend && cp .env.example .env && npm install && npm run dev
```

Run the API:

```bash
python -m src.main serve      # http://localhost:8000
python -m src.main scrape     # one-time scrape
```

Or use Docker:

```bash
docker compose up -d --build
```

## Project layout

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how scraping, AI extraction, and the CRM API fit together.

| Path | Purpose |
|------|---------|
| `src/scraper/` | RSS and HTML newspaper scrapers |
| `src/ai/` | Name extraction (spaCy + OpenAI) and summarization |
| `src/pipeline/` | Scrape orchestration, scheduling, background jobs |
| `src/database/` | SQLAlchemy models, contacts, CRUD |
| `src/api/` | FastAPI REST server and SPA hosting |
| `frontend/` | React CRM dashboard |
| `config/newspapers.yaml` | Newspaper source configuration |

## Adding a newspaper source

Edit `config/newspapers.yaml`:

```yaml
sources:
  - name: "Your Local Paper"
    url: "https://example.com/search/?f=rss&t=article"
    type: rss
    enabled: true
    region: "Your City, ST"
    filters:
      url_must_contain: "/article_"
    selectors:
      content: "#article-body, .article-content"
```

Restart the API or trigger a scrape to pick up changes. See inline comments in the YAML file for BLOX/TNCMS RSS tips.

## Code style

**Python**

- Follow existing patterns in each module; prefer small, focused functions.
- Add module docstrings and docstrings on public functions.
- Run `python3 -m compileall src` before pushing.

**TypeScript / React**

- Match existing component structure and CSS class naming (`btn--primary`, `modal`, etc.).
- Keep API calls in `frontend/src/api/client.ts`.
- Run `npm run lint` and `npm run build` in `frontend/` before pushing.

## Pull requests

1. Branch from `main` using a descriptive name.
2. Keep changes focused — one feature or fix per PR when possible.
3. Update README or `docs/` if you change API behavior, schema, or env vars.
4. Confirm the frontend builds and Python modules compile.

## Reporting issues

Include:

- What you expected vs. what happened
- Steps to reproduce
- Relevant logs (scrape run, API error, browser console)
- Environment (local Docker, Railway, etc.)

## Security

Do not open public issues for vulnerabilities. See [SECURITY.md](SECURITY.md).
