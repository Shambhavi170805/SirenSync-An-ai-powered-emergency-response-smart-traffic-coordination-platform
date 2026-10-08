export function renderReservationsTable(container, { reservations }) {
  if (!reservations || reservations.length === 0) {
    container.innerHTML = `
      <div class="bg-white p-12 text-center rounded-2xl border border-slate-200">
        <div class="w-12 h-12 rounded-full bg-slate-50 text-slate-400 flex items-center justify-center mx-auto mb-3">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        </div>
        <h3 class="text-sm font-semibold text-slate-900">No Bed Reservations</h3>
        <p class="text-xs text-slate-500 mt-1 max-w-sm mx-auto">No active or historical bed reservation records found for this facility.</p>
      </div>
    `;
    return;
  }

  const statusBadges = {
    RESERVED: '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-800"><span class="w-1.5 h-1.5 rounded-full bg-amber-500 mr-1 animate-pulse"></span>ACTIVE LOCK</span>',
    OCCUPIED: '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-sky-100 text-sky-800">ADMITTED</span>',
    RELEASED_FOR_REASSIGNMENT: '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-purple-100 text-purple-800">REASSIGNED</span>',
    CANCELLED: '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600">CANCELLED</span>',
  };

  const rows = reservations.map(r => {
    const sBadge = statusBadges[r.status] || `<span class="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700">${r.status}</span>`;
    const reservedTime = new Date(r.reservedAt).toLocaleString();

    let detailsCol = '<span class="text-slate-400 text-xs">Standard allocation</span>';
    if (r.status === 'RELEASED_FOR_REASSIGNMENT') {
      detailsCol = `<span class="text-purple-700 text-xs font-medium flex items-center">
        <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/></svg>
        Reassigned to: <span class="font-mono ml-1 font-bold">${r.reassignedToEmergencyId || 'New Case'}</span>
      </span>`;
    }

    return `
      <tr class="hover:bg-slate-50/80 transition-colors border-b border-slate-100 text-xs">
        <td class="px-4 py-3.5 whitespace-nowrap font-mono font-bold text-slate-900">
          ${r.reservationId}
        </td>
        <td class="px-4 py-3.5 whitespace-nowrap font-mono text-slate-700">
          ${r.emergencyId}
        </td>
        <td class="px-4 py-3.5 whitespace-nowrap">
          <span class="font-bold text-slate-900">${r.bedNumber}</span>
          <span class="text-slate-400 text-[10px] ml-1">(${r.bedType})</span>
        </td>
        <td class="px-4 py-3.5 whitespace-nowrap">
          ${sBadge}
        </td>
        <td class="px-4 py-3.5">
          ${detailsCol}
        </td>
        <td class="px-4 py-3.5 whitespace-nowrap text-slate-500">
          ${reservedTime}
        </td>
      </tr>
    `;
  }).join('');

  container.innerHTML = `
    <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
      
      <div class="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 class="text-sm font-bold text-slate-900 tracking-tight">Active & Historical Bed Reservations</h3>
          <p class="text-xs text-slate-500">Verified database reservations with atomic concurrency locking audit trail</p>
        </div>
        <span class="px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 font-bold text-xs">
          ${reservations.length} Total Records
        </span>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-200 text-left">
          <thead class="bg-slate-50/80 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            <tr>
              <th scope="col" class="px-4 py-3">Reservation ID</th>
              <th scope="col" class="px-4 py-3">Emergency ID</th>
              <th scope="col" class="px-4 py-3">Locked Bed</th>
              <th scope="col" class="px-4 py-3">Status</th>
              <th scope="col" class="px-4 py-3">Audit Details</th>
              <th scope="col" class="px-4 py-3">Timestamp</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 bg-white">
            ${rows}
          </tbody>
        </table>
      </div>

    </div>
  `;
}
