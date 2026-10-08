export function renderBedGrid(container, { beds, onUpdateStatus, selectedCategory = 'ALL', selectedStatus = 'ALL', onFilterChange }) {
  if (!beds || beds.length === 0) {
    container.innerHTML = `
      <div class="bg-white p-12 text-center rounded-2xl border border-slate-200">
        <svg class="mx-auto h-12 w-12 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
        <h3 class="mt-2 text-sm font-medium text-slate-900">No beds found</h3>
        <p class="mt-1 text-xs text-slate-500">No beds match the current category or status filter.</p>
      </div>
    `;
    return;
  }

  // Filter beds
  const filteredBeds = beds.filter(bed => {
    const matchesCat = selectedCategory === 'ALL' || bed.bed_type === selectedCategory;
    const matchesStat = selectedStatus === 'ALL' || bed.status === selectedStatus;
    return matchesCat && matchesStat;
  });

  const categories = ['ALL', 'ICU', 'TRAUMA_EMERGENCY', 'OXYGEN_HDU', 'GENERAL_WARD', 'PEDIATRIC_ICU'];
  const statuses = ['ALL', 'AVAILABLE', 'RESERVED', 'OCCUPIED'];

  const categoryPills = categories.map(cat => `
    <button class="filter-cat-btn px-3 py-1 text-xs font-medium rounded-lg transition-colors ${selectedCategory === cat ? 'bg-slate-900 text-white shadow-sm' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'}" data-cat="${cat}">
      ${cat.replace('_', ' ')}
    </button>
  `).join('');

  const statusPills = statuses.map(stat => `
    <button class="filter-stat-btn px-3 py-1 text-xs font-medium rounded-lg transition-colors ${selectedStatus === stat ? 'bg-slate-900 text-white shadow-sm' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'}" data-stat="${stat}">
      ${stat}
    </button>
  `).join('');

  const bedCards = filteredBeds.map(bed => {
    let statusBadge = '';
    let cardBorder = '';
    let actionBtn = '';

    if (bed.status === 'AVAILABLE') {
      statusBadge = '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-emerald-100 text-emerald-800"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1 animate-pulse"></span>AVAILABLE</span>';
      cardBorder = 'border-slate-200 hover:border-emerald-300';
      actionBtn = `
        <button class="btn-toggle-bed w-full text-xs font-medium py-1.5 px-2 rounded-lg bg-slate-100 hover:bg-sky-50 hover:text-sky-700 text-slate-700 transition-colors" data-bed-id="${bed.id}" data-action="OCCUPIED">
          Mark Occupied
        </button>
      `;
    } else if (bed.status === 'RESERVED') {
      statusBadge = '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-800"><svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>RESERVED</span>';
      cardBorder = 'border-amber-200 bg-amber-50/20';
      actionBtn = `
        <button class="btn-toggle-bed w-full text-xs font-medium py-1.5 px-2 rounded-lg bg-amber-100 hover:bg-amber-200 text-amber-900 transition-colors" data-bed-id="${bed.id}" data-action="OCCUPIED">
          Confirm Admission (Occupied)
        </button>
      `;
    } else if (bed.status === 'OCCUPIED') {
      statusBadge = '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-sky-100 text-sky-800">OCCUPIED</span>';
      cardBorder = 'border-sky-200 bg-sky-50/10';
      actionBtn = `
        <button class="btn-toggle-bed w-full text-xs font-medium py-1.5 px-2 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 transition-colors" data-bed-id="${bed.id}" data-action="AVAILABLE">
          Discharge (Set Available)
        </button>
      `;
    } else {
      statusBadge = `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-slate-100 text-slate-800">${bed.status}</span>`;
      cardBorder = 'border-slate-200';
      actionBtn = `
        <button class="btn-toggle-bed w-full text-xs font-medium py-1.5 px-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors" data-bed-id="${bed.id}" data-action="AVAILABLE">
          Set Available
        </button>
      `;
    }

    return `
      <div class="bg-white p-4 rounded-xl border ${cardBorder} shadow-sm hover:shadow transition-all flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-bold text-slate-900">${bed.bed_number}</span>
            ${statusBadge}
          </div>
          <div class="text-xs text-slate-500 mb-1 flex items-center">
            <span class="font-medium text-slate-700 mr-1">${bed.bed_type}</span>
          </div>
          <p class="text-[11px] text-slate-400 truncate mb-3">${bed.department}</p>
        </div>
        <div>
          <div class="text-[10px] text-slate-400 mb-2 truncate">ID: ${bed.id}</div>
          ${actionBtn}
        </div>
      </div>
    `;
  }).join('');

  container.innerHTML = `
    <div class="space-y-4">
      
      <!-- Filter Toolbar -->
      <div class="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1.5">Specialization</span>
          <div class="flex items-center space-x-1.5 flex-wrap gap-y-1">
            ${categoryPills}
          </div>
        </div>
        <div>
          <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1.5">Bed Status</span>
          <div class="flex items-center space-x-1.5 flex-wrap gap-y-1">
            ${statusPills}
          </div>
        </div>
      </div>

      <!-- Result Count Info -->
      <div class="flex items-center justify-between text-xs text-slate-500 px-1">
        <span>Showing <strong>${filteredBeds.length}</strong> of ${beds.length} total hospital beds</span>
      </div>

      <!-- Beds Grid -->
      <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
        ${bedCards}
      </div>

    </div>
  `;

  // Bind filter events
  container.querySelectorAll('.filter-cat-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      onFilterChange({ category: btn.dataset.cat, status: selectedStatus });
    });
  });

  container.querySelectorAll('.filter-stat-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      onFilterChange({ category: selectedCategory, status: btn.dataset.stat });
    });
  });

  // Bind toggle action events
  container.querySelectorAll('.btn-toggle-bed').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const bedId = e.currentTarget.dataset.bedId;
      const targetAction = e.currentTarget.dataset.action;
      onUpdateStatus(bedId, targetAction);
    });
  });
}
