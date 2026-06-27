# Changelog

All notable changes to Intel are documented here.

## [1.0.0] — 2026-06-27

### Added

- Contact name editing from the person detail modal (typo fixes)
- `name_manually_edited` flag to protect user corrections during re-scrape
- `PATCH /api/v1/people/{id}` rename endpoint
- Review queue with bulk confirm/reject
- Name re-extraction job (`POST /api/v1/reprocess/names`)
- Canonical contacts + person_mentions data model
- React CRM dashboard with Today's names, All people, Articles tabs
- Railway deployment guide (`RAILWAY.md`)
- Architecture documentation (`docs/ARCHITECTURE.md`)
- CI workflow (Python compile + frontend build/lint)
- MIT license, CONTRIBUTING, and SECURITY docs

### Changed

- README rewritten with full API reference and architecture overview
- Frontend package renamed to `intel-dashboard`
