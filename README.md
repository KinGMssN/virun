# Virun

Virun is a travel planning application with a static HTML frontend and a FastAPI
backend. The repository is organized as a small monorepo:

```text
.
|-- frontend/                 # HTML app and image assets
|-- backend/
|   |-- app/                  # API, planner, auth, data and integrations
|   |-- frontend/             # Frontend bundled with the standalone backend repo
|   |-- migrations/           # SQLAlchemy and Alembic migrations
|   |-- scripts/              # Local and database utilities
|   |-- tests/                # Backend tests
|   |-- docs/                 # API examples
|   |-- supabase/             # Supabase SQL and seed assets
|   |-- Dockerfile
|   `-- requirements*.txt
|-- .github/workflows/        # CI and static-site deployment
|-- render.yaml               # Render service blueprint
`-- TODO.md                   # Delivery checklist
```

## Run locally

Start the API from `backend/`:

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. The API serves the frontend and image assets.
For the local frontend proxy on port 8001, start the API first, then from the
repository root run:

```powershell
python backend/scripts/local_frontend_proxy.py
```

Install dependencies from `backend/requirements-dev.txt` to run tests. Copy
`backend/.env.example` to `backend/.env` for local integrations and keep real
credentials private.

## Deploy

Render uses root `render.yaml` and builds `backend/Dockerfile` with the repository
root as its context. Set private provider and database values in Render's
environment settings. The GitHub Pages workflow publishes the frontend from
`frontend/`; set the repository's Pages source to **GitHub Actions**.

For API configuration and integrations, see
[`backend/README.md`](backend/README.md). Image credits are in attribution files
under `frontend/resources/images/`.
