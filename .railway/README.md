# Railway Infrastructure as Code

This folder defines the full Railway stack for Intel:

- **Postgres** — managed PostgreSQL database
- **Intel** — web service (API + CRM dashboard)

## Apply the stack

From the repo root, with the [Railway CLI](https://docs.railway.com/cli) installed:

```bash
railway login
railway link          # select your Intel project + environment
railway config plan   # preview: should show "Create service Postgres"
railway config apply  # provisions Postgres and wires DATABASE_URL
```

After apply:

1. Confirm **Intel** service has `DATABASE_URL` referencing **Postgres**
2. Set `OPENAI_API_KEY` and `API_KEY` on the Intel service (if not already set)
3. Redeploy the Intel service

## Note on railway.toml

`railway.toml` was removed — this project uses Infrastructure as Code (`.railway/railway.ts`) instead. A service cannot be managed by both at the same time.
