/**
 * SirenSync Patient Emergency & Hospital Intelligence Service
 * Communicates with FastAPI backend for:
 * 1. Registering & persisting emergency requests (POST /api/v1/emergencies)
 * 2. Deterministic 4-factor hospital ranking (POST /api/v1/hospitals/rank)
 * 3. Concurrency-safe atomic bed reservation (POST /api/v1/emergencies/{id}/select-hospital)
 * 4. Authoritative emergency status & history lookup
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

async function handleResponse(response) {
  let data = null;
  try {
    data = await response.json();
  } catch (e) {
    // Non-JSON response
  }

  if (!response.ok) {
    const errorDetail = data?.detail || data?.message || `Request failed with status ${response.status}`;
    const error = new Error(typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail));
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

export const emergencyService = {
  /**
   * Registers and persists an emergency intake record on the backend.
   */
  async createEmergency({
    emergencyId,
    patientId,
    emergencyType,
    priority,
    patientLocation,
    requiredBedType,
    requiredCapabilities = [],
    symptoms = '',
    region = 'Dehradun'
  }) {
    const payload = {
      emergencyId: emergencyId || undefined,
      patientId: patientId || undefined,
      emergencyType: emergencyType || 'CARDIAC_ARREST',
      priority: priority || 'P1_CRITICAL',
      region: region || 'Dehradun',
      patientLocation: {
        latitude: Number(patientLocation.latitude),
        longitude: Number(patientLocation.longitude),
        address: patientLocation.address || 'Pickup Location'
      },
      requiredBedType: requiredBedType || 'ICU',
      requiredCapabilities: requiredCapabilities || [],
      symptoms: symptoms || ''
    };

    const response = await fetch(`${API_BASE}/api/v1/emergencies`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include', // Automatically passes session cookie if signed in
      body: JSON.stringify(payload),
    });

    return handleResponse(response);
  },

  /**
   * Requests deterministic 4-factor hospital ranking from the backend for the persisted emergency.
   */
  async rankHospitals({
    emergencyId,
    patientLocation,
    emergencyType,
    priority,
    requiredBedType,
    requiredCapabilities = [],
    patientId,
    symptoms,
    region = 'Dehradun'
  }) {
    const payload = {
      emergencyId: emergencyId,
      region: region || 'Dehradun',
      patientLocation: {
        latitude: Number(patientLocation.latitude),
        longitude: Number(patientLocation.longitude),
        address: patientLocation.address || ''
      },
      emergencyType: emergencyType || 'CARDIAC_ARREST',
      priority: priority || 'P1_CRITICAL',
      requiredBedType: requiredBedType || 'ICU',
      requiredCapabilities: requiredCapabilities || [],
      patientId: patientId || undefined,
      symptoms: symptoms || undefined
    };

    const response = await fetch(`${API_BASE}/api/v1/hospitals/rank`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(payload),
    });

    return handleResponse(response);
  },

  /**
   * Confirms patient hospital selection and acquires an atomic bed reservation lock.
   */
  async selectHospital({
    emergencyId,
    hospitalId,
    requiredBedType
  }) {
    const payload = {
      selectedHospitalId: hospitalId,
      requiredBedType: requiredBedType || 'ICU'
    };

    const response = await fetch(`${API_BASE}/api/v1/emergencies/${encodeURIComponent(emergencyId)}/select-hospital`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(payload),
    });

    return handleResponse(response);
  },

  /**
   * Retrieves authoritative emergency details by ID.
   */
  async getEmergency(emergencyId) {
    const response = await fetch(`${API_BASE}/api/v1/emergencies/${encodeURIComponent(emergencyId)}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      credentials: 'include',
    });

    return handleResponse(response);
  },


  /** Retrieves a current traffic-aware route for an assigned ambulance. */
  async getAmbulanceRoute(ambulanceId) {
    const response = await fetch(`${API_BASE}/api/v1/ambulances/${encodeURIComponent(ambulanceId)}/route`, {
      method: 'GET', headers: { 'Accept': 'application/json' }, credentials: 'include'
    });
    return handleResponse(response);
  },

  /** Retrieves the current ambulance telemetry snapshot for an emergency. */
  async getTrackingSnapshot(emergencyId) {
    const response = await fetch(`${API_BASE}/api/v1/tracking/snapshot/${encodeURIComponent(emergencyId)}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      credentials: 'include',
    });
    return handleResponse(response);
  },

  /**
   * Retrieves live bed reservation details by ID.
   */
  async getReservation(reservationId) {
    const response = await fetch(`${API_BASE}/api/v1/reservations/${encodeURIComponent(reservationId)}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      credentials: 'include',
    });

    return handleResponse(response);
  },

  /**
   * Retrieves active patient's past emergency records.
   */
  async getMyEmergencies() {
    const response = await fetch(`${API_BASE}/api/v1/emergencies/patient/my-emergencies`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      credentials: 'include',
    });

    return handleResponse(response);
  }
};

export default emergencyService;
