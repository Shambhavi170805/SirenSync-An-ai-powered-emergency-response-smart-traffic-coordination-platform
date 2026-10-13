/**
 * RerouteBanner Component
 * Displays prominent, real-time reroute alerts when Samriddhi's bed reassignment
 * policy approves a bed reassignment (< 40% route progress) and emits BED_REASSIGNMENT_REROUTE.
 * Automatically synchronizes with authoritative backend destination state.
 */

import { escapeHtml } from '../utils.js';

export function renderRerouteBanner(state, onAcknowledgeReroute) {
  const alert = state.rerouteAlert;
  if (!alert) return '';

  return `
    <div class="bg-rose-50 border-2 border-rose-500 rounded-xl p-4 sm:p-5 shadow-lg shadow-rose-900/10 mb-6 animate-pulse">
      <div class="flex items-start justify-between gap-3">
        <div class="flex items-start space-x-3">
          <div class="h-10 w-10 rounded-xl bg-rose-600 text-white flex items-center justify-center shrink-0">
            <svg class="w-6 h-6 animate-spin" style="animation-duration: 3s;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <span class="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-rose-600 text-white tracking-wider">
                URGENT REROUTE REQUIRED
              </span>
              <span class="text-xs text-rose-800 font-mono font-semibold">${escapeHtml(alert.eventType || 'BED_REASSIGNMENT_REROUTE')}</span>
            </div>
            <h3 class="text-base font-bold text-rose-950 mt-1">
              Destination Hospital Reassigned: Proceed to New Facility
            </h3>
            <p class="text-xs text-rose-800 mt-0.5 leading-relaxed">
              ${escapeHtml(alert.reason || 'Priority escalation displaced bed reservation at previous hospital (< 40% route progress threshold).')}
            </p>

            <div class="flex flex-wrap items-center gap-4 mt-3 pt-3 border-t border-rose-200/70 text-xs">
              <div>
                <span class="text-rose-600 block text-[10px] uppercase font-bold">Previous Destination</span>
                <span class="font-mono font-bold text-rose-900 line-through">${escapeHtml(alert.previousHospitalId || 'Previous Hospital')}</span>
              </div>
              <div class="text-rose-400 font-bold text-lg">&rarr;</div>
              <div>
                <span class="text-rose-600 block text-[10px] uppercase font-bold">New Destination Hospital</span>
                <span class="font-mono font-black text-rose-950 text-sm bg-rose-200/60 px-2 py-0.5 rounded">${escapeHtml(alert.newHospitalId || 'New Assigned Facility')}</span>
              </div>
              <div>
                <span class="text-rose-600 block text-[10px] uppercase font-bold">Route Progress</span>
                <span class="font-mono font-bold text-rose-900">${typeof alert.routeProgress === 'number' && Number.isFinite(alert.routeProgress) ? `Reset to ${alert.routeProgress.toFixed(1)}% (New Destination Branch)` : 'Reset to 0.0% (New Destination Branch)'}</span>
              </div>
            </div>
          </div>
        </div>

        <button
          id="btn-ack-reroute"
          class="shrink-0 px-3.5 py-2 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-lg shadow transition cursor-pointer"
        >
          Acknowledge & Sync
        </button>
      </div>
    </div>
  `;
}
