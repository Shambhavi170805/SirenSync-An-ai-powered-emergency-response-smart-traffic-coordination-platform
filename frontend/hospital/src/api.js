/**
 * SirenSync Hospital Intelligence API Client
 * Connects frontend dashboard with backend FastAPI endpoints.
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
        // use fallback text
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
  // Hospital Directory
  getHospitals: () => request('/hospitals'),
  getHospitalDetails: (hospitalId) => request(`/hospitals/${hospitalId}`),

  // Dashboard Aggregation
  getHospitalDashboard: (hospitalId) => request(`/hospitals/${hospitalId}/dashboard`),

  // Beds & Resources
  getHospitalBeds: (hospitalId, bedType = null) => {
    const query = bedType ? `?bed_type=${encodeURIComponent(bedType)}` : '';
    return request(`/hospitals/${hospitalId}/beds${query}`);
  },
  getHospitalBedSummary: (hospitalId) => request(`/hospitals/${hospitalId}/beds/summary`),
  updateBedStatus: (hospitalId, bedId, newStatus) => request(`/hospitals/${hospitalId}/beds/${bedId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status: newStatus }),
  }),

  // Emergency Queue & Reservations
  getHospitalQueue: (hospitalId) => request(`/hospitals/${hospitalId}/queue`),
  getHospitalReservations: (hospitalId) => request(`/hospitals/${hospitalId}/reservations`),

  // 4-Factor Ranking Demonstration
  rankHospitals: (rankingPayload) => request('/hospitals/rank', {
    method: 'POST',
    body: JSON.stringify(rankingPayload),
  }),

  // Reassignment & Prototype Policy
  evaluateReassignment: (reassignmentPayload) => request('/reassignment/evaluate', {
    method: 'POST',
    body: JSON.stringify(reassignmentPayload),
  }),
  getReassignmentAudit: () => request('/reassignment/audit'),
};
