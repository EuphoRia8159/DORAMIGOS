# AEGIS — Emergency Care Orchestration AI

AEGIS is an emergency-care coordination prototype combining a Streamlit command dashboard with a FastAPI backend for hospital discovery, ambulance coordination, emergency workflows, recommendations, simulation, analytics, and IBM Z integration.

> **Safety notice:** This is a demonstration project, not a clinically validated medical system. Data, capacities, ambulance statuses, and arrival estimates may be simulated. Do not use it for real-world triage, patient care, or emergency dispatch.

## Live Demo

- **Streamlit frontend:** https://doramigos-frontend.onrender.com
- **FastAPI backend:** https://doramigos-api.onrender.com
- **API documentation:** https://doramigos-api.onrender.com/docs
- **Backend health check:** https://doramigos-api.onrender.com/health

> **Integration note:** The deployed project uses a sandbox simulation. IBM Z integration is in mock/simulation mode; these links do not represent a live IBM Z mainframe or live hospital-system connection.

## Architecture

- **Streamlit frontend:** `app.py`
- **FastAPI entry point:** `aegis_backend/main.py`
- **Backend package:** `aegis_backend/`
- **API routers:** `aegis_backend/routers/`
- **IBM Z integration modules:** `aegis_backend/ibm_z/`
- **Static HTML/CSS/JavaScript frontend:** `static/`
- **Tests:** `tests/`

The Streamlit interface and static web interface are separate frontend options. The FastAPI application serves the static frontend at `/` by default. Streamlit runs separately and should be used when working with the Streamlit dashboard.

## Requirements

Use Python 3.10 or newer. Install the dependencies listed in `requirements.txt`.

## Run the Streamlit frontend

From the repository root, create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows Git Bash:

```bash
source .venv/Scripts/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Start Streamlit:

```bash
streamlit run app.py
```

Streamlit will print the local URL in the terminal.

## Run the FastAPI backend

Open a second terminal in the repository root and activate the same virtual environment.

Start the API:

```bash
python -m uvicorn aegis_backend.main:app --host 127.0.0.1 --port 8000
```

API base URL:

`http://127.0.0.1:8000`

Interactive API documentation:

`http://127.0.0.1:8000/docs`

Health endpoint:

`http://127.0.0.1:8000/health`

The backend uses SQLite by default and may initialize a local `aegis.db` database. Its simulation is enabled by default. IBM Z integration is configured for mock mode by default; a real enterprise connection is not implied.

## Backend modules

- `aegis_backend/classifier.py` — emergency classification.
- `aegis_backend/config.py` — application and integration settings.
- `aegis_backend/database.py` — database setup and sessions.
- `aegis_backend/events.py` — event and WebSocket management.
- `aegis_backend/models.py` — database models.
- `aegis_backend/recommendation_engine.py` — recommendation logic.
- `aegis_backend/schemas.py` — request and response schemas.
- `aegis_backend/seed_data.py` — baseline demonstration data.
- `aegis_backend/simulation.py` — simulation engine.
- `aegis_backend/import_hospitals.py` — hospital data import functionality.

### API routers

The `aegis_backend/routers/` package contains endpoints for hospitals, ambulances, emergencies, recommendations, simulation, IBM Z integration, and analytics.

### IBM Z modules

The `aegis_backend/ibm_z/` package contains the IBM Z client, configuration, capacity synchronization, health-record integration, and status handling.

## Static web frontend

The separate static frontend is located in `static/`:

- `static/index.html`
- `static/css/styles.css`
- `static/js/api.js`
- `static/js/app.js`
- `static/js/map.js`
- `static/js/websocket.js`

When the FastAPI server is running, its root route serves `static/index.html` and static assets are mounted under `/static`.

## Tests

Run the test suite from the repository root:

```bash
python -m pytest
```

Tests may require additional environment configuration or running services. Passing tests is not a substitute for validating the application before any real-world use.

## Configuration

The backend supports environment variables with the `AEGIS_` prefix and can read a local `.env` file. Important settings include the database URL, server host and port, simulation configuration, recommendation weights, CORS origins, and IBM Z options.

Do not commit credentials, API keys, private environment files, or production connection details.

## Development and integration notes

- Keep the Streamlit frontend in `app.py` separate from the FastAPI entry point in `aegis_backend/main.py`.
- Review API request and response schemas before connecting the Streamlit UI to backend endpoints.
- Verify endpoint behavior and run tests after integration.
- Treat simulated hospital, ambulance, emergency, and telemetry information as demonstration data unless independently verified.
