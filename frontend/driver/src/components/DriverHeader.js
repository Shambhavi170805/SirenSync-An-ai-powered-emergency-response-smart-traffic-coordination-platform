/**
 * DriverHeader Component
 * Displays ambulance identity, vehicle badge, driver name, vehicle switcher,
 * and live WebSocket / REST telemetry stream connection status.
 */

import { escapeHtml, formatLocation } from '../utils.js';

export function renderDriverHeader(state, onSelectAmbulance, onRefresh) {
  const currentAmb = state.selectedAmbulance;
  const isWsConnected = state.wsConnected;
  const isRestFallback = state.usingRestFallback;
  const hasEmergency = Boolean(currentAmb?.assignedEmergencyId);

  // Status badge styling
  const statusStyles = {
    AVAILABLE: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    ASSIGNED: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    EN_ROUTE_PICKUP: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    PATIENT_ONBOARD: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
    EN_ROUTE_HOSPITAL: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
    ARRIVED: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    MAINTENANCE: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
  };

  const typeBadges = {
    MICU: 'bg-rose-600 text-white font-bold',
    ALS: 'bg-blue-600 text-white font-semibold',
    BLS: 'bg-slate-600 text-slate-100 font-medium',
  };

  const locDisplay = currentAmb ? formatLocation(currentAmb.currentLocation) : '';

  return `
    <header class="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-30 shadow-lg">
      <div class="max-w-6xl mx-auto px-4 py-3 sm:px-6 flex flex-col md:flex-row md:items-center md:justify-between gap-3">

        <!-- Logo & Title -->
        <div class="flex items-center space-x-3">
          <div class="h-10 w-10 rounded-xl bg-gradient-to-tr from-rose-600 to-amber-500 flex items-center justify-center shadow-md shadow-rose-900/30">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <h1 class="text-lg font-bold tracking-tight text-white">SirenSync</h1>
              <span class="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30">
                Driver Console
              </span>
              <span class="text-[10px] text-slate-400 hidden sm:inline">• Member 3</span>
            </div>
            <p class="text-xs text-slate-400">Emergency Telemetry & Inbound Dispatch HUD</p>
          </div>
        </div>

        <!-- Vehicle Selector & Live Indicators -->
        <div class="flex flex-wrap items-center gap-2 sm:gap-3">

          <!-- Vehicle Switcher Dropdown -->
          <div class="flex items-center space-x-1 bg-slate-800/80 rounded-lg p-1 border border-slate-700">
            <label for="ambulance-selector" class="text-xs text-slate-400 pl-2 font-medium">Vehicle:</label>
            <select
              id="ambulance-selector"
              class="bg-slate-900 text-slate-100 text-xs font-semibold rounded px-2.5 py-1.5 border border-slate-700 focus:outline-none focus:ring-1 focus:ring-rose-500 cursor-pointer"
            >
              ${state.fleet.map(amb => `
                <option value="${escapeHtml(amb.id)}" ${currentAmb?.id === amb.id ? 'selected' : ''}>
                  ${escapeHtml(amb.vehicleNumber)} (${escapeHtml(amb.ambulanceType)}) - ${escapeHtml(amb.driverName)} [${escapeHtml(amb.status)}]
                </option>
              `).join('')}
            </select>
          </div>

          <!-- Connection Status Pill -->
          <div class="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border bg-slate-800/70 border-slate-700">
            ${hasEmergency ? (
              isWsConnected ? `
                <span class="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span class="text-emerald-400 font-semibold">Live WS Stream</span>
              ` : (isRestFallback ? `
                <span class="h-2 w-2 rounded-full bg-amber-400"></span>
                <span class="text-amber-400">REST Fallback</span>
              ` : `
                <span class="h-2 w-2 rounded-full bg-rose-400"></span>
                <span class="text-rose-400">Connecting...</span>
              `)
            ) : `
              <span class="h-2 w-2 rounded-full bg-slate-500"></span>
              <span class="text-slate-400">Channel Standby</span>
            `}
          </div>

          <!-- Refresh Button -->
          <button
            id="btn-refresh-state"
            class="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium border border-slate-700 transition flex items-center space-x-1 cursor-pointer"
            title="Refresh state from backend"
          >
            <svg class="w-3.5 h-3.5 ${state.isRefreshing ? 'animate-spin' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span class="hidden sm:inline">Sync</span>
          </button>
        </div>

      </div>

      <!-- Quick Vehicle Meta Bar -->
      ${currentAmb ? `
        <div class="bg-slate-950/70 border-t border-slate-800/80 px-4 py-2 text-xs">
          <div class="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-2">
            <div class="flex items-center space-x-2">
              <span class="text-slate-400">Driver:</span>
              <span class="font-bold text-slate-200">${escapeHtml(currentAmb.driverName)}</span>
              <span class="text-slate-500 font-mono text-[11px]">${escapeHtml(currentAmb.driverContact)}</span>
              <span class="text-slate-600">•</span>
              <span class="px-1.5 py-0.5 rounded text-[10px] ${typeBadges[currentAmb.ambulanceType] || 'bg-slate-700'}">
                ${escapeHtml(currentAmb.ambulanceType)}
              </span>
            </div>

            <div class="flex items-center space-x-2">
              <span class="text-slate-400">Status:</span>
              <span class="px-2 py-0.5 rounded-full text-[11px] font-semibold border ${statusStyles[currentAmb.status] || 'bg-slate-800 text-slate-300'}">
                ${escapeHtml(currentAmb.status.replace(/_/g, ' '))}
              </span>
              <span class="text-slate-600">•</span>
              <span class="text-slate-400">Location:</span>
              <span class="text-slate-300 font-mono text-[11px] truncate max-w-[200px]" title="${escapeHtml(locDisplay)}">
                ${escapeHtml(locDisplay)}
              </span>
            </div>
          </div>
        </div>
      ` : ''}
    </header>
  `;
}
