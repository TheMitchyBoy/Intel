# Deploying Intel on Railway

## Fix: "DATABASE_URL is empty"

This means **PostgreSQL is not connected** to your Intel service. Follow these steps exactly:

### Step 1 — Add PostgreSQL

1. Open your Railway project
2. Click **+ New** → **Database** → **PostgreSQL**
3. Wait for it to finish provisioning (~30 seconds)

### Step 2 — Connect Postgres to Intel

1. Click the **PostgreSQL** service on your canvas
2. Click the **Connect** button (or **Data** tab → Connect)
3. Select your **Intel** service from the list
4. Railway automatically adds `DATABASE_URL`, `PGHOST`, `PGUSER`, etc.

> **Important:** Use **Connect**, don't manually type `${{Postgres.DATABASE_URL}}` unless a Postgres service named exactly `Postgres` exists.

### Step 3 — Set API keys on Intel

Intel service → **Variables**:

| Variable | Value |
|---|---|
| `OPENAI_API_KEY` | your OpenAI key |
| `API_KEY` | a strong random secret |

### Step 4 — Redeploy Intel

Click **Deploy** on the Intel service (or push to GitHub).

### Step 5 — Verify

Open your Railway URL. If Postgres is connected, the yellow setup banner disappears.

Check diagnostics: `https://YOUR-APP.up.railway.app/api/v1/setup`

---

## Alternative: CLI (Infrastructure as Code)

```bash
npm i -g @railway/cli
railway login
railway link
railway config apply   # creates Postgres + wires DATABASE_URL
```

---

## Architecture

| Service | Purpose |
|---|---|
| **PostgreSQL** | Database (add via Dashboard or `railway config apply`) |
| **Intel** | API + CRM dashboard + **daily auto-scrape** (6:00 AM Alaska time) |
| **worker** (optional) | Only if you disable the built-in scheduler |

## Daily auto-scrape

The Intel service automatically crawls Ketchikan Daily News **every day at 6:00 AM Alaska time** (`America/Sitka`). No separate worker needed.

Override on Intel → **Variables**:

| Variable | Default | Purpose |
|---|---|---|
| `SCRAPE_SCHEDULE_ENABLED` | `true` | Set `false` to disable auto-scrape |
| `SCRAPE_SCHEDULE_HOUR` | `6` | Hour to run (24h clock, local timezone) |
| `SCRAPE_SCHEDULE_MINUTE` | `0` | Minute to run |
| `SCRAPE_TIMEZONE` | `America/Sitka` | Ketchikan local time |

Check schedule: `GET /health` or `GET /api/v1/setup` → `scrape_schedule`.

## Optional worker

Only needed if you set `SCRAPE_SCHEDULE_ENABLED=false` and want a dedicated scraper process:

1. **+ New** → same repo → name `worker`
2. Start command: `python -m src.main scheduler`
3. Postgres → Connect → worker
4. Set `OPENAI_API_KEY` and `API_KEY`

| Diagnostics | Meaning | Fix |
|---|---|---|
| `DATABASE_URL: missing` | Not linked | Use Postgres → Connect → Intel |
| `DATABASE_URL: unresolved_reference` | Broken `${{Postgres...}}` ref | Delete variable, use Connect button |
| `PGHOST: set` but URL missing | Partial connect | Redeploy Intel after Connect |
| App starts but no data | DB not init yet | Click **Run scrape** or wait for daily auto-scrape (6 AM AK) |

## Troubleshooting
