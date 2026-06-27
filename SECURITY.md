# Security Policy

## Supported versions

Security fixes are applied to the latest release on the `main` branch.

## Reporting a vulnerability

Please report security issues privately by opening a GitHub Security Advisory on this repository, or by contacting the repository owner directly. Do not file public issues for exploitable vulnerabilities.

## Authentication

- All `/api/v1/*` data endpoints require the `X-API-Key` header matching the `API_KEY` environment variable.
- `/health` and `/api/v1/setup` are public and return only non-sensitive status information.
- Change `API_KEY` from the default `dev-api-key` before deploying to production.

## Dashboard API key injection

When the React dashboard is served from the API (`static/` build), the server injects `window.__THROUGHLINE_API_KEY__` into the HTML. Anyone with access to the dashboard URL can read this key from page source. Treat the dashboard as an authenticated internal tool, or place it behind your own auth proxy.

## Webhooks

When `CRM_WEBHOOK_SECRET` is set, outbound webhook payloads include an `X-Throughline-Signature` HMAC-SHA256 header. Verify this signature before trusting webhook data.

## CORS

The API allows all origins (`*`) by default for CRM integration flexibility. Restrict CORS at a reverse proxy if exposing the API publicly.

## Scraping

Configure `request_delay_seconds` in `config/newspapers.yaml` and respect newspaper terms of service. The default User-Agent identifies the bot and links to this repository.
