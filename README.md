# AEGIS — Emergency Care Orchestration Platform

**AEGIS** (Adaptive Emergency & Geographic Intelligence System) is a real-time emergency dispatch coordination platform that connects incoming emergencies with the most suitable hospitals and available ambulance units using AI-assisted triage, multi-criteria recommendation scoring, live telemetry simulation, and an IBM Z enterprise integration layer.

---

## Architecture Overview

```
aegis_backend/               # FastAPI application package
├── main.py                  # Application entrypoint, lifespan, WebSocket
├── config.py                # Pydantic-settings configuration
├── database.py              # SQLAlchemy engine, session, migration
├── models.py                # ORM models: Hospital, Emergency, Ambulance, etc.
├── schemas.py               # Pydantic request/response schemas
├── classifier.py            # AI emergency triage and classification engine
├── recommendation_engine.py # Multi-criteria hospital ranking engine
├── simulation.py            # Real-time simulation loop
├── events.py                # WebSocket broadcast and event audit log
├── seed_data.py             # Initial hospital / ambulance seeding
├── import_hospitals.py      # Excel hospital dataset importer
├── routers/                 # FastAPI API routers
│   ├── hospitals.py         # Hospital CRUD, proximity search
│   ├── ambulances.py        # Ambulance fleet management
│   ├── emergencies.py       # Emergency dispatch and triage
│   ├── recommendations.py   # Recommendation engine API
│   ├── analytics.py         # KPIs, event audit log
│   ├── simulation_api.py    # Simulation control endpoints
│   └── ibm_z_api.py         # IBM Z mainframe integration endpoints
└── ibm_z/                   # IBM Z enterprise integration layer
    ├── client.py            # z/OS Connect EE adapter (mock + live)
    ├── health_records.py    # Mainframe EHR patient lookup (CICS EHR1)
    ├── capacity_sync.py     # Hospital capacity sync to z/OS (CICS CAP1)
    ├── status.py            # IBM Z connectivity status service
    └── config.py            # IBM Z settings bridge

static/                      # Frontend static assets
├── index.html               # Main dashboard SPA
├── css/styles.css           # Application stylesheet
└── js/                      # Frontend JavaScript modules
    ├── app.js               # Main application logic
    ├── api.js               # REST API client
    ├── map.js               # Live map/dispatch visualization
    └── websocket.js         # Real-time WebSocket client

tests/                       # Automated test suite
run.py                       # Uvicorn server launcher
requirements.txt             # Python dependencies
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI (Python 3.11+) |
| ORM | SQLAlchemy 2.x |
| Database | SQLite (development), PostgreSQL-compatible |
| Validation | Pydantic v2 + pydantic-settings |
| HTTP Client | httpx (for IBM Z Connect adapter) |
| Real-time | WebSockets (FastAPI native) |
| Testing | pytest |
| Data Import | pandas + openpyxl |
| Enterprise | IBM z/OS Connect EE (mock sandbox + live mode) |

---

## Quick Start

### Prerequisites

- Python 3.11 or higher
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/EuphoRia8159/DORAMIGOS.git
cd DORAMIGOS

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
python run.py
```

The API will be available at: **http://127.0.0.1:8000**  
Interactive API docs (Swagger UI): **http://127.0.0.1:8000/docs**  
Dashboard frontend: **http://127.0.0.1:8000/**

---

## Configuration

All settings use the `AEGIS_` environment variable prefix. Copy `.env.example` (if provided) or set variables directly:

```env
AEGIS_DATABASE_URL=sqlite:///./aegis.db
AEGIS_DEBUG=True
AEGIS_HOST=127.0.0.1
AEGIS_PORT=8000
AEGIS_AUTO_SIMULATION_ENABLED=True

# IBM Z Integration (default: mock mode)
AEGIS_IBM_Z_MOCK_MODE=True
AEGIS_IBM_Z_CONNECT_URL=https://zosconnect.enterprise.internal:9443/zosConnect/services
AEGIS_IBM_Z_API_KEY=
```

> **Note:** Never commit `.env` files or real API keys/credentials to version control.

---

## API Endpoints

### Hospitals
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/hospitals` | List hospitals with search, filter, proximity |
| `GET` | `/api/hospitals/{id}` | Get single hospital |
| `POST` | `/api/hospitals` | Register new hospital |
| `PATCH` | `/api/hospitals/{id}/capacity` | Update live bed/ER capacity |

### Emergencies
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/emergencies` | Create emergency + AI triage + recommendations |
| `GET` | `/api/emergencies` | List emergencies |
| `GET` | `/api/emergencies/{id}` | Get emergency details |
| `POST` | `/api/emergencies/{id}/dispatch` | Dispatch ambulance to emergency |
| `PATCH` | `/api/emergencies/{id}/status` | Update emergency lifecycle status |

### Recommendations
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/recommendations/{emergency_id}` | Get ranked recommendations |
| `POST` | `/api/recommendations/{emergency_id}/recalculate` | Force recalculation |

### Ambulances
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/ambulances` | List fleet |
| `PATCH` | `/api/ambulances/{id}/location` | Update GPS telemetry |
| `POST` | `/api/ambulances/{id}/reset` | Reset to AVAILABLE |

