export function renderStatsOverview(container, { bedSummary, queueCount, activeReservationsCount }) {
  if (!bedSummary) {
    container.innerHTML = `
      <div class="animate-pulse space-y-4">
        <div class="h-24 bg-slate-100 rounded-xl"></div>
      </div>
    `;
    return;
  }

  const { total_beds, available_beds, reserved_beds, occupied_beds, by_category } = bedSummary;
  const availPct = total_beds > 0 ? Math.round((available_beds / total_beds) * 100) : 0;
  const resPct = total_beds > 0 ? Math.round((reserved_beds / total_beds) * 100) : 0;
  const occPct = total_beds > 0 ? Math.round((occupied_beds / total_beds) * 100) : 0;

  // Category cards
  const categoryCards = Object.entries(by_category || {}).map(([catKey, counts]) => {
    const catAvailPct = counts.total > 0 ? Math.round((counts.available / counts.total) * 100) : 0;
    let badgeColor = "bg-emerald-50 text-emerald-700 border-emerald-200";
    if (counts.available === 0) badgeColor = "bg-rose-50 text-rose-700 border-rose-200";
    else if (catAvailPct < 25) badgeColor = "bg-amber-50 text-amber-700 border-amber-200";

    const formattedCatName = catKey.replace('_', ' ');

    return `
      <div class="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm hover:border-slate-300 transition-all">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-semibold uppercase tracking-wider text-slate-500">${formattedCatName}</span>
          <span class="px-2 py-0.5 text-xs font-medium rounded-md border ${badgeColor}">
            ${counts.available} / ${counts.total} Available
          </span>
        </div>
        <div class="w-full bg-slate-100 rounded-full h-2 mb-3 overflow-hidden flex">
          <div class="bg-emerald-500 h-2" style="width: ${catAvailPct}%" title="Available: ${counts.available}"></div>
          <div class="bg-amber-400 h-2" style="width: ${counts.total > 0 ? (counts.reserved / counts.total)*100 : 0}%" title="Reserved: ${counts.reserved}"></div>
          <div class="bg-sky-500 h-2" style="width: ${counts.total > 0 ? (counts.occupied / counts.total)*100 : 0}%" title="Occupied: ${counts.occupied}"></div>
        </div>
        <div class="grid grid-cols-3 gap-1 text-center text-xs">
          <div class="bg-slate-50 py-1 rounded">
            <span class="text-slate-400 block text-[10px]">AVAIL</span>
            <span class="font-bold text-emerald-600">${counts.available}</span>
          </div>
          <div class="bg-slate-50 py-1 rounded">
            <span class="text-slate-400 block text-[10px]">RSVD</span>
            <span class="font-bold text-amber-600">${counts.reserved}</span>
          </div>
          <div class="bg-slate-50 py-1 rounded">
            <span class="text-slate-400 block text-[10px]">OCC</span>
            <span class="font-bold text-sky-600">${counts.occupied}</span>
          </div>
        </div>
      </div>
    `;
  }).join('');

  container.innerHTML = `
    <div class="space-y-6">
      
      <!-- Top Operational KPI Tiles -->
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        
        <!-- Total Beds -->
        <div class="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm relative overflow-hidden">
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Capacity</span>
            <div class="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-600">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5" />
              </svg>
            </div>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span class="text-3xl font-extrabold text-slate-900">${total_beds}</span>
            <span class="text-xs text-slate-400">beds configured</span>
          </div>
        </div>

        <!-- Available Beds -->
        <div class="bg-white p-5 rounded-2xl border border-emerald-100 shadow-sm bg-gradient-to-br from-white to-emerald-50/30">
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium text-emerald-800 uppercase tracking-wider">Available Beds</span>
            <div class="w-8 h-8 rounded-lg bg-emerald-100/80 flex items-center justify-center text-emerald-700">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span class="text-3xl font-extrabold text-emerald-600">${available_beds}</span>
            <span class="text-xs font-semibold px-1.5 py-0.5 bg-emerald-100 text-emerald-700 rounded-md">${availPct}%</span>
          </div>
        </div>

        <!-- Reserved Beds -->
        <div class="bg-white p-5 rounded-2xl border border-amber-100 shadow-sm bg-gradient-to-br from-white to-amber-50/30">
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium text-amber-800 uppercase tracking-wider">Reserved Locks</span>
            <div class="w-8 h-8 rounded-lg bg-amber-100/80 flex items-center justify-center text-amber-700">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span class="text-3xl font-extrabold text-amber-600">${reserved_beds}</span>
            <span class="text-xs text-amber-600 font-medium">${activeReservationsCount} active locks</span>
          </div>
        </div>

        <!-- Occupied Beds -->
        <div class="bg-white p-5 rounded-2xl border border-sky-100 shadow-sm bg-gradient-to-br from-white to-sky-50/30">
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium text-sky-800 uppercase tracking-wider">Occupied / In Use</span>
            <div class="w-8 h-8 rounded-lg bg-sky-100/80 flex items-center justify-center text-sky-700">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span class="text-3xl font-extrabold text-sky-700">${occupied_beds}</span>
            <span class="text-xs text-slate-400 font-medium">${occPct}% full</span>
          </div>
        </div>

        <!-- Emergency Queue -->
        <div class="bg-white p-5 rounded-2xl border border-rose-100 shadow-sm bg-gradient-to-br from-white to-rose-50/30 col-span-2 sm:col-span-1">
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium text-rose-800 uppercase tracking-wider">Inbound Queue</span>
            <div class="w-8 h-8 rounded-lg bg-rose-100/80 flex items-center justify-center text-rose-700">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span class="text-3xl font-extrabold text-rose-600">${queueCount || 0}</span>
            <span class="text-xs text-rose-600 font-medium">inbound cases</span>
          </div>
        </div>

      </div>

      <!-- Capacity Visual Progress Bar -->
      <div class="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
        <div class="flex items-center justify-between text-xs font-medium text-slate-600 mb-2">
          <span>Overall Capacity Allocation</span>
          <div class="flex items-center space-x-4">
            <span class="inline-flex items-center"><span class="w-2.5 h-2.5 rounded-full bg-emerald-500 mr-1.5"></span>Available (${available_beds})</span>
            <span class="inline-flex items-center"><span class="w-2.5 h-2.5 rounded-full bg-amber-400 mr-1.5"></span>Reserved (${reserved_beds})</span>
            <span class="inline-flex items-center"><span class="w-2.5 h-2.5 rounded-full bg-sky-500 mr-1.5"></span>Occupied (${occupied_beds})</span>
          </div>
        </div>
        <div class="w-full bg-slate-100 rounded-full h-3 overflow-hidden flex shadow-inner">
          <div class="bg-emerald-500 transition-all duration-500" style="width: ${availPct}%"></div>
          <div class="bg-amber-400 transition-all duration-500" style="width: ${resPct}%"></div>
          <div class="bg-sky-500 transition-all duration-500" style="width: ${occPct}%"></div>
        </div>
      </div>

      <!-- Category Breakdown Grid -->
      <div>
        <h3 class="text-sm font-bold text-slate-800 uppercase tracking-wider mb-3">Bed Allocation by Specialization</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          ${categoryCards}
        </div>
      </div>

    </div>
  `;
}
