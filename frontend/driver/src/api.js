/**
 * SirenSync Driver Interface API Client (Member 3 - Nidhi)
 * Communicates with backend FastAPI endpoints for ambulance telemetry,
 * status transitions, route progress, and tracking snapshots.
 */

const API_BASE = '/api/v1';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const res = await fetch(url, config);
    if (!res.ok) {
      let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errorJson = await res.json();
        if (errorJson.detail) {
          errorDetail = typeof errorJson.detail === 'string'
            ? errorJson.detail
            : JSON.stringify(errorJson.detail);
        }
      } catch (e) {
        // Fallback to default status text
      }
      throw new Error(errorDetail);
    }
    return await res.json();
  } catch (err) {
    console.error(`API Error on [${options.method || 'GET'}] ${url}:`, err);
    throw err;
  }
}

export const api = {
  // Fleet & Ambulance details
  getAmbulances: (statusFilter = null, typeFilter = null) => {
    const params = new URLSearchParams();
    if (statusFilter) params.append('status_filter', statusFilter);
    if (typeFilter) params.append('type_filter', typeFilter);
    const query = params.toString() ? `?${params.toString()}` : '';
    return request(`/ambulances${query}`);
  },

  getAmbulance: (ambulanceId) => request(`/ambulances/${encodeURIComponent(ambulanceId)}`),

  getAmbulanceByEmergency: (emergencyId) =>
    request(`/ambulances/by-emergency/${encodeURIComponent(emergencyId)}`),

  // Driver operational lifecycle transitions
  updateStatus: (ambulanceId, status, notes = null) =>
    request(`/ambulances/${encodeURIComponent(ambulanceId)}/status`, {
      method: 'POST',
      body: JSON.stringify({ status, notes }),
    }),

  // Telemetry updates (explicitly flagged simulated for prototype transparency)
  updateLocation: (ambulanceId, { latitude, longitude, address = null, isSimulated = true }) => {
    const lat = typeof latitude === 'number' ? latitude : parseFloat(latitude);
    const lng = typeof longitude === 'number' ? longitude : parseFloat(longitude);
    if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
      throw new Error(`Latitude must be a valid finite number between -90 and 90 (received: ${latitude})`);
    }
    if (!Number.isFinite(lng) || lng < -180 || lng > 180) {
      throw new Error(`Longitude must be a valid finite number between -180 and 180 (received: ${longitude})`);
    }
    return request(`/ambulances/${encodeURIComponent(ambulanceId)}/location`, {
      method: 'POST',
      body: JSON.stringify({
        latitude: lat,
        longitude: lng,
        address,
        isSimulated: Boolean(isSimulated),
        timestamp: new Date().toISOString(),
      }),
    });
  },

  // Monotonic route progress reporting (0.0 to 100.0)
  updateRouteProgress: (ambulanceId, { routeProgress, emergencyId = null, isSimulated = true }) => {
    const progress = typeof routeProgress === 'number' ? routeProgress : parseFloat(routeProgress);
    if (!Number.isFinite(progress) || progress < 0 || progress > 100) {
      throw new Error(`Route progress must be a valid number between 0.0 and 100.0 (received: ${routeProgress})`);
    }
    return request(`/ambulances/${encodeURIComponent(ambulanceId)}/progress`, {
      method: 'POST',
      body: JSON.stringify({
        routeProgress: progress,
        isSimulated: Boolean(isSimulated),
        emergencyId,
      }),
    });
  },

  // Real-time tracking fallback snapshot
  getTrackingSnapshot: (emergencyId) =>
    request(`/tracking/snapshot/${encodeURIComponent(emergencyId)}`),

  // Destination hospital details
  getHospital: (hospitalId) =>
    request(`/hospitals/${encodeURIComponent(hospitalId)}`),
};
