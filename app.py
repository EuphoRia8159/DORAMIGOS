import math
import os
from datetime import datetime
import streamlit as st

try:
    import requests
except ImportError:  # API integration is optional; local demo mode remains available.
    requests = None

st.set_page_config(
    page_title="Emergency Care Orchestration AI",
    page_icon="🚑",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root{color-scheme:dark;--bg:#0B0F14;--surface:#111C24;--elev:#17252D;--teal:#14B8A6;--bright:#2DD4BF;--text:#F1F5F9;--muted:#9CB0B9;--border:#243640;--good:#34D399;--warn:#FBBF24;--bad:#FB7185}
html,body,[class*="css"],.stApp{font-family:'Manrope',sans-serif}.stApp{background:radial-gradient(ellipse at 88% 0%,rgba(20,184,166,.10),transparent 31%),linear-gradient(135deg,#0B0F14,#102027 52%,#0B0F14);color:var(--text)}
[data-testid="stHeader"]{background:rgba(11,15,20,.9)}.block-container{max-width:1500px;padding-top:1.35rem;padding-bottom:3rem}h1,h2,h3{color:#F1F5F9!important;letter-spacing:-.035em}p,label,[data-testid="stCaptionContainer"]{color:#B0BEC5}
[data-testid="stMetric"]{background:linear-gradient(145deg,#14232A,#101820);border:1px solid #243640;padding:17px 18px;border-radius:15px;box-shadow:0 10px 30px #0002}[data-testid="stMetricLabel"]{color:#9CB0B9!important;font-size:.78rem!important}[data-testid="stMetricValue"]{color:#F1F5F9!important;font-weight:800}
.stTabs [data-baseweb="tab-list"]{gap:8px;border-bottom:1px solid #243640}.stTabs [data-baseweb="tab"]{background:#111C24;border:1px solid #243640;border-radius:10px 10px 0 0;padding:11px 16px;color:#B0BEC5}.stTabs [aria-selected="true"]{color:#2DD4BF!important;border-color:#14B8A6!important;background:#102B2B!important}
.stButton>button,.stDownloadButton>button,button[kind="primary"]{border-radius:10px;border:1px solid #14B8A6;background:#14B8A6;color:#042F2E;font-weight:800;min-height:2.65rem;transition:all .2s ease}.stButton>button:hover,.stDownloadButton>button:hover{background:#2DD4BF;border-color:#2DD4BF;box-shadow:0 0 20px #14b8a62e;color:#042F2E}
input,textarea,[data-baseweb="select"]>div{background:#101820!important;color:#F1F5F9!important;border-color:#2A414A!important;border-radius:9px!important}[data-testid="stDataFrame"]{border:1px solid #243640;border-radius:12px;overflow:hidden}[data-testid="stForm"]{background:#111c24b8;border:1px solid #243640;border-radius:16px;padding:18px 20px 8px}hr{border-color:#243640!important}
.hero{display:flex;justify-content:space-between;gap:24px;align-items:center;padding:26px 28px;border:1px solid #24434A;border-radius:20px;background:radial-gradient(circle at 88% 15%,#14b8a629,transparent 29%),linear-gradient(115deg,#111c24f7,#0d1f22f5);margin-bottom:20px;box-shadow:0 18px 55px #0003}.eyebrow{font:500 11px 'DM Mono',monospace;letter-spacing:.15em;color:#2DD4BF;text-transform:uppercase;margin-bottom:9px}.hero-title{font-size:clamp(27px,3vw,39px);font-weight:800;line-height:1.1;letter-spacing:-.05em;color:#F1F5F9}.hero-sub{margin-top:10px;color:#AFC1C8;font-size:14px;max-width:720px}.live-pill{display:inline-flex;align-items:center;gap:8px;border:1px solid #28564F;background:#14b8a61a;color:#5EEAD4;border-radius:999px;padding:8px 12px;font:500 11px 'DM Mono',monospace;white-space:nowrap}.pulse{width:7px;height:7px;border-radius:50%;background:#34D399;box-shadow:0 0 12px #34d399b3;display:inline-block}.kicker{color:#2DD4BF;font:500 11px 'DM Mono',monospace;text-transform:uppercase;letter-spacing:.13em;margin:6px 0}.panel{background:linear-gradient(145deg,#111c24f5,#101820f5);border:1px solid #243640;border-radius:16px;padding:18px 20px;margin:8px 0 14px}.panel-title{color:#F1F5F9;font-weight:800;font-size:16px}.muted{color:#91A6AF;font-size:12px}.rec-card{background:radial-gradient(circle at 100% 0%,#14b8a622,transparent 35%),#111C24;border:1px solid #1D665F;border-radius:18px;padding:22px;box-shadow:0 0 32px #14b8a610;margin:12px 0 18px}.rec-label{color:#5EEAD4;font:500 11px 'DM Mono',monospace;text-transform:uppercase;letter-spacing:.12em}.rec-name{font-size:26px;color:#F1F5F9;font-weight:800;letter-spacing:-.04em;margin:6px 0 2px}.status{display:inline-block;border-radius:999px;padding:4px 9px;font:500 10px 'DM Mono',monospace}.status-good{color:#6EE7B7;border:1px solid #24604E;background:#34d39917}.status-warn{color:#FCD34D;border:1px solid #665224;background:#fbbf2417}.status-bad{color:#FDA4AF;border:1px solid #673341;background:#fb718517}.route-node{border:1px solid #29434A;border-radius:12px;padding:13px;background:#111C24;text-align:center}.footer-note{border-top:1px solid #243640;margin-top:28px;padding-top:14px;color:#8298A2;font-size:11px}
[data-testid="stSidebar"]{background:#0D151B}@media(max-width:760px){.block-container{padding:1rem .75rem 2rem}.hero{padding:20px;flex-direction:column;align-items:flex-start}.rec-name{font-size:22px}.stTabs [data-baseweb="tab"]{padding:9px 10px;font-size:12px}}@media(prefers-reduced-motion:reduce){*,*::before,*::after{transition:none!important;animation:none!important}}
</style>
<div class="hero"><div><div class="eyebrow">Emergency operations intelligence · Prototype</div><div class="hero-title">AEGIS <span style="color:#2DD4BF">/</span> Care orchestration</div><div class="hero-sub">A unified command view of simulated hospital capacity, compatible ambulance resources, and explainable destination recommendations.</div></div><div class="live-pill"><span class="pulse"></span> DEMO SYSTEM · SIMULATED DATA</div></div>
""", unsafe_allow_html=True)
st.warning("DEMONSTRATION ONLY — all hospital capacity, specialist availability, ambulance status, and travel estimates are simulated. This is not a clinical triage tool and must not be used for real dispatch decisions.")

# ------------------------- Simulated data -------------------------
# Values are fictional and deliberately not tied to real hospitals.
if "hospitals" not in st.session_state:
    st.session_state.hospitals = [
        {
            "id": "HOSP-A", "name": "Demo Hospital A",
            "emergency_department": True, "specialties": ["cardiology", "trauma"],
            "icu_total": 12, "icu_available": 0, "emergency_beds_available": 1,
            "workload": "High", "status_updated": datetime.now(),
            "data_mode": "Simulated",
        },
        {
            "id": "HOSP-B", "name": "Demo Hospital B",
            "emergency_department": True, "specialties": ["cardiology", "respiratory", "trauma"],
            "icu_total": 15, "icu_available": 3, "emergency_beds_available": 4,
            "workload": "Medium", "status_updated": datetime.now(),
            "data_mode": "Simulated",
        },
        {
            "id": "HOSP-C", "name": "Demo Hospital C",
            "emergency_department": True, "specialties": ["respiratory", "trauma", "pediatric"],
            "icu_total": 10, "icu_available": 2, "emergency_beds_available": 3,
            "workload": "Low", "status_updated": datetime.now(),
            "data_mode": "Simulated",
        },
        {
            "id": "HOSP-D", "name": "Demo Hospital D",
            "emergency_department": True, "specialties": ["cardiology", "respiratory", "pediatric"],
            "icu_total": 8, "icu_available": 1, "emergency_beds_available": 2,
            "workload": "Medium", "status_updated": datetime.now(),
            "data_mode": "Simulated",
        },
    ]

if "ambulances" not in st.session_state:
    st.session_state.ambulances = [
        {"id": "AMB-01", "status": "Available", "equipment": "Advanced", "eta_to_patient_min": 6},
        {"id": "AMB-02", "status": "Available", "equipment": "Basic", "eta_to_patient_min": 9},
        {"id": "AMB-03", "status": "Assigned", "equipment": "Advanced", "eta_to_patient_min": 4},
    ]

if "incidents" not in st.session_state:
    st.session_state.incidents = []
if "event_log" not in st.session_state:
    st.session_state.event_log = []

SCENARIOS = {
    "Cardiac emergency (demo)": {
        "specialty": "cardiology", "requires_icu": True, "ambulance_equipment": "Advanced"
    },
    "Severe respiratory distress (demo)": {
        "specialty": "respiratory", "requires_icu": True, "ambulance_equipment": "Advanced"
    },
    "Major trauma (demo)": {
        "specialty": "trauma", "requires_icu": False, "ambulance_equipment": "Advanced"
    },
    "Critical pediatric emergency (demo)": {
        "specialty": "pediatric", "requires_icu": True, "ambulance_equipment": "Advanced"
    },
}

WORKLOAD_SCORE = {"Low": 1, "Medium": 2, "High": 3}

def calculate_travel_minutes(ambulance, hospital):
    """Clearly simulated travel estimate; not a routing or traffic service."""
    # Stable fictional estimates so the demo is reproducible.
    hospital_offset = {"HOSP-A": 8, "HOSP-B": 12, "HOSP-C": 17, "HOSP-D": 14}
    return ambulance["eta_to_patient_min"] + hospital_offset[hospital["id"]]

def match_hospitals(scenario_name):
    """Ask the backend API to rank the current snapshot; use local fallback if it is offline."""
    api_url = os.getenv("AEGIS_API_URL", "http://127.0.0.1:8000").rstrip("/")
    if requests is not None:
        payload = {
            "scenario_name": scenario_name,
            "hospitals": [
                {k: v for k, v in h.items() if k in {
                    "id", "name", "emergency_department", "specialties", "icu_total",
                    "icu_available", "emergency_beds_available", "workload", "data_mode"
                }}
                for h in st.session_state.hospitals
            ],
            "ambulances": [
                {k: v for k, v in a.items() if k in {"id", "status", "equipment", "eta_to_patient_min"}}
                for a in st.session_state.ambulances
            ],
        }
        try:
            response = requests.post(
                f"{api_url}/api/v1/recommendations", json=payload, timeout=1.2
            )
            response.raise_for_status()
            data = response.json()
            if data.get("engine") == "backend-api" and isinstance(data.get("recommendations"), list):
                st.session_state.recommendation_engine_mode = "Connected backend API"
                return data["recommendations"]
        except (requests.RequestException, ValueError, TypeError):
            pass

    # Standalone fallback keeps the demo usable when the API server is not running.
    st.session_state.recommendation_engine_mode = "Local fallback (API offline)"
    requirements = SCENARIOS[scenario_name]
    available_ambulances = [
        a for a in st.session_state.ambulances
        if a["status"] == "Available"
        and (requirements["ambulance_equipment"] != "Advanced" or a["equipment"] == "Advanced")
    ]
    results = []
    for hospital in st.session_state.hospitals:
        reasons = []
        eligible = True
        if not hospital["emergency_department"]:
            eligible = False
            reasons.append("Emergency department unavailable")
        if requirements["specialty"] not in hospital["specialties"]:
            eligible = False
            reasons.append(f"Required service unavailable: {requirements['specialty']}")
        if requirements["requires_icu"] and hospital["icu_available"] < 1:
            eligible = False
            reasons.append("No simulated ICU beds available")
        if hospital["emergency_beds_available"] < 1:
            eligible = False
            reasons.append("No simulated emergency beds available")
        if not available_ambulances:
            eligible = False
            reasons.append("No available ambulance meets the configured equipment requirement")
        if eligible:
            ambulance = min(available_ambulances, key=lambda a: calculate_travel_minutes(a, hospital))
            travel = calculate_travel_minutes(ambulance, hospital)
            score = travel + WORKLOAD_SCORE[hospital["workload"]] * 3
            reasons = [
                "Configured service requirement matched",
                "Simulated emergency capacity available",
                "Simulated ICU capacity available" if requirements["requires_icu"] else "ICU not required by this demo scenario",
                f"Compatible ambulance: {ambulance['id']}",
                f"Simulated estimated arrival: {travel} minutes",
            ]
        else:
            ambulance, travel, score = None, None, None
        results.append({
            "hospital": hospital, "eligible": eligible, "ambulance": ambulance,
            "travel": travel, "score": score, "reasons": reasons,
        })
    return sorted(results, key=lambda r: (not r["eligible"], r["score"] if r["score"] is not None else math.inf))

def record_event(event_name, description):
    st.session_state.event_log.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "event": event_name,
        "description": description,
    })

# ------------------------- Dashboard -------------------------
eligible_ambulances = sum(a["status"] == "Available" for a in st.session_state.ambulances)
available_icu = sum(h["icu_available"] for h in st.session_state.hospitals)
m1, m2, m3, m4 = st.columns(4)
m1.metric("Open incidents", len(st.session_state.incidents))
m2.metric("Demo hospitals", len(st.session_state.hospitals))
m3.metric("Available ambulances", eligible_ambulances)
m4.metric("Simulated ICU beds available", available_icu)

tab_match, tab_resources, tab_incidents, tab_events = st.tabs([
    "◈ Command overview", "▦ Hospital & fleet", "≋ Incident log", "⚡ Event simulator"
])

with tab_match:
    st.markdown('<div class="kicker">01 / Dispatch workflow</div>', unsafe_allow_html=True)
    st.subheader("Evaluate an emergency scenario")
    st.caption("Choose a predefined demo scenario. These mappings are illustrative and not clinically validated.")
    with st.form("matching_form"):
        scenario_name = st.selectbox("Demo emergency scenario", list(SCENARIOS.keys()))
        incident_location = st.text_input("Incident location (demo)", value="Hyderabad — demo location")
        description = st.text_area("Optional notes", placeholder="Enter non-identifying demo notes")
        match_submitted = st.form_submit_button("Evaluate hospitals")
    if match_submitted:
        if not incident_location.strip():
            st.error("Enter a demo incident location.")
        else:
            results = match_hospitals(scenario_name)
            eligible = [r for r in results if r["eligible"]]
            st.session_state.last_match = {
                "scenario": scenario_name, "location": incident_location.strip(),
                "description": description.strip(), "results": results,
                "recommended_id": eligible[0]["hospital"]["id"] if eligible else None,
                "created_at": datetime.now().strftime("%H:%M:%S"),
            }
            st.session_state.incidents.insert(0, {
                "id": len(st.session_state.incidents) + 1,
                "time": datetime.now().strftime("%H:%M:%S"),
                "location": incident_location.strip(),
                "scenario": scenario_name,
                "status": "Evaluated",
                "recommended_hospital": eligible[0]["hospital"]["name"] if eligible else "No eligible destination",
            })
    if "last_match" in st.session_state:
        match = st.session_state.last_match
        # Always recompute against current simulated resource state so changes show immediately.
        current_results = match_hospitals(match["scenario"])
        st.caption(f"Recommendation engine: {st.session_state.get('recommendation_engine_mode', 'Local fallback (API offline)')} · demo data only")
        eligible_now = [r for r in current_results if r["eligible"]]
        current_id = eligible_now[0]["hospital"]["id"] if eligible_now else None
        previous_id = match.get("recommended_id")
        if current_id != previous_id:
            st.info("Resource state changed; the recommendation has been recalculated.")
            st.session_state.last_match["recommended_id"] = current_id
            st.session_state.last_match["results"] = current_results
        st.markdown(f"**Scenario:** {match['scenario']}  \n**Location:** {match['location']}")
        if eligible_now:
            top = eligible_now[0]
            st.markdown(f'<div class="rec-card"><div class="rec-label">✦ Current recommended destination</div><div class="rec-name">{top["hospital"]["name"]}</div><div style="color:#B0BEC5;font-size:13px">Compatible unit <b style="color:#5EEAD4">{top["ambulance"]["id"]}</b> &nbsp;·&nbsp; Simulated arrival <b style="color:#5EEAD4">{top["travel"]} min</b></div><hr style="border-color:#24443F"><div class="muted">Ranked using configured demo rules, synthetic capacity and fictional ETA offsets.</div></div>', unsafe_allow_html=True)
            for reason in top["reasons"]:
                st.write(f"✓ {reason}")
        else:
            st.error("No eligible destination could be confirmed from the current simulated data. Do not use this prototype for real-world dispatch.")
        st.subheader("Hospital eligibility and ranking")
        rows = []
        for r in current_results:
            h = r["hospital"]
            rows.append({
                "Hospital": h["name"],
                "Eligible": "Yes" if r["eligible"] else "No",
                "Simulated ICU beds": f"{h['icu_available']} / {h['icu_total']}",
                "Emergency beds": h["emergency_beds_available"],
                "Workload": h["workload"],
                "Ambulance": r["ambulance"]["id"] if r["ambulance"] else "—",
                "Simulated arrival (min)": r["travel"] if r["travel"] is not None else "—",
                "Decision details": "; ".join(r["reasons"]),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="panel"><div class="kicker">AWAITING ASSESSMENT</div><div class="panel-title">No active demo recommendation</div><div class="muted">Evaluate a scenario to reveal ranked destinations, compatible units and the factors behind the result.</div></div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.markdown('<div class="route-node">⌖<br><b>Scenario</b><div class="muted">Configured needs</div></div>', unsafe_allow_html=True)
        c2.markdown('<div class="route-node" style="color:#2DD4BF">⇢<br><b>Eligibility</b><div class="muted">Capacity checks</div></div>', unsafe_allow_html=True)
        c3.markdown('<div class="route-node">✦<br><b>Recommend</b><div class="muted">Explainable ranking</div></div>', unsafe_allow_html=True)

with tab_resources:
    st.markdown('<div class="kicker">03 / Resource telemetry</div>', unsafe_allow_html=True)
    st.subheader("Simulated hospital capacity")
    hospital_rows = []
    for h in st.session_state.hospitals:
        hospital_rows.append({
            "ID": h["id"], "Hospital": h["name"], "Emergency dept": "Yes" if h["emergency_department"] else "No",
            "Services": ", ".join(h["specialties"]), "ICU available / total": f"{h['icu_available']} / {h['icu_total']}",
            "Emergency beds available": h["emergency_beds_available"], "Workload": h["workload"],
            "Updated": h["status_updated"].strftime("%H:%M:%S"), "Data mode": h["data_mode"],
        })
    st.dataframe(hospital_rows, use_container_width=True, hide_index=True)

    st.subheader("Simulated ambulance fleet")
    st.dataframe(st.session_state.ambulances, use_container_width=True, hide_index=True)
    st.caption("Travel estimates are generated from fixed demo offsets, not a live road-routing or traffic service.")

with tab_incidents:
    st.markdown('<div class="kicker">04 / Audit trail</div>', unsafe_allow_html=True)
    st.subheader("Incident history")
    if st.session_state.incidents:
        st.dataframe(st.session_state.incidents, use_container_width=True, hide_index=True)
        csv = __import__("pandas").DataFrame(st.session_state.incidents).to_csv(index=False).encode("utf-8")
        st.download_button("Download incident log (CSV)", csv, "demo_incidents.csv", "text/csv")
    else:
        st.info("No incidents evaluated yet.")

with tab_events:
    st.markdown('<div class="kicker">05 / Scenario lab</div>', unsafe_allow_html=True)
    st.subheader("Simulate a resource update")
    st.write("Trigger an event to change the simulated state. The matching engine reevaluates the last scenario on the next app rerun.")
    hospital_options = {h["name"]: h["id"] for h in st.session_state.hospitals}
    selected_hospital_name = st.selectbox("Hospital affected", list(hospital_options.keys()))
    selected_hospital_id = hospital_options[selected_hospital_name]
    event_type = st.selectbox("Event type", [
        "ICU bed occupied (-1)", "ICU bed released (+1)",
        "Emergency bed occupied (-1)", "Emergency bed released (+1)",
        "Workload changed to High", "Workload changed to Low",
    ])
    if st.button("Apply simulated hospital event"):
        hospital = next(h for h in st.session_state.hospitals if h["id"] == selected_hospital_id)
        if event_type == "ICU bed occupied (-1)":
            if hospital["icu_available"] > 0:
                hospital["icu_available"] -= 1
                record_event("ICU_BED_OCCUPIED", f"{hospital['name']}: available ICU beds decreased to {hospital['icu_available']}")
            else:
                st.warning("No available simulated ICU beds remain; state unchanged.")
        elif event_type == "ICU bed released (+1)":
            if hospital["icu_available"] < hospital["icu_total"]:
                hospital["icu_available"] += 1
                record_event("ICU_BED_RELEASED", f"{hospital['name']}: available ICU beds increased to {hospital['icu_available']}")
            else:
                st.warning("All simulated ICU beds are already available; state unchanged.")
        elif event_type == "Emergency bed occupied (-1)":
            if hospital["emergency_beds_available"] > 0:
                hospital["emergency_beds_available"] -= 1
                record_event("EMERGENCY_BED_OCCUPIED", f"{hospital['name']}: emergency beds decreased to {hospital['emergency_beds_available']}")
            else:
                st.warning("No available simulated emergency beds remain; state unchanged.")
        elif event_type == "Emergency bed released (+1)":
            hospital["emergency_beds_available"] += 1
            record_event("EMERGENCY_BED_RELEASED", f"{hospital['name']}: emergency beds increased to {hospital['emergency_beds_available']}")
        elif event_type == "Workload changed to High":
            hospital["workload"] = "High"
            record_event("HOSPITAL_WORKLOAD_CHANGED", f"{hospital['name']}: workload changed to High")
        elif event_type == "Workload changed to Low":
            hospital["workload"] = "Low"
            record_event("HOSPITAL_WORKLOAD_CHANGED", f"{hospital['name']}: workload changed to Low")
        hospital["status_updated"] = datetime.now()
        st.rerun()

    st.subheader("Simulate an ambulance status change")
    ambulance_options = {a["id"]: a["id"] for a in st.session_state.ambulances}
    selected_ambulance_id = st.selectbox("Ambulance", list(ambulance_options.keys()))
    ambulance_status = st.selectbox("Set status to", ["Available", "Assigned", "Out of service"])
    if st.button("Update ambulance status"):
        ambulance = next(a for a in st.session_state.ambulances if a["id"] == selected_ambulance_id)
        old_status = ambulance["status"]
        ambulance["status"] = ambulance_status
        record_event("AMBULANCE_STATUS_CHANGED", f"{ambulance['id']}: {old_status} → {ambulance_status}")
        st.rerun()

    st.subheader("Event history")
    if st.session_state.event_log:
        st.dataframe(st.session_state.event_log, use_container_width=True, hide_index=True)
    else:
        st.info("No simulated events yet.")

st.markdown('<div class="footer-note">AEGIS · EMERGENCY CARE ORCHESTRATION AI &nbsp; / &nbsp; Hackathon prototype. All facility names, capacity, status and ETAs are synthetic. Not for clinical triage or real-world dispatch. No live map, routing, hospital feed, or ambulance integration is connected.</div>', unsafe_allow_html=True)
