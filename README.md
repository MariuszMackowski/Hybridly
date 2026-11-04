# Hybridly

Self-hosted training tracker for hybrid athletes: strength workouts logged from the phone with load suggestions, running data from COROS, recovery and progress in one place. Single user, runs on a home machine and is reached over Tailscale as a PWA.

**Stack:** FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL 16 · React + TypeScript (Vite) · nginx · Docker Compose · pytest / Vitest · GitHub Actions.

## Run

```bash
cp .env.example .env
docker compose up -d --build        # db, backend (migrates on start), web on :8080
```

Open http://localhost:8080.

## First-time data

Personal files live in `data/` (git-ignored, mounted read-only at `/data`):

```bash
docker compose run --rm backend python -m app.cli seed-exercises
docker compose run --rm backend python -m app.cli import-gravitus /data/<gravitus-export>.csv
```

Both commands are safe to re-run: existing exercises and workouts are skipped.

## Phone access (Tailscale)

On the home machine (once):

```bash
sudo tailscale serve --bg --https=443 http://localhost:8080
tailscale serve status            # shows https://<machine>.<tailnet>.ts.net
```

On the iPhone (Tailscale app connected): open that URL in Safari → Share → **Add to Home Screen**. The app opens full-screen; a workout in progress is kept on the phone until **Save**.

## Development

```bash
docker compose run --rm backend pytest -q          # backend tests (uses hybridly_test DB)
docker compose run --rm backend ruff check .
cd frontend && npm install && npm test && npm run typecheck
npm run dev                                         # Vite on :5173, API proxied to :8080
```

Design and plans: `docs/superpowers/`.
