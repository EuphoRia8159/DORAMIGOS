/**
 * AEGIS Emergency Care Orchestration AI
 * Main Frontend Application Controller
 */

class AEGISApp {
    constructor() {
        this.hospitals = [];
        this.ambulances = [];
        this.emergencies = [];
        this.activeEmergencyId = null;
        this.recommendations = [];
        this.events = [];
        this.overview = null;
        this.radarMap = null;
        this.pendingDispatchHospitalId = null;

        this.init();
    }

    async init() {
        console.log("Initializing AEGIS Command Center...");

        // Setup Radar Canvas Map
        this.radarMap = new window.AEGISRadarMap('map-canvas');

        // Setup Navigation Tabs
        this.bindTabs();

        // Setup Forms and Buttons
        this.bindControls();

        // Connect Real-time WebSocket
        window.aegisWS.connect();
        window.aegisWS.subscribe((payload) => this.handleWebSocketEvent(payload));

        // Initial Data Fetch
        await this.refreshAll();

        // Poll fallback every 8 seconds if WS disconnected
        setInterval(() => {
            if (!window.aegisWS.isConnected) {
                this.refreshAll();
            }
        }, 8000);
    }

    bindTabs() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                tabBtns.forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

                btn.classList.add('active');
                const targetId = btn.getAttribute('data-tab');
                const targetContent = document.getElementById(targetId);
                if (targetContent) targetContent.classList.add('active');

