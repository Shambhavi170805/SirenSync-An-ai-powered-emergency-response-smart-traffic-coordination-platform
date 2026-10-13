/**
 * LocationSimulator Component
 * Provides prototype telemetry and route progress simulation controls.
 * Explicitly labeled as Simulated Coordinates Prototype Mode;
 * never claims real GPS. Validates coordinates and monotonic progress rules.
 */

import { escapeHtml } from '../utils.js';

export function renderLocationSimulator(state) {
  const ambulance = state.selectedAmbulance;
  if (!ambulance) return '';

  const latVal = typeof ambulance.currentLocation?.latitude === 'number' && Number.isFinite(ambulance.currentLocation.latitude)
    ? ambulance.currentLocation.latitude
    : 12.9716;
  const lngVal = typeof ambulance.currentLocation?.longitude === 'number' && Number.isFinite(ambulance.currentLocation.longitude)
    ? ambulance.currentLocation.longitude
    : 77.5946;
  const currentAddr = ambulance.currentLocation?.address || 'MG Road Transit Sector';
  const currentProgress = typeof ambulance.routeProgress === 'number' && Number.isFinite(ambulance.routeProgress)
    ? Math.max(0, Math.min(100, ambulance.routeProgress))
    : 0.0;

  // Waypoint presets in Bengaluru for quick evaluator demonstration
  const WAYPOINTS = [
    { name: 'MG Road Metro Origin', lat: 12.9716, lng: 77.5946, addr: 'MG Road Metro Station Area, Bengaluru' },
    { name: 'Indiranagar 100ft Rd', lat: 12.9784, lng: 77.6408, addr: '100ft Road, Indiranagar, Bengaluru' },
    { name: 'Koramangala 80ft Rd', lat: 12.9352, lng: 77.6245, addr: 'Sony World Signal, Koramangala, Bengaluru' },
    { name: 'HAL Old Airport Corridor', lat: 12.9650, lng: 77.6350, addr: 'Old Airport Road Corridor, Bengaluru' },
    { name: 'Kodihalli / Manipal Gate', lat: 12.9592, lng: 77.6477, addr: 'Manipal Hospital Receiving Bay, Kodihalli' },
    { name: 'Bannerghatta / Apollo Gate', lat: 12.8942, lng: 77.5990, addr: 'Apollo Hospital Emergency Bay, Bannerghatta' },
  ];

  return `
    <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5 sm:p-6 space-y-6">

      <!-- Section Header with Prototype Notice -->
      <div class="pb-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <div class="flex items-center space-x-2">
            <h3 class="text-sm font-bold text-slate-900">Telemetry & Route Simulator</h3>
            <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-100 text-amber-800 border border-amber-300">
              Prototype Simulation
            </span>
          </div>
          <p class="text-xs text-slate-500">
            Explicitly labeled simulated coordinates; browser GPS is deliberately disabled per system safeguards.
          </p>
        </div>
        <div class="text-[11px] text-slate-400 font-mono">
          isSimulated: <strong class="text-emerald-600">true</strong>
        </div>
      </div>

      <!-- Part 1: Coordinate Telemetry Controls -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-slate-700">1. Simulated Coordinate Telemetry</span>
          <span class="text-[11px] text-slate-400">Validated [-90, 90] / [-180, 180]</span>
        </div>

        <!-- Waypoint Preset Pills -->
        <div>
          <span class="text-[11px] text-slate-500 block mb-1.5 font-medium">Quick Waypoint Presets:</span>
          <div class="flex flex-wrap gap-1.5">
            ${WAYPOINTS.map(wp => `
              <button
                type="button"
                class="btn-apply-waypoint px-2 py-1 bg-slate-50 hover:bg-slate-100 text-slate-700 rounded text-[11px] border border-slate-200 transition font-medium cursor-pointer"
                data-lat="${wp.lat}"
                data-lng="${wp.lng}"
                data-addr="${escapeHtml(wp.addr)}"
              >
                ${escapeHtml(wp.name)}
              </button>
            `).join('')}
          </div>
        </div>

        <!-- Coordinate Inputs Grid -->
        <form id="form-location-update" class="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
          <div>
            <label for="sim-lat" class="block text-[11px] font-medium text-slate-600 mb-0.5">Latitude (°N)</label>
            <input
              type="number"
              step="0.0001"
              min="-90"
              max="90"
              id="sim-lat"
              class="w-full text-xs font-mono px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-rose-500"
              value="${latVal.toFixed(4)}"
              required
            />
          </div>
          <div>
            <label for="sim-lng" class="block text-[11px] font-medium text-slate-600 mb-0.5">Longitude (°E)</label>
            <input
              type="number"
              step="0.0001"
              min="-180"
              max="180"
              id="sim-lng"
              class="w-full text-xs font-mono px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-rose-500"
              value="${lngVal.toFixed(4)}"
              required
            />
          </div>
          <div>
            <label for="sim-addr" class="block text-[11px] font-medium text-slate-600 mb-0.5">Transit Landmark</label>
            <input
              type="text"
              id="sim-addr"
              class="w-full text-xs px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-rose-500"
              value="${escapeHtml(currentAddr)}"
            />
          </div>
          <div class="sm:col-span-3 flex justify-end">
            <button
              type="submit"
              id="btn-send-location"
              class="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold shadow-sm transition flex items-center space-x-1.5 cursor-pointer"
            >
              <svg class="w-3.5 h-3.5 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd" />
              </svg>
              <span>Transmit Simulated Coordinates</span>
            </button>
          </div>
        </form>
      </div>

      <!-- Part 2: Monotonic Route Progress Controls -->
      <div class="pt-4 border-t border-slate-100 space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-slate-700">2. Route Progress Simulation (0.0% to 100.0%)</span>
          <span class="text-[11px] text-slate-400">Synchronized with 40% Reassignment Policy</span>
        </div>

        <form id="form-progress-update" class="space-y-3">
          <div class="flex flex-col sm:flex-row sm:items-center gap-3">
            <div class="flex-1">
              <label for="sim-progress-range" class="block text-[11px] text-slate-500 mb-1">
                Progress Target: <span id="progress-val-label" class="font-bold text-rose-600 font-mono text-xs">${currentProgress.toFixed(1)}%</span>
              </label>
              <input
                type="range"
                id="sim-progress-range"
                min="${currentProgress.toFixed(1)}"
                max="100"
                step="0.5"
                value="${currentProgress.toFixed(1)}"
                class="w-full accent-rose-600 cursor-pointer"
              />
            </div>

            <!-- Quick Step Increment Buttons -->
            <div class="flex items-center gap-1.5 pt-4 sm:pt-0">
              <button
                type="button"
                class="btn-step-progress px-2 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-xs font-semibold border border-slate-200 transition cursor-pointer"
                data-add="5"
              >
                +5%
              </button>
              <button
                type="button"
                class="btn-step-progress px-2 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-xs font-semibold border border-slate-200 transition cursor-pointer"
                data-add="10"
              >
                +10%
              </button>
              <button
                type="button"
                class="btn-step-progress px-2 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-xs font-semibold border border-slate-200 transition cursor-pointer"
                data-add="25"
              >
                +25%
              </button>
            </div>
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-1">
            <p class="text-[11px] text-slate-400">
              Backend enforces non-reversing progression (<span class="font-mono">progress &ge; ${currentProgress.toFixed(1)}%</span>).
            </p>
            <button
              type="submit"
              id="btn-send-progress"
              class="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shadow-sm transition flex items-center justify-center space-x-1 cursor-pointer"
            >
              <span>Report Route Progress</span>
            </button>
          </div>
        </form>
      </div>

    </div>
  `;
}