### IBM Z Integration
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/ibm-z/status` | IBM Z connectivity status |
| `POST` | `/api/ibm-z/patient-lookup` | Mainframe EHR patient lookup |
| `POST` | `/api/ibm-z/sync-capacity` | Sync hospital capacity to z/OS ledger |

### Simulation & Analytics
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/simulation/status` | Simulation engine status |
| `POST` | `/api/simulation/start` | Start simulation |
| `POST` | `/api/simulation/stop` | Stop simulation |
| `POST` | `/api/simulation/tick` | Execute single simulation tick |
| `POST` | `/api/simulation/surge` | Trigger mass-casualty surge |
| `GET` | `/api/analytics/overview` | System-wide operational KPIs |
| `GET` | `/api/analytics/events` | Audit event log |

### WebSocket
| Path | Description |
|------|-------------|
| `ws://host/ws/events` | Real-time telemetry and event broadcast |

---

## Recommendation Engine

The engine scores hospitals across five weighted dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Clinical Capability | 35% | Specialty matching, cath lab, stroke center, trauma level |
| Travel Time (ETA) | 25% | Haversine distance + urban transit time estimate |
| Bed Availability | 20% | ICU and inpatient bed headroom |
| ER Congestion | 15% | Current ER load and diversion status |
| IBM Z Verification | 5% | Enterprise mainframe ledger verification bonus |

---

## Emergency Classification

The AI triage classifier uses keyword pattern matching and vital sign risk stratification to assign:

- **Category:** `CARDIAC_ARREST`, `ACUTE_STROKE`, `POLYTRAUMA`, `RESPIRATORY_FAILURE`, `SEVERE_BURN`, `PEDIATRIC_CRITICAL`, `GENERAL_MEDICAL`
- **Severity:** `CRITICAL`, `URGENT`, `MODERATE`, `LOW`
- **Required Specialties and Resources** (feeds into recommendation engine)

---

## IBM Z Integration

AEGIS includes a **high-fidelity IBM z/OS Connect EE mock sandbox** for demonstration. In mock mode:

- All CICS transactions (`AEG1`, `EHR1`, `CAP1`, `PNG1`) are simulated with realistic latency
- Patient EHR records use structured COBOL copybook data (`CPYEMERG`, `CPYCAPAC`)
- No real mainframe credentials are required

To connect to a live IBM z16/z15 mainframe:
```env
AEGIS_IBM_Z_MOCK_MODE=False
AEGIS_IBM_Z_CONNECT_URL=https://your-zos-connect-url:9443/zosConnect/services
AEGIS_IBM_Z_API_KEY=your-racf-jwt-token
```

---

## Hospital Dataset Import

To import the Indian hospital directory into AEGIS:

```bash
# Import all records (requires sweekar_hospital_cleaned-1.xlsx locally)
python -m aegis_backend.import_hospitals --file sweekar_hospital_cleaned-1.xlsx --sheet in

# Test with first 100 records
python -m aegis_backend.import_hospitals --file sweekar_hospital_cleaned-1.xlsx --limit 100
```

> **Note:** The Excel dataset file (`sweekar_hospital_cleaned-1.xlsx`) is excluded from the repository
> due to its large size (~6 MB) and the presence of institutional contact information (phone numbers,
> registration numbers). It must be obtained and placed locally before running the importer.

---

## Running Tests

```bash
# Run the full unit test suite (no live server required)
pytest tests/test_classifier.py tests/test_recommendation_engine.py \
       tests/test_ibm_z_integration.py tests/test_simulation.py -v

# Run all tests (live-server tests will be skipped if server is not running)
pytest tests/ -v
```

### Test Results (last verified)

```
tests/test_classifier.py::test_cardiac_arrest_classification       PASSED
tests/test_classifier.py::test_stroke_classification               PASSED
tests/test_classifier.py::test_polytrauma_classification           PASSED
tests/test_classifier.py::test_pediatric_critical_classification   PASSED
tests/test_recommendation_engine.py::test_distance_and_transit_calculation  PASSED
tests/test_recommendation_engine.py::test_recommendation_scoring_and_ranking PASSED
tests/test_ibm_z_integration.py::test_ibm_z_status_diagnostics    PASSED
tests/test_ibm_z_integration.py::test_ibm_z_patient_record_lookup PASSED
tests/test_ibm_z_integration.py::test_ibm_z_capacity_ledger_sync  PASSED
tests/test_simulation.py::test_simulation_status_and_tick          PASSED
tests/test_simulation.py::test_mass_casualty_surge_trigger         PASSED

11 passed, 1 warning (starlette/httpx deprecation — non-breaking)
```

---

## Security Notes

- Never commit `.env` files, API keys, or database credentials
- The SQLite database (`aegis.db`) is excluded from version control
- IBM Z integration runs in mock mode by default — no live credentials needed
- The hospital dataset file is excluded from the repository

---

## Contributors

- Kaushya Smirti — Backend architecture, AEGIS FastAPI implementation
- Rhea Yaramkota — Frontend, initial Streamlit prototype

---

## License

This project is part of the DORAMIGOS academic initiative.
