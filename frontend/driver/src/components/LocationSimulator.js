/** Automatic browser GPS telemetry panel. Real coordinates require driver permission. */
export function renderLocationSimulator(state) {
  const amb = state.selectedAmbulance;
  if (!amb) return '';
  const assigned = Boolean(amb.assignedEmergencyId);
  const live = Boolean(state.liveGpsActive);
  const gpsMessage = state.liveGpsMessage || (assigned ? 'Waiting for device location permission…' : 'GPS starts automatically when an emergency is assigned.');
  return `
    <section class="bg-white rounded-xl shadow-sm border border-slate-200 p-5 sm:p-6 space-y-3">
      <div class="flex items-center justify-between gap-3">
        <div>
          <h3 class="text-sm font-bold text-slate-900">Automatic Live GPS</h3>
          <p class="text-xs text-slate-500 mt-1">The driver's device sends location updates automatically. Route progress is calculated from GPS movement.</p>
        </div>
        <span class="px-2 py-1 rounded text-[10px] font-bold uppercase ${live ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">${live ? 'GPS Active' : 'GPS Standby'}</span>
      </div>
      <div class="rounded-lg bg-slate-50 border border-slate-200 p-3 text-xs text-slate-700">${gpsMessage}</div>
      ${state.routeSummary ? `<div class="grid grid-cols-2 gap-2"><div class="rounded-lg border border-slate-200 p-3"><div class="text-[10px] uppercase text-slate-500 font-bold">Traffic-aware ETA</div><div class="text-sm font-bold text-slate-900 mt-1">${Math.max(1, Math.round(state.routeSummary.durationSeconds / 60))} min</div></div><div class="rounded-lg border border-slate-200 p-3"><div class="text-[10px] uppercase text-slate-500 font-bold">Road distance</div><div class="text-sm font-bold text-slate-900 mt-1">${(Number(state.routeSummary.distanceMeters || 0) / 1000).toFixed(1)} km</div></div></div><div class="text-[11px] text-emerald-700 font-semibold">Google Routes • Traffic-aware • ${state.routeSummary.trafficSummary || 'Current traffic incorporated'}</div>` : `<div class="text-[11px] text-amber-700">Live traffic ETA and road geometry become available after GOOGLE_MAPS_API_KEY is configured. GPS-only progress is an estimate.</div>`}
      <div class="flex flex-wrap items-center justify-between gap-2">
        <span class="text-[11px] text-slate-500">${assigned ? `Emergency ${amb.assignedEmergencyId}` : 'No active assignment'}</span>
        ${assigned ? `<button id="btn-start-live-gps" class="px-3 py-2 rounded-lg text-xs font-semibold ${live ? 'bg-slate-200 text-slate-700' : 'bg-emerald-600 text-white hover:bg-emerald-700'}">${live ? 'Restart GPS' : 'Enable device GPS'}</button>` : ''}
      </div>
      <p class="text-[10px] text-slate-400">Use the driver dashboard on the ambulance driver's phone over HTTPS (localhost is also supported for testing). Browser location permission is required. Simulated coordinates are never marked as live.</p>
    </section>`;
}
