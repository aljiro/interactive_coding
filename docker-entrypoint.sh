#!/bin/sh
# Entrypoint for the app image: "web" (API + frontend) or "worker" (evaluation worker).
set -e
cd /app

wait_for_db() {
  python - <<'PY'
import os, sys, time
import sqlalchemy
url = os.environ["DATABASE_URL"]
for i in range(60):
    try:
        sqlalchemy.create_engine(url).connect().close()
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"waiting for database ({exc.__class__.__name__})...", flush=True)
        time.sleep(2)
sys.exit("database not reachable")
PY
}

case "${1:-web}" in
  web)
    wait_for_db
    alembic upgrade head
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="*"
    ;;
  worker)
    wait_for_db
    exec python -m app.worker
    ;;
  *)
    exec "$@"
    ;;
esac
