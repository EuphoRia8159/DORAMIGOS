# AEGIS — Emergency Care Orchestration AI

Hackathon prototype with a Streamlit command dashboard and an optional FastAPI recommendation service.

> **Safety:** This project is a demonstration only. Hospital records, capacities, ambulance status, and arrival estimates in the Streamlit interface are synthetic. Do not use it for clinical triage, patient care, or real-world dispatch.

## Run locally

Use Python 3.10+.

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # macOS/Linux:
   # source .venv/bin/activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. In terminal 1, start the recommendation API:

   ```bash
   uvicorn backend_api:app --host 127.0.0.1 --port 8000
   ```

   API health: http://127.0.0.1:8000/health  
   Interactive API docs: http://127.0.0.1:8000/docs

4. In terminal 2, start the existing Streamlit frontend:

   ```bash
   streamlit run app.py
   ```

The Streamlit dashboard attempts to call `POST /api/v1/recommendations` and displays whether the backend API or local fallback is active. If the API is stopped, the dashboard remains usable in local demo mode. To change the API base URL, set `AEGIS_API_URL` (default `http://127.0.0.1:8000`).

## Integration notes

- The existing four-tab Streamlit UI is preserved: Command overview, Hospital & fleet, Incident log, and Event simulator.
- The API ranks the current synthetic hospital and ambulance snapshot submitted by the UI; it does not persist records.
- `backend_api.py` is intentionally self-contained so the demo can run without the incomplete legacy package imports.
- The legacy FastAPI entrypoint and its router imports are retained but are not required for this integrated demo launch path.
- The Indian hospital directory CSV is not automatically loaded by this prototype. Do not treat demo facility names or capacities as verified operational data.
- The recommendation rules and ETAs are illustrative, not clinically validated, and not a substitute for emergency dispatch systems.
