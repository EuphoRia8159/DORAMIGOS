/**
 * AEGIS Unified API Client
 * Connects website frontend to FastAPI backend endpoints.
 */

const API = {
    baseUrl: window.location.origin,

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            ...(options.headers || {})
        };

        try {
            const response = await fetch(url, { ...options, headers });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(errorData.detail || `HTTP Error ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    },

    // Hospital APIs
    async getHospitals(filters = {}) {
        const params = new URLSearchParams(filters).toString();
        return this.request(`/api/hospitals${params ? '?' + params : ''}`);
    },

    async updateHospitalCapacity(hospitalId, data) {
        return this.request(`/api/hospitals/${hospitalId}/capacity`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    },

    // Ambulance APIs
    async getAmbulances(filters = {}) {
        const params = new URLSearchParams(filters).toString();
        return this.request(`/api/ambulances${params ? '?' + params : ''}`);
    },

    async resetAmbulance(ambulanceId) {
        return this.request(`/api/ambulances/${ambulanceId}/reset`, {
            method: 'POST'
        });
    },

    // Emergency APIs
    async getEmergencies(filters = {}) {
        const params = new URLSearchParams(filters).toString();
        return this.request(`/api/emergencies${params ? '?' + params : ''}`);
    },

    async getEmergency(id) {
        return this.request(`/api/emergencies/${id}`);
    },

    async createEmergency(data) {
        return this.request('/api/emergencies', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async dispatchEmergency(emergencyId, payload) {
        return this.request(`/api/emergencies/${emergencyId}/dispatch`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    // Recommendation APIs
    async getRecommendations(emergencyId) {
        return this.request(`/api/recommendations/${emergencyId}`);
    },

    async recalculateRecommendations(emergencyId) {
        return this.request(`/api/recommendations/${emergencyId}/recalculate`, {
            method: 'POST'
        });
    },

    // Simulation APIs
    async getSimulationStatus() {
        return this.request('/api/simulation/status');
    },

    async startSimulation() {
        return this.request('/api/simulation/start', { method: 'POST' });
    },

    async stopSimulation() {
        return this.request('/api/simulation/stop', { method: 'POST' });
    },

    async stepSimulation() {
        return this.request('/api/simulation/tick', { method: 'POST' });
    },

    async triggerSurge(hospitalId, incomingPatients = 10) {
        return this.request('/api/simulation/surge', {
            method: 'POST',
            body: JSON.stringify({ hospital_id: hospitalId, incoming_patients: incomingPatients })
        });
    },

    // IBM Z APIs
    async getIBMZStatus() {
        return this.request('/api/ibm-z/status');
    },

    async lookupPatientEHR(nationalHealthId, patientName = '') {
        return this.request('/api/ibm-z/patient-lookup', {
            method: 'POST',
            body: JSON.stringify({ national_health_id: nationalHealthId, patient_name: patientName })
        });
    },

    async syncCapacityToIBMZ(hospitalCode) {
        return this.request('/api/ibm-z/sync-capacity', {
            method: 'POST',
            body: JSON.stringify({ hospital_code: hospitalCode })
        });
    },

    // Analytics APIs
    async getOverview() {
        return this.request('/api/analytics/overview');
    },

    async getEvents(limit = 40) {
        return this.request(`/api/analytics/events?limit=${limit}`);
    }
};

window.API = API;
