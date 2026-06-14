# Deploying Intel on Railway

## Architecture

Railway runs two services from this repo:

| Service | Purpose | Start command |
|---|---|---|
| **web** | API + CRM dashboard | `Dockerfile` (default) |
| **worker** (optional) | Scheduled scraper | `python -m src.main scheduler` |
| **PostgreSQL** | Database | Railway plugin |

## Quick setup

### 1. Create a Railway project

1. Go to [railway.app](https://railway.app) and create a new project
2. **Deploy from GitHub** → connect this repo (`TheMitchyBoy/Intel`)
3. Railway will detect `railway.toml` and build from the `Dockerfile`

### 2. Add PostgreSQL

1. In your project, click **+ New** → **Database** → **PostgreSQL**
2. Railway automatically sets `DATABASE_URL` on linked services

### 3. Set environment variables

On the **web** service, add these variables:

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | Your OpenAI API key |
| `API_KEY` | Yes | Secret key for API auth (pick a strong random string) |
| `OPENAI_MODEL` | No | Default: `gpt-4o-mini` |
| `SCRAPE_INTERVAL_HOURS` | No | Default: `6` |

> **Important:** `DATABASE_URL` must be linked from Postgres — do not type it manually.

### 4. Link Postgres to web service (required)

This is the most common cause of deploy failures.

1. Open your **web** service (not Postgres)
2. Go to **Variables** tab
3. Click **+ New Variable** → **Add Reference**
4. Select your **PostgreSQL** service
5. Choose **`DATABASE_URL`** (or `DATABASE_PRIVATE_URL` for internal networking)
6. Click **Add**

You should see a variable like `${{Postgres.DATABASE_URL}}` in the web service variables.

### 5. Deploy

Railway builds the Docker image (frontend + API) and starts on the assigned `PORT`.

Your CRM dashboard will be at your Railway URL, e.g. `https://intel-production.up.railway.app`

## Optional: scheduled scraper worker

To scrape automatically without using the dashboard button:

1. **+ New** → **GitHub Repo** → same repo
2. Name it `worker`
3. Set the **Custom Start Command**: `python -m src.main scheduler`
4. Add the same env vars (`DATABASE_URL`, `OPENAI_API_KEY`, `API_KEY`)
5. Link the same Postgres database

## Optional: Railway Cron (alternative to worker)

Instead of a worker, use Railway Cron to hit the scrape endpoint:

1. **+ New** → **Cron Job**
2. Schedule: `0 */6 * * *` (every 6 hours)
3. Command:
   ```bash
   curl -X POST https://YOUR-APP.up.railway.app/api/v1/scrape -H "X-API-Key: YOUR_API_KEY"
   ```

## First run

After deploy:

1. Open your Railway URL — the CRM dashboard loads
2. Click **Run scrape** to pull Ketchikan Daily News articles
3. Check **Today's names** tab

## Troubleshooting

| Issue | Fix |
|---|---|
| Build fails | Check Railway build logs; ensure `frontend/package-lock.json` exists |
| 502 / app won't start | Check deploy logs; confirm Postgres is linked and `DATABASE_URL` is set |
| `Connection refused` to `localhost:5432` | `DATABASE_URL` not linked — see step 4 above |
| Empty dashboard | Click **Run scrape** or add the worker/cron service |
| `postgres://` errors | Handled automatically — app converts to `postgresql://` |
| API key mismatch | Set `API_KEY` env var on web service; it's injected into the frontend at runtime |

## Local vs Railway

- **Local Docker**: `http://localhost:8000`
- **Railway**: your assigned `*.up.railway.app` URL
- No separate frontend service needed — API serves the CRM on one port
