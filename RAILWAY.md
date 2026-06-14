# Deploying Intel on Railway

## The problem this fixes

If `DATABASE_URL` is set to `${{Postgres.DATABASE_URL}}` but **no Postgres service exists**, Railway resolves it to an **empty string**. The app then fails to start.

This repo includes **Infrastructure as Code** (`.railway/railway.ts`) that provisions Postgres and wires `DATABASE_URL` automatically.

## Quick setup (recommended)

### 1. Install Railway CLI

```bash
npm i -g @railway/cli
railway login
```

### 2. Link your project

```bash
cd Intel
railway link    # select your Intel project + environment
```

### 3. Provision Postgres + wire DATABASE_URL

```bash
railway config plan    # preview: should show "Create service Postgres"
railway config apply   # creates Postgres and links DATABASE_URL to Intel
```

### 4. Set required variables on Intel service

In Railway dashboard → **Intel** service → **Variables**:

| Variable | Required |
|---|---|
| `OPENAI_API_KEY` | Yes |
| `API_KEY` | Yes (strong random secret) |

`DATABASE_URL` is set automatically by `railway config apply`.

### 5. Deploy

Push to GitHub or click **Deploy** in Railway. Open your Railway URL — the CRM dashboard loads at `/`.

---

## Manual setup (dashboard)

If you prefer not to use the CLI:

1. **+ New** → **Database** → **PostgreSQL** (name it `Postgres`)
2. Open **Intel** service → **Variables** → **Add Reference** → Postgres → `DATABASE_URL`
3. Set `OPENAI_API_KEY` and `API_KEY`
4. Redeploy

---

## Architecture

| Service | Purpose |
|---|---|
| **Postgres** | Managed PostgreSQL database |
| **Intel** | API + CRM dashboard (Dockerfile) |
| **worker** (optional) | `python -m src.main scheduler` |

## Optional: scheduled scraper worker

1. **+ New** → same GitHub repo → name it `worker`
2. **Start command:** `python -m src.main scheduler`
3. Link `DATABASE_URL` from Postgres + set `OPENAI_API_KEY`, `API_KEY`

## Optional: Railway Cron

```bash
curl -X POST https://YOUR-APP.up.railway.app/api/v1/scrape -H "X-API-Key: YOUR_API_KEY"
```

Schedule: `0 */6 * * *`

## First run

1. Open your Railway URL
2. Click **Run scrape**
3. Check **Today's names**

## Troubleshooting

| Issue | Fix |
|---|---|
| `DATABASE_URL is empty` | Run `railway config apply` or add Postgres manually |
| `Connection refused` to `localhost:5432` | Postgres not linked — see step 3 above |
| Build fails | Check build logs; `frontend/package-lock.json` must exist |
| Empty dashboard | Click **Run scrape** or add worker/cron |
| `railway.toml` conflict | Removed — this project uses `.railway/railway.ts` instead |

## Local vs Railway

- **Local Docker:** `http://localhost:8000`
- **Railway:** your `*.up.railway.app` URL
