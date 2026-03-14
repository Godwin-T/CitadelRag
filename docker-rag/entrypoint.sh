#!/usr/bin/env bash
set -euo pipefail

ALEMBIC_INI="/app/api/alembic.ini"
VERSIONS_DIR="/app/api/alembic/versions"
AUTO_MIGRATE="${AUTO_MIGRATE:-true}"
DB_WAIT_SECONDS="${DB_WAIT_SECONDS:-30}"

wait_for_db() {
  local deadline=$((SECONDS + DB_WAIT_SECONDS))
  while true; do
    if python - <<'PY'
import os
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL not set")
engine = create_engine(url)
with engine.connect() as conn:
    conn.execute(text("SELECT 1"))
engine.dispose()
PY
    then
      break
    fi
    if (( SECONDS >= deadline )); then
      echo "Database not ready after ${DB_WAIT_SECONDS}s" >&2
      exit 1
    fi
    sleep 1
  done
}

run_autogenerate() {
  mkdir -p "$VERSIONS_DIR"

  local before_list after_list
  before_list="$(mktemp)"
  after_list="$(mktemp)"

  find "$VERSIONS_DIR" -type f -name "*.py" -print | sort > "$before_list"

  local head_list
  head_list="$(alembic -c "$ALEMBIC_INI" heads | awk '{print $1}' | grep -E '^[0-9a-f]+' | sort | uniq || true)"
  if [[ -z "$head_list" ]]; then
    echo "No migration heads found. Generating initial revision."
    alembic -c "$ALEMBIC_INI" revision --autogenerate -m "initial"
  else
    alembic -c "$ALEMBIC_INI" revision --autogenerate -m "auto"
  fi

  find "$VERSIONS_DIR" -type f -name "*.py" -print | sort > "$after_list"
  local changed
  changed="$(comm -13 "$before_list" "$after_list" || true)"

  if [[ -z "$changed" ]]; then
    echo "No schema changes detected."
    rm -f "$before_list" "$after_list"
    return 0
  fi

  for file in $changed; do
    if [[ ! -f "$file" ]]; then
      continue
    fi
    if ! grep -q "op\." "$file"; then
      echo "Empty migration removed: $file"
      rm -f "$file"
      continue
    fi
    echo "Migration generated: $file"
  done

  rm -f "$before_list" "$after_list"
}

wait_for_db

if [[ "$AUTO_MIGRATE" != "false" && "$AUTO_MIGRATE" != "0" ]]; then
  run_autogenerate
fi

alembic -c "$ALEMBIC_INI" upgrade head

echo "Starting application..."

exec "$@"
