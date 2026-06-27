# Railway IaC

This folder defines the full Railway stack for Throughline:

- **Postgres** — managed PostgreSQL database
- **Throughline** — web service (API + CRM dashboard)

## Usage

```bash
npm i -g @railway/cli
railway login
railway link          # select your Throughline project + environment
railway up
```

## After deploy

1. Confirm **Throughline** service has `DATABASE_URL` referencing **Postgres**
2. Set `OPENAI_API_KEY` and `API_KEY` on the Throughline service (if not already set)
3. Redeploy the Throughline service
