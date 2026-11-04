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

## COROS sync

Settings → **Connect COROS** uses the official COROS MCP server (OAuth with dynamic client registration + PKCE; EU endpoint by default, `COROS_SERVER_URL` to change).

- If the app is reachable over HTTPS (e.g. `tailscale serve`), set `PUBLIC_URL` in `.env` and COROS redirects straight back to `/api/coros/callback`.
- Otherwise the login ends on a `http://localhost:8765/callback?code=…` error page: paste that address into the box in Settings.

Sync runs in the Celery worker: once whenever the stack starts and on **Sync now**. It imports every non-strength activity (FIT file + COROS training load / TE) and stores the daily recovery and training-load snapshots. COROS allows 50 FIT downloads per day, so one run downloads at most 45; the rest follow on the next run. FIT files are kept in `data/fit/`. Runs can also be added by uploading `.fit` files on the Runs tab — the same activity from both sources is stored once.

## Running plan & home routines

- **Plan** tab → *Instructions for your AI coach*: copy the format description, send it to the coach, then import the YAML it returns (file or paste). CLI: `python -m app.cli import-plan /data/seed/<plan>.yaml`.
- A newer plan takes over from `max(its first week, today)`; earlier days keep the plan that was active then. Runs are matched to planned sessions automatically (same day, otherwise ±1 day if the distance is plausible) and compared: distance, pace vs. range, time in HR zone, interval laps.
- **Today** shows the planned run, week progress, coach notes, the strength template (with a cutback/taper hint) and the recovery view.
- Exercises, templates, the weekday template plan and home routines live under **Settings → Training setup**. Home routines: today's checklist on top; below, add YouTube links to the library, group them into routines (alternatives — doing one counts) and assign them to weekdays.

## Load & recovery

- One recovery % for gym and running together (COROS's own % shown alongside). Run load is the COROS training load; strength sets are scaled to the same range by set intensity (set e1RM vs. best e1RM of that exercise), unilateral sets count twice, warm-ups not at all.
- Fatigue decays exponentially (36 h overall, 48 h per muscle); capacity is 3 × the mean daily load of the last 42 days (min. 120). Constants: `backend/app/load/model.py`.
- Muscle map (front/back, white → red) with the most fatigued muscles listed; **Show all** expands to the full breakdown. **Load chart** opens the last 14 days of gym vs. cardio load.
- The logger stops suggesting weight increases (holds the weight, marked 💤) while overall recovery is below 40 % or a primary muscle of the exercise is ≥ 70 % fatigued.

## Development

```bash
docker compose run --rm backend pytest -q          # backend tests (uses hybridly_test DB)
docker compose run --rm backend ruff check .
cd frontend && npm install && npm test && npm run typecheck
npm run dev                                         # Vite on :5173, API proxied to :8080
```

Design and plans: `docs/superpowers/`.
