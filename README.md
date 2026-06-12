# Test Case Assignment & Tracking Platform

A web-based platform for QA teams to import test cases, assign them, track execution,
integrate with JIRA, and visualize progress through dashboards and pivot analytics.
Built to handle **10,000+ test cases** and 50+ concurrent users.

> Status: backend is fully functional and verified with **8,972 real test cases**
> imported from `Master_Project_List.xlsx`. Frontend is scaffolded and ready to run
> once Node.js/npm is installed.

## Tech Stack

| Layer    | Technology                                                        |
| -------- | ---------------------------------------------------------------- |
| Backend  | FastAPI, SQLAlchemy 2, Pydantic v2, Alembic-ready, PostgreSQL/SQLite |
| Frontend | React 18, TypeScript, Material UI 6, TanStack (Table/Query), Recharts |
| Auth     | JWT + Role Based Access Control (`ADMIN`, `TEAM_LEAD`, `TEAM_MEMBER`) |

## Architecture (Clean Architecture)

Controllers (`api`) → Services (`services`) → Repositories (`repositories`) → Models.
Business logic never lives in controllers or UI components.

```
backend/app/{api,services,repositories,models,schemas,core,utils}
frontend/src/{pages,components,services,hooks,types,utils}
```

---

## Backend — Quick Start

Requires Python 3.11+ (tested on 3.13).

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# (optional) copy env file; defaults to local SQLite if you skip this
copy .env.example .env

# create tables + seed the admin user
.\.venv\Scripts\python.exe -m app.core.init_db

# run the API
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- API docs (Swagger): http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health
- Default admin: `admin@example.com` / `admin123` (configurable in `.env`)

### Import your real data

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.import_master_list "C:\Users\viverma\Desktop\Master_Project_List.xlsx"
```

The importer auto-detects the worksheet containing `Case ID` + `Title`, maps your
column names (e.g. `Test Case Execution Type` → execution type, `Automation_Deployment_Status`
→ deployment status), rejects duplicate Case IDs, and prints an import summary.

### Sample data for a demo (optional)

```powershell
.\.venv\Scripts\python.exe -m scripts.seed_sample_data
```

Switch to PostgreSQL by setting `DATABASE_URL` in `.env`:

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/test_tracker
```

---

## Frontend — Quick Start

Requires **Node.js 18+** (not currently installed on this machine — install from
https://nodejs.org first).

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api` to the backend on port 8000.

---

## Key API Endpoints (prefix `/api/v1`)

| Area          | Endpoint                                   |
| ------------- | ------------------------------------------ |
| Auth          | `POST /auth/login`, `GET /auth/me`         |
| Users (admin) | `GET/POST /users`, `PATCH /users/{id}`     |
| Test cases    | `GET /test-cases` (paginated, filtered)    |
| Imports       | `POST /imports/test-cases` (csv/xlsx)      |
| Assignments   | `POST /assignments`, `/bulk`, `/auto`, `PATCH /{id}/status` |
| Dashboards    | `/dashboards/executive,team-lead,team-member` |
| Analytics     | `/analytics/pivot/technology,release,assignee` |
| JIRA          | `POST /jira/defects` (abstracted via service) |

## Roles & Permissions

- **ADMIN** — full access, user management, delete.
- **TEAM_LEAD** — import, create/assign test cases, view all dashboards & analytics.
- **TEAM_MEMBER** — view & update only their own assignments. Cannot assign/reassign/delete.

RBAC is enforced in the backend (`require_roles`); the frontend role checks are
for UX only and are never trusted.
