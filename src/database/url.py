import os
from urllib.parse import quote_plus

LOCAL_DATABASE_URL = "postgresql://intel:intel_secret@localhost:5432/intel_db"

URL_ENV_KEYS = (
    "DATABASE_PRIVATE_URL",
    "DATABASE_URL",
    "POSTGRES_PRIVATE_URL",
    "POSTGRES_URL",
)


def is_unresolved_reference(value: str) -> bool:
    return "${{" in value or "}}" in value


def normalize_postgres_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def build_url_from_pg_env() -> str:
    """Build a connection URL from Railway Postgres Connect variables (PGHOST, etc.)."""
    host = os.environ.get("PGHOST", "").strip()
    if not host or is_unresolved_reference(host):
        return ""

    user = os.environ.get("PGUSER", "postgres").strip()
    password = os.environ.get("PGPASSWORD", "").strip()
    port = os.environ.get("PGPORT", "5432").strip()
    database = os.environ.get("PGDATABASE", "railway").strip()

    for part in (user, password, port, database):
        if is_unresolved_reference(part):
            return ""

    auth = quote_plus(user)
    if password:
        auth = f"{auth}:{quote_plus(password)}"

    return f"postgresql://{auth}@{host}:{port}/{database}"


def resolve_database_url(explicit_url: str = "") -> str:
    """Resolve the best available database URL from environment variables."""
    candidates = [explicit_url, *[os.environ.get(key, "") for key in URL_ENV_KEYS]]
    for raw in candidates:
        value = (raw or "").strip()
        if not value or is_unresolved_reference(value):
            continue
        return normalize_postgres_url(value)

    built = build_url_from_pg_env()
    if built:
        return built

    if os.environ.get("RAILWAY_ENVIRONMENT"):
        return ""

    return LOCAL_DATABASE_URL


def database_diagnostics() -> dict:
    """Return which database-related env vars are present (for setup troubleshooting)."""
    keys = [
        *URL_ENV_KEYS,
        "PGHOST",
        "PGPORT",
        "PGUSER",
        "PGPASSWORD",
        "PGDATABASE",
        "RAILWAY_ENVIRONMENT",
    ]
    result = {}
    for key in keys:
        value = os.environ.get(key, "")
        if not value:
            result[key] = "missing"
        elif is_unresolved_reference(value):
            result[key] = "unresolved_reference"
        else:
            result[key] = "set"
    return result


def database_setup_error() -> str:
    diag = database_diagnostics()
    lines = [
        "PostgreSQL is not connected to this service.",
        "",
        "In Railway (takes ~2 minutes):",
        "  1. Project canvas → + New → Database → PostgreSQL",
        "  2. Click your new Postgres service → Connect → select Intel",
        "     (this adds DATABASE_URL and PGHOST variables automatically)",
        "  3. Redeploy Intel",
        "",
        "Or delete the broken variable and re-add it:",
        "  Intel → Variables → remove empty DATABASE_URL",
        "  → + New Variable → Add Reference → pick Postgres → DATABASE_URL",
        "",
        "Diagnostics:",
    ]
    for key, status in diag.items():
        lines.append(f"  {key}: {status}")
    return "\n".join(lines)
