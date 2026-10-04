# Windows helper mirroring the Makefile targets.  Usage:  .\scripts\arena.ps1 <command>
param([Parameter(Position = 0)][string]$Command = "help", [string]$m = "")
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

switch ($Command) {
  "up"        { docker compose up -d --build }
  "down"      { docker compose down }
  "logs"      { docker compose logs -f }
  "restart"   { docker compose restart web worker }
  "build"     { docker compose build web }
  "runner"    { docker compose build runner-builder }
  "demo"      { docker compose exec web python -m app.scripts.seed_demo }
  "test"      { docker compose run --rm --no-deps -e DATA_DIR=/data/tests -e TEST_DATABASE_URL=sqlite:////tmp/test.db worker sh -c 'pytest -q; rc=$?; rm -rf /data/tests; exit $rc' }
  "lint"      { docker compose run --rm --no-deps worker sh -c "ruff format --check . && ruff check ." }
  "typecheck" { docker run --rm -v "${PWD}\frontend:/fe" -w /fe node:20-alpine npx tsc --noEmit }
  "dev"       { docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build }
  "dev-down"  { docker compose -f docker-compose.yml -f docker-compose.dev.yml down }
  "shell"     { docker compose exec web bash }
  "psql"      { docker compose exec db psql -U arena arena }
  "migrate"   { docker compose exec web alembic upgrade head }
  "migration" { docker compose exec web alembic revision --autogenerate -m "$m" }
  "clean"     { docker compose down -v }
  default     { Write-Host "Commands: up down logs restart build runner demo test lint typecheck dev dev-down shell psql migrate migration clean" }
}
