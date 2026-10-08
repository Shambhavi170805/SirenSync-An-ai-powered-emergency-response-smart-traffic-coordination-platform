export function renderEmergencyQueue(container, { queue }) {
  if (!queue || queue.length === 0) {
    container.innerHTML = `
      <div class="bg-white p-12 text-center rounded-2xl border border-slate-200">
        <div class="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-3">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 class="text-sm font-semibold text-slate-900">Queue is Clear</h3>
        <p class="text-xs text-slate-500 mt-1 max-w-sm mx-auto">No inbound emergency cases are currently coordinated or queued for this receiving facility.</p>
      </div>
    `;
    return;
  }

  const priorityStyles = {
    P1_CRITICAL: {
      badge: 'bg-rose-100 text-rose-800 border-rose-200',
      dot: 'bg-rose-500 animate-ping',
      label: 'P1 CRITICAL (Resuscitation)'
    },
    P2_EMERGENCY: {
      badge: 'bg-orange-100 text-orange-800 border-orange-200',
      dot: 'bg-orange-500',
      label: 'P2 EMERGENCY (Severe)'
    },
    P3_URGENT: {
      badge: 'bg-amber-100 text-amber-800 border-amber-200',
      dot: 'bg-amber-500',
      label: 'P3 URGENT'
    },
    P4_NON_URGENT: {
      badge: 'bg-blue-100 text-blue-800 border-blue-200',
      dot: 'bg-blue-500',
      label: 'P4 NON-URGENT'
    },
  };

  const rows = queue.map((item, idx) => {
    const pStyle = priorityStyles[item.priority] || priorityStyles.P3_URGENT;
    const progress = Math.min(100, Math.max(0, item.route_progress || 0));
    const createdTime = new Date(item.created_at).toLocaleTimeString();

    let statusStyle = 'bg-slate-100 text-slate-700';
    if (item.status === 'EN_ROUTE') statusStyle = 'bg-indigo-100 text-indigo-700';
    else if (item.status === 'ARRIVED') statusStyle = 'bg-emerald-100 text-emerald-800';
    else if (item.status === 'REROUTED') statusStyle = 'bg-purple-100 text-purple-800 border-purple-200';

    return `
      <tr class="hover:bg-slate-50/80 transition-colors border-b border-slate-100">
        <td class="px-4 py-3.5 whitespace-nowrap text-xs font-bold text-slate-900 flex items-center">
          <span class="w-6 h-6 rounded-full bg-slate-100 text-slate-600 inline-flex items-center justify-center font-bold text-[10px] mr-2">
            #${idx + 1}
          </span>
          <span class="font-mono text-slate-700">${item.emergency_id}</span>
        </td>
        <td class="px-4 py-3.5 whitespace-nowrap">
          <span class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold border ${pStyle.badge}">
            <span class="w-1.5 h-1.5 rounded-full ${pStyle.dot} mr-1.5"></span>
            ${pStyle.label}
          </span>
        </td>
        <td class="px-4 py-3.5 whitespace-nowrap">
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${statusStyle}">
            ${item.status}
          </span>
        </td>
        <td class="px-4 py-3.5 whitespace-nowrap">
          <div class="w-36">
            <div class="flex items-center justify-between text-[11px] font-medium text-slate-600 mb-1">
              <span>Transit Progress</span>
              <span class="font-bold">${progress}%</span>
            </div>
            <div class="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
              <div class="bg-gradient-to-r from-rose-500 to-indigo-600 h-1.5 transition-all duration-300" style="width: ${progress}%"></div>
            </div>
          </div>
        </td>
        <td class="px-4 py-3.5 text-xs text-slate-600 max-w-xs truncate" title="${item.notes || 'Coordinating dispatch'}">
          ${item.notes || 'Coordinating ambulance dispatch'}
        </td>
        <td class="px-4 py-3.5 whitespace-nowrap text-xs text-slate-400">
          ${createdTime}
        </td>
      </tr>
    `;
  }).join('');

  container.innerHTML = `
    <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
      
      <div class="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 class="text-sm font-bold text-slate-900 tracking-tight">Incoming Emergency Priority Queue</h3>
          <p class="text-xs text-slate-500">Live clinical triage hierarchy for incoming ambulance arrivals</p>
        </div>
        <span class="px-2.5 py-1 rounded-full bg-rose-50 border border-rose-200 text-rose-700 font-bold text-xs">
          ${queue.length} Inbound Cases
        </span>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-200 text-left">
          <thead class="bg-slate-50/80 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            <tr>
              <th scope="col" class="px-4 py-3">Emergency Case</th>
              <th scope="col" class="px-4 py-3">Triage Priority</th>
              <th scope="col" class="px-4 py-3">Coordination Status</th>
              <th scope="col" class="px-4 py-3">Route Progress</th>
              <th scope="col" class="px-4 py-3">Operational Notes</th>
              <th scope="col" class="px-4 py-3">Initiated At</th>
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
