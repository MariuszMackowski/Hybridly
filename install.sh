#!/usr/bin/env bash
# Hybridly installer / updater.
#   curl -fsSL https://raw.githubusercontent.com/MariuszMackowski/Hybridly/main/install.sh | bash
# Re-run it any time to update. Env overrides: HYBRIDLY_DIR, WEB_PORT, TIMEZONE, HYBRIDLY_AUTOSTART=yes|no.
set -euo pipefail

REPO_URL="https://github.com/MariuszMackowski/Hybridly.git"
DIR="${HYBRIDLY_DIR:-$HOME/hybridly}"

say() { printf '\033[1;33m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mError:\033[0m %s\n' "$*" >&2; exit 1; }

# Ask on the terminal even when the script itself is piped from curl; fall back to the default.
ask() {
  local prompt="$1" default="$2" answer=""
  if (: </dev/tty) 2>/dev/null; then
    read -r -p "$prompt [$default]: " answer </dev/tty || true
  fi
  echo "${answer:-$default}"
}

require() {
  command -v git >/dev/null || die "git is not installed."
  command -v docker >/dev/null || die "Docker is not installed: https://docs.docker.com/engine/install/"
  docker compose version >/dev/null 2>&1 || die "Docker Compose v2 is missing (docker compose …)."
  docker info >/dev/null 2>&1 || die "Cannot talk to Docker. Is it running, and is $USER in the docker group?"
}

fetch_code() {
  if [ -f docker-compose.yml ] && [ -d .git ] && grep -q '^name: hybridly' docker-compose.yml; then
    DIR="$(pwd)"
  fi
  if [ -d "$DIR/.git" ]; then
    say "Updating $DIR"
    git -C "$DIR" pull --ff-only
  else
    say "Cloning into $DIR"
    git clone --depth 1 "$REPO_URL" "$DIR"
  fi
  cd "$DIR"
}

detect_timezone() {
  timedatectl show -p Timezone --value 2>/dev/null \
    || cat /etc/timezone 2>/dev/null \
    || echo "Europe/Warsaw"
}

write_env() {
  if [ -f .env ]; then
    say "Keeping existing .env"
    return
  fi
  local port tz password
  port="${WEB_PORT:-$(ask 'Web port' 8080)}"
  tz="${TIMEZONE:-$(ask 'Timezone' "$(detect_timezone)")}"
  password="$(head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 24)"
  cat >.env <<EOF
POSTGRES_USER=hybridly
POSTGRES_PASSWORD=$password
POSTGRES_DB=hybridly
WEB_PORT=$port
TIMEZONE=$tz
UID=$(id -u)
GID=$(id -g)

# HTTPS URL of this machine (e.g. Tailscale) — enables the direct COROS login redirect
PUBLIC_URL=
EOF
  chmod 600 .env
  say "Created .env (random database password)"
}

# The backend migrates the database before serving, so a healthy API means the tables exist.
wait_for_backend() {
  local probe="import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"
  for _ in $(seq 1 60); do
    docker compose exec -T backend python -c "$probe" >/dev/null 2>&1 && return 0
    sleep 2
  done
  die "Backend did not come up; check: docker compose logs backend"
}

start_stack() {
  mkdir -p data/fit
  say "Building and starting containers (first build takes a few minutes)"
  docker compose up -d --build
  wait_for_backend
  say "Adding the starter exercise catalog"
  docker compose exec -T backend python -m app.cli seed-exercises >/dev/null
}

install_autostart() {
  local choice="${HYBRIDLY_AUTOSTART:-$(ask 'Start Hybridly on boot (systemd, needs sudo)? yes/no' yes)}"
  case "$choice" in [Yy]*) ;; *) return 0 ;; esac
  command -v systemctl >/dev/null || { say "No systemd here, skipping autostart"; return 0; }
  sudo tee /etc/systemd/system/hybridly.service >/dev/null <<EOF
[Unit]
Description=Hybridly (docker compose)
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=$USER
WorkingDirectory=$DIR
ExecStart=/usr/bin/env docker compose up -d
ExecStop=/usr/bin/env docker compose stop

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable docker hybridly >/dev/null
  say "Autostart enabled (hybridly.service)"
}

main() {
  require
  fetch_code
  write_env
  start_stack
  install_autostart
  local port
  port="$(grep -E '^WEB_PORT=' .env | cut -d= -f2)"
  say "Done. Open http://localhost:${port:-8080} (or this machine's address on your network)."
}

main "$@"