                // If map tab activated or resized, retrigger canvas projection
                if (this.radarMap) {
                    this.radarMap.initCanvas();
                }
            });
        });
    }

    bindControls() {
        // Preset Scenarios
        document.querySelectorAll('.scenario-pill').forEach(pill => {
            pill.addEventListener('click', () => {
                const type = pill.getAttribute('data-scenario');
                this.loadScenario(type);
            });
        });

        // Emergency Intake Form Submission
        const form = document.getElementById('emergency-form');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitEmergency();
            });
        }

        // Simulation Controls
        const btnToggleSim = document.getElementById('btn-toggle-sim');
        if (btnToggleSim) {
            btnToggleSim.addEventListener('click', () => this.toggleSimulation());
        }

        const btnStepSim = document.getElementById('btn-step-sim');
        if (btnStepSim) {
            btnStepSim.addEventListener('click', () => this.stepSimulation());
        }

        const btnSurgeModal = document.getElementById('btn-open-surge-modal');
        if (btnSurgeModal) {
            btnSurgeModal.addEventListener('click', () => this.openSurgeModal());
        }

        // Surge Form
        const surgeForm = document.getElementById('surge-form');
        if (surgeForm) {
            surgeForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.triggerSurgeIncident();
            });
        }

        // Dispatch Modal Close
        const closeDispatchBtn = document.getElementById('btn-close-dispatch-modal');
        if (closeDispatchBtn) {
            closeDispatchBtn.addEventListener('click', () => {
                document.getElementById('dispatch-modal').classList.remove('active');
            });
        }

        const closeSurgeBtn = document.getElementById('btn-close-surge-modal');
        if (closeSurgeBtn) {
            closeSurgeBtn.addEventListener('click', () => {
                document.getElementById('surge-modal').classList.remove('active');
            });
        }

        // IBM Z Patient Lookup Form
        const ehrForm = document.getElementById('ibm-z-ehr-form');
        if (ehrForm) {
            ehrForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.lookupPatientEHR();
            });
        }
    }

    loadScenario(type) {
        const scenarios = {
            cardiac: {
                location: "7th Ave & 34th St, Penn Station Plaza",
                lat: 40.7505,
                lon: -73.9934,
                caller: "Officer Miller",
                phone: "911-DIRECT-CH2",
                complaint: "64-year-old male with sudden crushing chest pain radiating to left jaw, severe diaphoresis, acute dyspnea. History of coronary stenting.",
                age: 64,
                gender: "M",
                bp: "85/54",
                hr: 132,
                spo2: 90,
                gcs: 14
            },
            stroke: {
                location: "Washington Square Park North",
                lat: 40.7315,
                lon: -73.9970,
                caller: "Dr. Sarah Chen",
                phone: "555-0199",
                complaint: "58-year-old female with acute onset right facial droop, slurred expressive speech, and complete right hemiparesis. Symptoms began 22 minutes ago.",
                age: 58,
                gender: "F",
                bp: "178/104",
                hr: 92,
                spo2: 96,
                gcs: 12
            },
            trauma: {
                location: "FDR Drive & Houston St Exit",
                lat: 40.7210,
                lon: -73.9720,
                caller: "Highway Patrol Unit 4",
                phone: "911-NYSP-04",
                complaint: "Major high-speed highway collision, entrapped 29-year-old driver with open bilateral femur fractures, heavy hemorrhaging, blunt abdominal trauma.",
                age: 29,
                gender: "M",
                bp: "78/45",
                hr: 144,
                spo2: 86,
                gcs: 8
            },
            pediatric: {
                location: "Riverside Park & 79th St",
                lat: 40.7600,
                lon: -73.9900,
                caller: "Parent Lisa Brown",
                phone: "555-0722",
                complaint: "3-year-old toddler unresponsive, high fever, continuous febrile seizure activity lasting over 8 minutes. Labored breathing.",
                age: 3,
                gender: "F",
                bp: "92/60",
                hr: 158,
                spo2: 92,
                gcs: 10
            }
        };

        const sc = scenarios[type];
        if (!sc) return;

        document.getElementById('input-location').value = sc.location;
        document.getElementById('input-latitude').value = sc.lat;
        document.getElementById('input-longitude').value = sc.lon;
        document.getElementById('input-caller-name').value = sc.caller;
        document.getElementById('input-caller-phone').value = sc.phone;
        document.getElementById('input-complaint').value = sc.complaint;
        document.getElementById('input-patient-age').value = sc.age;
        document.getElementById('input-patient-gender').value = sc.gender;
        document.getElementById('input-vitals-bp').value = sc.bp;
        document.getElementById('input-vitals-hr').value = sc.hr;
        document.getElementById('input-vitals-spo2').value = sc.spo2;
        document.getElementById('input-vitals-gcs').value = sc.gcs;
    }

    async submitEmergency() {
        const btn = document.getElementById('btn-submit-emergency');
        const originalText = btn.innerHTML;
        btn.innerHTML = `<span class="icon">⏳</span> Analyzing Symptoms with AI...`;
        btn.disabled = true;

        const payload = {
            location_name: document.getElementById('input-location').value.trim(),
            latitude: parseFloat(document.getElementById('input-latitude').value),
            longitude: parseFloat(document.getElementById('input-longitude').value),
            caller_name: document.getElementById('input-caller-name').value.trim() || 'Anonymous Caller',
            caller_phone: document.getElementById('input-caller-phone').value.trim() || '911-DIRECT',
            chief_complaint: document.getElementById('input-complaint').value.trim(),
            patient_age: parseInt(document.getElementById('input-patient-age').value) || null,
            patient_gender: document.getElementById('input-patient-gender').value || null,
            vitals_bp: document.getElementById('input-vitals-bp').value.trim() || null,
            vitals_hr: parseInt(document.getElementById('input-vitals-hr').value) || null,
            vitals_spo2: parseInt(document.getElementById('input-vitals-spo2').value) || null,
            vitals_gcs: parseInt(document.getElementById('input-vitals-gcs').value) || null
        };

        try {
            const emergency = await window.API.createEmergency(payload);
            console.log("Emergency created:", emergency);
            this.activeEmergencyId = emergency.id;
            await this.refreshAll();
            this.selectEmergency(emergency.id);
        } catch (err) {
            alert(`Error reporting emergency: ${err.message}`);
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }

    async refreshAll() {
        try {
            const [hospitals, ambulances, emergencies, overview, events, ibmZ] = await Promise.all([
                window.API.getHospitals(),
                window.API.getAmbulances(),
                window.API.getEmergencies(),
                window.API.getOverview(),
                window.API.getEvents(30),
                window.API.getIBMZStatus()
            ]);

            this.hospitals = hospitals;
            this.ambulances = ambulances;
            this.emergencies = emergencies;
            this.overview = overview;
            this.events = events;

            // Default to first emergency if none selected
            if (!this.activeEmergencyId && this.emergencies.length > 0) {
                this.activeEmergencyId = this.emergencies[0].id;
            }

            // Update radar canvas
            if (this.radarMap) {
                this.radarMap.updateData(this.hospitals, this.ambulances, this.emergencies);
            }

            this.renderOverviewStats();
            this.renderIncidentsQueue();
            this.renderEventFeed();
            this.renderHospitalsGrid();
            this.renderAmbulanceGrid();
            this.renderIBMZStatus(ibmZ);

            if (this.activeEmergencyId) {
                await this.loadRecommendations(this.activeEmergencyId);
            }
        } catch (err) {
            console.error("Failed to refresh AEGIS data:", err);
        }
    }

    renderOverviewStats() {
        if (!this.overview) return;
        const o = this.overview;

        document.getElementById('stat-active-emergencies').textContent = `${o.emergencies.active} Active (${o.emergencies.critical} Critical)`;
        document.getElementById('stat-bed-capacity').textContent = `${o.hospitals.available_beds} / ${o.hospitals.total_beds} (${Math.round(100 - o.hospitals.bed_occupancy_pct)}% Open)`;
        document.getElementById('stat-icu-units').textContent = `${o.hospitals.icu_available} / ${o.hospitals.icu_total} Units`;
        document.getElementById('stat-fleet-available').textContent = `${o.fleet.available} / ${o.fleet.total} Ready`;
    }

    renderIncidentsQueue() {
        const container = document.getElementById('incidents-queue');
        if (!container) return;

        if (this.emergencies.length === 0) {
            container.innerHTML = `<div style="color: #64748b; font-size: 0.8rem; text-align: center; padding: 1rem;">No incidents currently reported</div>`;
            return;
        }

        container.innerHTML = this.emergencies.map(emrg => {
            const isSelected = emrg.id === this.activeEmergencyId;
            const badgeClass = emrg.severity === 'CRITICAL' ? 'badge-critical' : (emrg.severity === 'URGENT' ? 'badge-urgent' : 'badge-moderate');
            
            return `
                <div class="incident-card ${isSelected ? 'active' : ''}" onclick="window.aegisApp.selectEmergency(${emrg.id})">
                    <div class="incident-header">
                        <span class="incident-code">${emrg.emergency_code}</span>
                        <span class="severity-badge ${badgeClass}">${emrg.severity}</span>
                    </div>
                    <div style="font-size: 0.82rem; font-weight: 600; color: #f1f5f9;">
                        ${emrg.category.replace('_', ' ')}
                    </div>
                    <div style="font-size: 0.72rem; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        📍 ${emrg.location_name}
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.68rem; color: #64748b; margin-top: 0.2rem;">
                        <span>Status: <strong style="color: #38bdf8;">${emrg.status}</strong></span>
                        <span>${new Date(emrg.created_at).toLocaleTimeString()}</span>
                    </div>
                </div>
            `;
        }).join('');
    }

    async selectEmergency(emergencyId) {
        this.activeEmergencyId = emergencyId;
        this.renderIncidentsQueue();
        await this.loadRecommendations(emergencyId);
    }

    async loadRecommendations(emergencyId) {
        try {
            const recResponse = await window.API.getRecommendations(emergencyId);
            this.recommendations = recResponse.recommendations;
            this.renderRecommendations(recResponse);
        } catch (err) {
            console.error("Failed to load recommendations:", err);
        }
    }

    renderRecommendations(recResponse) {
        const container = document.getElementById('recommendations-container');
        if (!container) return;

        const currentEmergency = this.emergencies.find(e => e.id === this.activeEmergencyId);
        
        // Update triage header card
        if (currentEmergency) {
            document.getElementById('active-triage-category').textContent = currentEmergency.category.replace('_', ' ');
            document.getElementById('active-triage-severity').textContent = currentEmergency.severity;
            document.getElementById('active-triage-location').textContent = currentEmergency.location_name;
            document.getElementById('active-triage-ai-summary').textContent = currentEmergency.ai_classification || 'AI Clinical assessment pending.';
            
            const specsContainer = document.getElementById('active-triage-specialties');
            if (specsContainer) {
                specsContainer.innerHTML = (currentEmergency.required_specialties || []).map(s => `
                    <span class="scenario-pill" style="cursor: default;">🩺 ${s}</span>
                `).join('') + (currentEmergency.required_resources || []).map(r => `
                    <span class="scenario-pill" style="cursor: default; border-color: rgba(16, 185, 129, 0.4); color: #34d399;">📦 ${r}</span>
                `).join('');
            }
        }

        if (this.recommendations.length === 0) {
            container.innerHTML = `<div style="color: #64748b; padding: 2rem; text-align: center;">No matching hospitals found</div>`;
            return;
        }

        container.innerHTML = this.recommendations.map(rec => {
            const isTop = rec.rank === 1;
            const traumaClass = rec.trauma_level === 'Level 1' ? 'level-1' : '';
            const isAssigned = currentEmergency && currentEmergency.assigned_hospital_id === rec.hospital_id;

            return `
                <div class="rec-card ${isTop ? 'rank-1' : ''}">
                    <div class="rec-top-row">
                        <div class="rec-hospital-info">
                            <div class="rec-rank-badge">#${rec.rank}</div>
                            <div>
                                <div class="rec-hospital-name">${rec.hospital_name}</div>
                                <div class="rec-hospital-meta">
                                    <span class="trauma-badge ${traumaClass}">${rec.trauma_level}</span>
                                    <span>🚗 ${rec.distance_km} km</span>
                                    <span style="color: #38bdf8; font-weight: 600;">⏱️ ${rec.estimated_transit_minutes} min ETA</span>
                                    ${rec.ibm_z_verified ? '<span class="ibm-z-badge"><span class="dot"></span> IBM Z Synced</span>' : ''}
                                </div>
                            </div>
                        </div>
                        <div class="rec-scores-summary">
                            <div class="score-circle">
                                <span class="score-num">${rec.composite_score.toFixed(1)}</span>
                                <span class="score-label">MATCH SCORE</span>
                            </div>
                        </div>
                    </div>

                    <!-- Multi-factor Breakdown -->
                    <div class="factor-bars">
                        <div class="factor-bar-item">
                            <div class="factor-header">
                                <span>Capability (35%)</span>
                                <strong>${rec.capability_score}%</strong>
                            </div>
                            <div class="progress-track">
                                <div class="progress-fill green" style="width: ${rec.capability_score}%"></div>
                            </div>
                        </div>
                        <div class="factor-bar-item">
                            <div class="factor-header">
                                <span>Transit Speed (25%)</span>
                                <strong>${rec.transit_score}%</strong>
                            </div>
                            <div class="progress-track">
                                <div class="progress-fill" style="width: ${rec.transit_score}%"></div>
                            </div>
                        </div>
                        <div class="factor-bar-item">
                            <div class="factor-header">
                                <span>Bed Headroom (20%)</span>
                                <strong>${rec.bed_score}%</strong>
                            </div>
                            <div class="progress-track">
                                <div class="progress-fill amber" style="width: ${rec.bed_score}%"></div>
                            </div>
                        </div>
                        <div class="factor-bar-item">
                            <div class="factor-header">
                                <span>ER Load Penalty (-15%)</span>
                                <strong style="color: #f43f5e;">-${rec.congestion_penalty}%</strong>
                            </div>
                            <div class="progress-track">
                                <div class="progress-fill red" style="width: ${Math.min(100, rec.congestion_penalty * 1.5)}%"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Explainability Rationale -->
                    <div class="rec-rationale">
                        <strong>AI Clinical Justification:</strong> ${rec.rationale}
                    </div>

                    <div class="rec-actions">
                        <div class="rec-capacity-tags">
                            <span class="rec-tag">🛏️ ${rec.available_beds} Beds Avail</span>
                            <span class="rec-tag">🩺 ${rec.icu_available} ICU Avail</span>
                            <span class="rec-tag">🏥 ER: ${rec.er_current_load}/${rec.er_capacity}</span>
                        </div>
                        <div>
                            ${isAssigned ? `
                                <button class="btn btn-ghost btn-sm" disabled style="color: #10b981; border-color: #10b981;">
                                    ✓ Hospital Assigned
                                </button>
                            ` : `
                                <button class="btn btn-primary btn-sm" onclick="window.aegisApp.openDispatchModal(${rec.hospital_id}, '${rec.hospital_name.replace(/'/g, "\\'")}')">
                                    🚀 Dispatch & Route Unit
                                </button>
                            `}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    openDispatchModal(hospitalId, hospitalName) {
        this.pendingDispatchHospitalId = hospitalId;
        const modal = document.getElementById('dispatch-modal');
        const hospitalTargetSpan = document.getElementById('modal-target-hospital');
        const ambulanceSelect = document.getElementById('modal-ambulance-select');

        hospitalTargetSpan.textContent = hospitalName;

        // Filter available ambulances
        const availableAmbs = this.ambulances.filter(a => a.status === 'AVAILABLE');
        if (availableAmbs.length === 0) {
            ambulanceSelect.innerHTML = `<option value="">⚠️ No ambulances currently available!</option>`;
        } else {
            ambulanceSelect.innerHTML = availableAmbs.map(amb => `
                <option value="${amb.id}">
                    ${amb.call_sign} (${amb.vehicle_type}) — Crew: ${amb.paramedic_crew} [${amb.equipment_level}]
                </option>
            `).join('');
        }

        modal.classList.add('active');

        // Bind confirm button
        const confirmBtn = document.getElementById('btn-confirm-dispatch');
        confirmBtn.onclick = () => this.confirmDispatch();
    }

    async confirmDispatch() {
        const ambulanceSelect = document.getElementById('modal-ambulance-select');
        const ambulanceId = parseInt(ambulanceSelect.value);
        if (!ambulanceId || !this.pendingDispatchHospitalId || !this.activeEmergencyId) {
            alert("Please select a valid ambulance unit.");
            return;
        }

        try {
            await window.API.dispatchEmergency(this.activeEmergencyId, {
                ambulance_id: ambulanceId,
                hospital_id: this.pendingDispatchHospitalId,
                notes: "Dispatched from AEGIS Command Center."
            });

            document.getElementById('dispatch-modal').classList.remove('active');
            await this.refreshAll();
        } catch (err) {
            alert(`Dispatch failed: ${err.message}`);
        }
    }

    renderEventFeed() {
        const container = document.getElementById('event-feed-container');
        if (!container) return;

        container.innerHTML = this.events.map(ev => `
            <div class="event-item ${ev.event_type}">
                <div class="event-top">
                    <span>${ev.actor} • ${ev.event_type}</span>
                    <span>${new Date(ev.timestamp).toLocaleTimeString()}</span>
                </div>
                <div class="event-text">${ev.summary}</div>
            </div>
        `).join('');
    }

    renderHospitalsGrid() {
        const container = document.getElementById('hospitals-grid');
        if (!container) return;

        container.innerHTML = this.hospitals.map(hosp => {
            const traumaClass = hosp.trauma_level === 'Level 1' ? 'level-1' : '';
            return `
                <div class="hospital-card">
                    <div class="hospital-card-header">
                        <div>
                            <div style="font-size: 1.05rem; font-weight: 700; color: #f8fafc;">${hosp.name}</div>
                            <div style="font-size: 0.72rem; color: #94a3b8; font-family: var(--font-mono); margin-top: 2px;">
                                ${hosp.code} • ${hosp.address}
                            </div>
                        </div>
                        <span class="trauma-badge ${traumaClass}">${hosp.trauma_level}</span>
                    </div>

                    <div class="hospital-specialty-pills">
                        ${(hosp.specialties || []).slice(0, 4).map(s => `<span class="specialty-tag">${s}</span>`).join('')}
                    </div>

                    <!-- Real-time Capacity Sliders -->
                    <div class="capacity-controls-box">
                        <div class="slider-group">
                            <div class="slider-label-row">
                                <span>Inpatient Available Beds</span>
                                <strong id="lbl-beds-${hosp.id}">${hosp.available_beds} / ${hosp.total_beds}</strong>
                            </div>
                            <input type="range" min="0" max="${hosp.total_beds}" value="${hosp.available_beds}"
                                onchange="window.aegisApp.onHospitalCapacityChange(${hosp.id}, 'available_beds', this.value)"
                                oninput="document.getElementById('lbl-beds-${hosp.id}').textContent = this.value + ' / ${hosp.total_beds}'"
                            />
                        </div>

                        <div class="slider-group">
                            <div class="slider-label-row">
                                <span>Available ICU Beds</span>
                                <strong id="lbl-icu-${hosp.id}">${hosp.icu_available} / ${hosp.icu_total}</strong>
                            </div>
                            <input type="range" min="0" max="${hosp.icu_total}" value="${hosp.icu_available}"
                                onchange="window.aegisApp.onHospitalCapacityChange(${hosp.id}, 'icu_available', this.value)"
                                oninput="document.getElementById('lbl-icu-${hosp.id}').textContent = this.value + ' / ${hosp.icu_total}'"
                            />
                        </div>

                        <div class="slider-group">
                            <div class="slider-label-row">
                                <span>Emergency Room Load</span>
                                <strong id="lbl-er-${hosp.id}">${hosp.er_current_load} / ${hosp.er_capacity}</strong>
                            </div>
                            <input type="range" min="0" max="${hosp.er_capacity + 15}" value="${hosp.er_current_load}"
                                onchange="window.aegisApp.onHospitalCapacityChange(${hosp.id}, 'er_current_load', this.value)"
                                oninput="document.getElementById('lbl-er-${hosp.id}').textContent = this.value + ' / ${hosp.er_capacity}'"
                            />
                        </div>
                    </div>

                    <div style="display: flex; align-items: center; justify-content: space-between; margin-top: auto;">
                        <button class="btn btn-ghost btn-sm" onclick="window.aegisApp.syncHospitalToIBMZ('${hosp.code}')">
                            <span class="icon">🔄</span> Sync IBM Z
                        </button>
                        <button class="btn btn-critical btn-sm" onclick="window.aegisApp.triggerHospitalSurge(${hosp.id})">
                            ⚠️ Surge +8
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    async onHospitalCapacityChange(hospitalId, field, value) {
        try {
            await window.API.updateHospitalCapacity(hospitalId, {
                [field]: parseInt(value)
            });
            // Automatically recalculate recommendations for active emergency
            if (this.activeEmergencyId) {
                await window.API.recalculateRecommendations(this.activeEmergencyId);
            }
        } catch (err) {
            console.error("Failed to update hospital capacity:", err);
        }
    }

    async syncHospitalToIBMZ(hospitalCode) {
        try {
            const res = await window.API.syncCapacityToIBMZ(hospitalCode);
            alert(`IBM z/OS Sync Confirmed!\nCICS Sequence: #${res.mainframe_sequence_no}\nStatus: ${res.sync_status}`);
            await this.refreshAll();
        } catch (err) {
            alert(`IBM Z Sync Failed: ${err.message}`);
        }
    }

    async triggerHospitalSurge(hospitalId) {
        try {
            const res = await window.API.triggerSurge(hospitalId, 8);
            alert(`Mass Casualty Surge Triggered!\nER Load increased to ${res.new_er_load} (${res.status}).\nRecommendations dynamically rerouted for ${res.recalculated_emergencies} incidents.`);
            await this.refreshAll();
        } catch (err) {
            alert(`Surge failed: ${err.message}`);
        }
    }

    renderAmbulanceGrid() {
        const container = document.getElementById('ambulance-grid');
        if (!container) return;

        container.innerHTML = this.ambulances.map(amb => {
            const isAvail = amb.status === 'AVAILABLE';
            const typeClass = `type-${amb.vehicle_type.toLowerCase()}`;
            return `
                <div class="fleet-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 1rem; font-weight: 700; color: #f8fafc; font-family: var(--font-mono);">${amb.call_sign}</span>
                        <span class="fleet-type-badge ${typeClass}">${amb.vehicle_type}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: #cbd5e1;">
                        👨‍⚕️ ${amb.paramedic_crew}
                    </div>
                    <div style="font-size: 0.72rem; color: #94a3b8;">
                        📦 ${amb.equipment_level}
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.4rem; font-size: 0.72rem;">
                        <span style="color: ${isAvail ? '#10b981' : '#38bdf8'}; font-weight: 700;">
                            ● ${amb.status}
                        </span>
                        <span>${amb.speed_kmh} km/h</span>
                    </div>
                    <div style="margin-top: 0.4rem;">
                        <button class="btn btn-ghost btn-sm" style="width: 100%;" onclick="window.aegisApp.resetAmbulance(${amb.id})">
                            Reset to Available
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    async resetAmbulance(ambulanceId) {
        try {
            await window.API.resetAmbulance(ambulanceId);
            await this.refreshAll();
        } catch (err) {
            console.error("Failed to reset ambulance:", err);
        }
    }

    renderIBMZStatus(ibmZ) {
        if (!ibmZ) return;
        const statusEl = document.getElementById('ibm-z-header-status');
        if (statusEl) {
            statusEl.textContent = `IBM Z: ${ibmZ.mode.replace('_', ' ')}`;
        }

        const noticeEl = document.getElementById('ibm-z-notice-text');
        if (noticeEl) {
            noticeEl.textContent = ibmZ.notice;
        }

        const sysplexEl = document.getElementById('ibm-z-sysplex-node');
        if (sysplexEl) {
            sysplexEl.textContent = ibmZ.active_sysplex_node;
        }

        const latencyEl = document.getElementById('ibm-z-latency');
        if (latencyEl) {
            latencyEl.textContent = `${ibmZ.average_latency_ms} ms`;
        }
    }

    async lookupPatientEHR() {
        const idInput = document.getElementById('input-patient-nhid').value.trim();
        const resultContainer = document.getElementById('ehr-lookup-result');
        if (!idInput) return;

        resultContainer.innerHTML = `<div style="color: #60a5fa;">Querying IBM z/OS CICS Master Patient Index...</div>`;

        try {
            const data = await window.API.lookupPatientEHR(idInput);
            resultContainer.innerHTML = `
                <div style="background: rgba(15, 98, 254, 0.1); border: 1px solid rgba(15, 98, 254, 0.35); border-radius: 8px; padding: 1rem; margin-top: 1rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <strong style="color: #93c5fd; font-size: 1rem;">${data.patient_name}</strong>
                        <span style="font-family: var(--font-mono); font-size: 0.75rem; color: #60a5fa;">Token: ${data.cics_audit_token}</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; font-size: 0.78rem;">
                        <div>🩸 Blood Type: <strong style="color: #f43f5e;">${data.blood_type}</strong></div>
                        <div>⚠️ DNR Directive: <strong>${data.dnr_order ? 'YES (DNR)' : 'NO (Full Resuscitation)'}</strong></div>
                        <div>❤️ Cardiac History: <strong>${data.cardiac_history ? 'YES (High Risk)' : 'None reported'}</strong></div>
                        <div>⏱️ CICS Latency: <strong>${data.response_latency_ms} ms</strong></div>
                    </div>
                    <div style="margin-top: 0.6rem; font-size: 0.75rem; color: #fdba74;">
                        <strong>Allergies:</strong> ${(data.allergies || []).join(', ')}
                    </div>
                    <div style="margin-top: 0.4rem; font-size: 0.75rem; color: #cbd5e1;">
                        <strong>Prior Interventions:</strong> ${(data.prior_surgeries || []).join('; ') || 'None'}
                    </div>
                </div>
            `;
        } catch (err) {
            resultContainer.innerHTML = `<div style="color: #f43f5e;">EHR lookup error: ${err.message}</div>`;
        }
    }

    async toggleSimulation() {
        const btn = document.getElementById('btn-toggle-sim');
        try {
            const status = await window.API.getSimulationStatus();
            if (status.active) {
                await window.API.stopSimulation();
                btn.textContent = "▶ Resume Sim";
                btn.className = "btn btn-ghost btn-sm";
            } else {
                await window.API.startSimulation();
                btn.textContent = "⏸ Pause Sim";
                btn.className = "btn btn-primary btn-sm";
            }
        } catch (err) {
            console.error("Toggle simulation failed:", err);
        }
    }

    async stepSimulation() {
        try {
            await window.API.stepSimulation();
            await this.refreshAll();
        } catch (err) {
            console.error("Step simulation failed:", err);
        }
    }

    openSurgeModal() {
        const select = document.getElementById('surge-hospital-select');
        select.innerHTML = this.hospitals.map(h => `
            <option value="${h.id}">${h.name} (${h.trauma_level}) — ER load: ${h.er_current_load}/${h.er_capacity}</option>
        `).join('');
        document.getElementById('surge-modal').classList.add('active');
    }

    async triggerSurgeIncident() {
        const hospitalId = parseInt(document.getElementById('surge-hospital-select').value);
        const count = parseInt(document.getElementById('surge-patient-count').value);

        try {
            await window.API.triggerSurge(hospitalId, count);
            document.getElementById('surge-modal').classList.remove('active');
            await this.refreshAll();
        } catch (err) {
            alert(`Surge trigger failed: ${err.message}`);
        }
    }

    handleWebSocketEvent(payload) {
        console.log("[AEGIS WS Event]", payload);

        // Instant update handlers
        if (payload.type === 'NEW_EMERGENCY') {
            this.refreshAll();
        } else if (payload.type === 'HOSPITAL_UPDATED') {
            const hosp = this.hospitals.find(h => h.id === payload.hospital_id);
            if (hosp) {
                hosp.available_beds = payload.available_beds;
                hosp.icu_available = payload.icu_available;
                hosp.er_current_load = payload.er_current_load;
                hosp.status = payload.status;
                this.renderOverviewStats();
                if (this.radarMap) this.radarMap.updateData(this.hospitals, this.ambulances, this.emergencies);
            }
        } else if (payload.type === 'AMBULANCE_TELEMETRY') {
            const amb = this.ambulances.find(a => a.id === payload.ambulance_id);
            if (amb) {
                amb.latitude = payload.latitude;
                amb.longitude = payload.longitude;
                amb.status = payload.status;
                amb.speed_kmh = payload.speed_kmh;
                if (this.radarMap) this.radarMap.updateData(this.hospitals, this.ambulances, this.emergencies);
            }
        } else if (payload.type === 'SIMULATION_TICK') {
            // Light telemetry refresh
            this.refreshAll();
        } else if (payload.type === 'RECOMMENDATIONS_UPDATED') {
            if (payload.emergency_id === this.activeEmergencyId) {
                this.loadRecommendations(this.activeEmergencyId);
            }
        }
    }
}

// Instantiate on DOM load
window.addEventListener('DOMContentLoaded', () => {
    window.aegisApp = new AEGISApp();
});
