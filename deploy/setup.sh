#!/usr/bin/env bash
#
# App-level setup for the Test Management Tool.
# Run as the 'testmgmt' service user from anywhere; it locates the repo itself.
#
#   sudo -u testmgmt bash deploy/setup.sh
#
# Assumes OS packages are already installed: python3 + venv, nodejs (20 LTS), npm.
# See deploy/DEPLOY.md for the full runbook.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${DATA_DIR:-/opt/testmgmt/data}"

echo "==> Repo:  $REPO_DIR"
echo "==> Data:  $DATA_DIR"

mkdir -p "$DATA_DIR"

echo "==> Backend: creating virtualenv and installing dependencies"
cd "$REPO_DIR/backend"
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip wheel
./.venv/bin/pip install -r requirements.txt

if [ ! -f .env ]; then
  cp "$REPO_DIR/deploy/env.production.example" .env
  echo "==> Created backend/.env from template — EDIT IT before starting the service:"
  echo "    - SECRET_KEY, FIRST_ADMIN_PASSWORD"
  echo "    - DATABASE_URL, MASTER_LIST_OUTPUT, ASSIGNMENT_SHEET_OUTPUT"
  echo "    - TESTRAIL_USER / TESTRAIL_PASSWORD"
else
  echo "==> backend/.env already exists — leaving it untouched"
fi

echo "==> Frontend: installing dependencies and building"
cd "$REPO_DIR/frontend"
npm ci
npm run build

echo ""
echo "==> Done."
echo "    Next: edit backend/.env, then install the systemd unit and nginx config"
echo "    (see deploy/DEPLOY.md), and start the service."
