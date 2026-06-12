# Deploying to the Linux VM (`sfthyd158.silabs.com` / `10.207.132.78`)

This guide deploys the Test Management Tool on a single Linux VM:

- **Backend** — FastAPI served by Uvicorn, managed by **systemd**, listening on `127.0.0.1:8000`.
- **Frontend** — the React app is built to static files and served by **Nginx** on port **80**.
- **Nginx** also reverse-proxies `/api/` to the backend, so the whole app is same-origin
  (`http://sfthyd158.silabs.com`) and needs no CORS setup.
- **Database** — SQLite by default (simplest). A PostgreSQL option is in the last section.

Tables are created and the first admin user is seeded **automatically** the first time the
backend starts (driven by the `FIRST_ADMIN_*` values in `.env`).

Run everything below over SSH on the VM. Commands assume you have `sudo`.

---

## 1. Install OS packages

**Ubuntu / Debian:**
```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip nginx
# Node.js 20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

**RHEL / CentOS / Rocky / Alma:**
```bash
sudo dnf install -y git python3 python3-pip nginx
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo -E bash -
sudo dnf install -y nodejs
```

Verify: `python3 --version` (>=3.11 ideal), `node --version` (v20.x), `nginx -v`.

---

## 2. Create a service user and clone the repo

```bash
sudo useradd --system --create-home --home-dir /opt/testmgmt --shell /bin/bash testmgmt
sudo mkdir -p /opt/testmgmt/data
sudo chown -R testmgmt:testmgmt /opt/testmgmt

sudo -u testmgmt git clone https://github.com/silabs-VivekV/TestManagementTool.git /opt/testmgmt/TestManagementTool
```

---

## 3. Build the app (venv + frontend build)

```bash
sudo -u testmgmt bash /opt/testmgmt/TestManagementTool/deploy/setup.sh
```

This creates `backend/.venv`, installs `requirements.txt`, copies `backend/.env` from the
template, and runs `npm ci && npm run build` (output in `frontend/dist`).

---

## 4. Configure `backend/.env`

```bash
sudo -u testmgmt nano /opt/testmgmt/TestManagementTool/backend/.env
```

Set at minimum:

- `SECRET_KEY` — generate with:
  `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`
- `FIRST_ADMIN_EMAIL`, `FIRST_ADMIN_PASSWORD`, `FIRST_ADMIN_NAME` — your real admin login.
- `DATABASE_URL=sqlite:////opt/testmgmt/data/test_tracker.db` (note the **four** slashes).
- `MASTER_LIST_OUTPUT=/opt/testmgmt/data/Master_Project_List.xlsx`
- `ASSIGNMENT_SHEET_OUTPUT=/opt/testmgmt/data/Assigned_Test_Cases.xlsx`
- `TESTRAIL_USER` / `TESTRAIL_PASSWORD` (a TestRail API key is preferred over a password).
- `BACKEND_CORS_ORIGINS=http://sfthyd158.silabs.com,http://10.207.132.78`

> The default config ships **Windows** paths for the two `*_OUTPUT` settings — they **must**
> be changed to the Linux paths above or the TestRail sync / export will fail.

---

## 5. Install and start the backend service

```bash
sudo cp /opt/testmgmt/TestManagementTool/deploy/testmgmt-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now testmgmt-backend
sudo systemctl status testmgmt-backend --no-pager
```

Quick check (should return JSON):
```bash
curl http://127.0.0.1:8000/health
```

Logs: `sudo journalctl -u testmgmt-backend -f`

---

## 6. Configure Nginx

```bash
# Debian/Ubuntu layout:
sudo cp /opt/testmgmt/TestManagementTool/deploy/nginx-testmgmt.conf /etc/nginx/sites-available/testmgmt.conf
sudo ln -sf /etc/nginx/sites-available/testmgmt.conf /etc/nginx/sites-enabled/testmgmt.conf
sudo rm -f /etc/nginx/sites-enabled/default

# RHEL/CentOS layout (no sites-enabled): instead copy to conf.d
# sudo cp .../deploy/nginx-testmgmt.conf /etc/nginx/conf.d/testmgmt.conf

sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx
```

On RHEL, also allow Nginx to make outbound proxy connections:
```bash
sudo setsebool -P httpd_can_network_connect 1   # only if SELinux is enforcing
```

Nginx must be able to read the build dir. The `testmgmt` home is `/opt/testmgmt`; make sure
the path is traversable by the nginx user:
```bash
sudo chmod o+x /opt/testmgmt /opt/testmgmt/TestManagementTool /opt/testmgmt/TestManagementTool/frontend
```

---

## 7. Open the firewall (port 80)

**Ubuntu (ufw):**
```bash
sudo ufw allow 80/tcp
```
**RHEL (firewalld):**
```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --reload
```

---

## 8. Verify

From your laptop, open: **http://sfthyd158.silabs.com**

Log in with the `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD` you set. Then:
- Use **Sync from TestRail** (or **Import**) to load test cases, or migrate existing data (below).

---

## 9. Loading your existing data

Your local data lives in a SQLite file that is **not** in the repo. Two options:

- **Re-sync (cleanest):** on the running app, click **Sync from TestRail** then **Import**.
- **Copy the SQLite DB** from your Windows machine to the VM (only valid for the SQLite option):
  ```bash
  # from the VM, after stopping the service:
  sudo systemctl stop testmgmt-backend
  # scp your local test_tracker.db to /opt/testmgmt/data/test_tracker.db, then:
  sudo chown testmgmt:testmgmt /opt/testmgmt/data/test_tracker.db
  # If the copied DB predates the ETA feature, add the column once:
  sudo -u testmgmt /opt/testmgmt/TestManagementTool/backend/.venv/bin/python \
    -m scripts.add_eta_column            # run from the backend/ dir
  sudo systemctl start testmgmt-backend
  ```

---

## 10. Updating after a code change

```bash
cd /opt/testmgmt/TestManagementTool
sudo -u testmgmt git pull
sudo -u testmgmt ./backend/.venv/bin/pip install -r backend/requirements.txt
cd frontend && sudo -u testmgmt npm ci && sudo -u testmgmt npm run build
sudo systemctl restart testmgmt-backend
sudo systemctl reload nginx
```

---

## Optional: PostgreSQL instead of SQLite (recommended for many concurrent users)

```bash
# Ubuntu: sudo apt install -y postgresql
# RHEL:   sudo dnf install -y postgresql-server && sudo postgresql-setup --initdb && sudo systemctl enable --now postgresql
sudo -u postgres psql -c "CREATE USER testmgmt WITH PASSWORD 'CHANGE_ME';"
sudo -u postgres psql -c "CREATE DATABASE test_tracker OWNER testmgmt;"
```
Then set in `backend/.env`:
```
DATABASE_URL=postgresql+psycopg2://testmgmt:CHANGE_ME@localhost:5432/test_tracker
```
Restart the service. Tables are auto-created on startup. With Postgres you may add
`--workers 4` to the Uvicorn `ExecStart` in the systemd unit for more throughput.
