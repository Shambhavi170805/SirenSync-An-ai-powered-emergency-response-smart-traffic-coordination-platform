/**
 * SirenSync Driver Interface Utilities (Member 3 - Nidhi)
 * Common helpers for HTML escaping and safe coordinate/location formatting.
 */

export function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function formatCoordinate(val, fallback = 'N/A') {
  const num = typeof val === 'number' ? val : parseFloat(val);
  return Number.isFinite(num) ? num.toFixed(4) : fallback;
}

export function formatLocation(location, fallback = 'Location unavailable') {
  if (!location) return fallback;
  if (location.address && typeof location.address === 'string' && location.address.trim()) {
    return location.address.trim();
  }
  const lat = typeof location.latitude === 'number' ? location.latitude : parseFloat(location.latitude);
  const lng = typeof location.longitude === 'number' ? location.longitude : parseFloat(location.longitude);
  if (Number.isFinite(lat) && Number.isFinite(lng)) {
    return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
  }
  return fallback;
}
