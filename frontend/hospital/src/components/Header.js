export function renderHeader(container, { hospitals, selectedHospitalId, onSelectHospital, onRefresh, isRefreshing, hospitalDetail }) {
  const hospitalOptions = hospitals.map(h => 
    `<option value="${h.id}" ${h.id === selectedHospitalId ? 'selected' : ''}>${h.name} (${h.id})</option>`
  ).join('');

  const capsBadges = (hospitalDetail?.capabilities || []).map(c => 
    `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
       ${c.capability_code}
     </span>`
  ).join(' ');

  container.innerHTML = `
    <header class="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          
          <!-- Logo & Title -->
          <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-rose-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-rose-500/20">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
            <div>
              <div class="flex items-center space-x-2">
                <h1 class="text-lg font-bold text-slate-900 tracking-tight">SirenSync</h1>
                <span class="px-2 py-0.5 text-xs font-semibold bg-rose-100 text-rose-700 rounded-full">Hospital Ops Desk</span>
              </div>
              <p class="text-xs text-slate-500">Hospital Intelligence & Bed Management • Samriddhi</p>
            </div>
          </div>

          <!-- Hospital Selector & Live Controls -->
          <div class="flex items-center space-x-3">
            
            <div class="relative">
              <select id="hospital-selector" class="block w-64 pl-3 pr-8 py-1.5 text-xs font-medium text-slate-700 bg-slate-50 border border-slate-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-rose-500 cursor-pointer">
                ${hospitalOptions}
              </select>
            </div>

            <!-- Auto-refresh Notice Badge -->
            <div class="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-medium">
              <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Online • Polling: 10s</span>
            </div>

            <!-- Manual Refresh Button -->
            <button id="btn-manual-refresh" class="inline-flex items-center px-3 py-1.5 border border-slate-300 shadow-sm text-xs font-medium rounded-lg text-slate-700 bg-white hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-rose-500 transition-colors">
              <svg class="w-3.5 h-3.5 mr-1.5 text-slate-500 ${isRefreshing ? 'animate-spin' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              ${isRefreshing ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>

        </div>

        <!-- Hospital Sub-bar: Address, Contact & Capabilities -->
        ${hospitalDetail ? `
          <div class="py-2.5 border-t border-slate-100 flex flex-wrap items-center justify-between text-xs text-slate-600 gap-2">
            <div class="flex items-center space-x-4 flex-wrap">
              <span class="flex items-center">
                <svg class="w-3.5 h-3.5 mr-1 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                ${hospitalDetail.address}
              </span>
              <span class="flex items-center">
                <svg class="w-3.5 h-3.5 mr-1 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                </svg>
                ${hospitalDetail.contact_number}
              </span>
            </div>
            <div class="flex items-center space-x-1.5 flex-wrap">
              <span class="text-slate-400 font-medium mr-1">Capabilities:</span>
              ${capsBadges}
            </div>
          </div>
        ` : ''}

      </div>
    </header>
  `;

  // Bind Events
  container.querySelector('#hospital-selector').addEventListener('change', (e) => {
    onSelectHospital(e.target.value);
  });

  container.querySelector('#btn-manual-refresh').addEventListener('click', () => {
    onRefresh();
  });
}
