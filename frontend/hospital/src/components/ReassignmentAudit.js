export function renderReassignmentAudit(container, { auditLogs, onTriggerScenario, lastReassignmentResult, isEvaluating }) {
  const auditRows = (auditLogs || []).map(log => {
    const isApproved = log.decision === 'REASSIGNMENT_APPROVED';
    const isUnderThreshold = log.routeProgress < (log.threshold || 40.0);
    const decisionBadge = isApproved
      ? '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">APPROVED (&lt;40%)</span>'
      : '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800 border border-amber-300">REJECTED (&ge;40%)</span>';

    const rerouteInfo = isApproved
      ? `<div class="text-[11px] text-emerald-700 font-medium">Reroute: <span class="font-mono font-bold">${log.newHospitalId || 'Alternative Hosp'}</span></div>`
      : `<div class="text-[11px] text-slate-500 font-medium">Reservation Retained</div>`;

    return `
      <tr class="hover:bg-slate-50/80 transition-colors border-b border-slate-100 text-xs">
        <td class="px-4 py-3 font-mono font-bold text-slate-800 text-[11px]">${log.eventId}</td>
        <td class="px-4 py-3 whitespace-nowrap">${decisionBadge}</td>
        <td class="px-4 py-3 whitespace-nowrap">
          <span class="font-bold ${isUnderThreshold ? 'text-emerald-600' : 'text-amber-600'}">
            ${Number(log.routeProgress).toFixed(1)}%
          </span>
          <span class="text-slate-400 text-[10px]"> (threshold: ${log.threshold || 40}%)</span>
        </td>
        <td class="px-4 py-3">
          <div class="font-mono text-slate-800 font-bold text-[11px]">${log.displacingEmergencyId}</div>
          <span class="inline-block px-1.5 py-0.2 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-200">${log.displacingPriority}</span>
        </td>
        <td class="px-4 py-3">
          <div class="font-mono text-slate-600 text-[11px]">${log.displacedEmergencyId}</div>
          <span class="inline-block px-1.5 py-0.2 rounded text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200">${log.displacedPriority}</span>
        </td>
        <td class="px-4 py-3">
          ${rerouteInfo}
          <div class="text-[10px] text-slate-400 truncate max-w-xs" title="${log.reason}">${log.reason}</div>
        </td>
        <td class="px-4 py-3 whitespace-nowrap text-slate-500 font-mono text-[11px]">
          ${new Date(log.createdAt).toLocaleTimeString()}
        </td>
      </tr>
    `;
  }).join('');

  // Result card data parsing
  let resultSection = '';
  if (lastReassignmentResult) {
    const isApproved = lastReassignmentResult.decision === 'REASSIGNMENT_APPROVED';
    const progress = lastReassignmentResult.routeProgress != null ? Number(lastReassignmentResult.routeProgress) : (isApproved ? 25.0 : 65.0);
    const threshold = lastReassignmentResult.thresholdPercent || 40.0;
    const isUnderThreshold = progress < threshold;

    const scenarioTitle = lastReassignmentResult.scenarioName 
      || (isUnderThreshold ? 'Scenario C (< 40% Route Progress)' : 'Scenario D (>= 40% Route Progress)');

    resultSection = `
      <div class="mt-4 p-5 rounded-2xl border ${isApproved ? 'bg-emerald-50/70 border-emerald-300' : 'bg-amber-50/70 border-amber-300'} shadow-sm space-y-4">
        
        <!-- Header -->
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b ${isApproved ? 'border-emerald-200' : 'border-amber-200'}">
          <div class="flex items-center space-x-2.5">
            <span class="px-3 py-1 rounded-lg text-xs font-black uppercase tracking-wider ${isApproved ? 'bg-emerald-600 text-white shadow-sm' : 'bg-amber-600 text-white shadow-sm'}">
              ${isApproved ? 'APPROVED: REASSIGNMENT EXECUTED' : 'REJECTED: RESERVATION RETAINED'}
            </span>
            <span class="text-xs font-bold text-slate-800">${scenarioTitle}</span>
          </div>
          <div class="flex items-center space-x-2 text-xs font-medium text-slate-600">
            <span class="inline-flex items-center px-2 py-0.5 rounded bg-white/80 border border-slate-200 text-[11px]">
              Threshold: <strong class="ml-1 text-slate-800">${threshold}%</strong>
            </span>
            <span class="inline-flex items-center px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-200 text-[11px] font-bold">
              ✓ Persisted in Audit Ledger
            </span>
          </div>
        </div>

        <!-- Route Progress Visual Gauge -->
        <div class="bg-white/90 p-4 rounded-xl border border-slate-200/80 shadow-xs space-y-2">
          <div class="flex items-center justify-between text-xs">
            <span class="font-bold text-slate-700">Simulated Route Progress vs Non-Disruption Threshold</span>
            <span class="font-mono font-bold ${isUnderThreshold ? 'text-emerald-700' : 'text-amber-700'}">
              ${progress.toFixed(1)}% / 100% (${isUnderThreshold ? '< 40% - Permitted' : '>= 40% - Protected'})
            </span>
          </div>
          <div class="relative w-full h-4 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
            <!-- 40% Threshold Marker -->
            <div class="absolute top-0 bottom-0 left-[40%] w-0.5 bg-rose-500 z-10" title="40% Non-Disruption Policy Threshold"></div>
            <!-- Progress Fill -->
            <div class="h-full transition-all duration-500 ${isUnderThreshold ? 'bg-emerald-500' : 'bg-amber-500'}" style="width: ${Math.min(progress, 100)}%;"></div>
          </div>
          <div class="flex justify-between text-[10px] text-slate-400 font-medium">
            <span>0% (Intake)</span>
            <span class="text-rose-600 font-bold">| 40% Threshold Lock</span>
            <span>100% (Hospital Arrival)</span>
          </div>
        </div>

        <!-- 4-State Impact Summary Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          
          <!-- Box 1: Bed Allocation -->
          <div class="p-3 bg-white/90 rounded-xl border border-slate-200/80">
            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Target Bed Status</span>
            ${isApproved && lastReassignmentResult.displacingReservation ? `
              <div class="mt-1 font-bold text-slate-900">${lastReassignmentResult.displacingReservation.bedNumber || 'ICU Bed'}</div>
              <div class="text-[11px] text-emerald-700 font-semibold">Allocated to P1 Displacing Emergency</div>
              <span class="inline-block mt-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">STATUS: RESERVED</span>
            ` : `
              <div class="mt-1 font-bold text-slate-900">Retained by Inbound Patient</div>
              <div class="text-[11px] text-slate-600 font-medium">Contention denied due to &ge;40% route progress</div>
              <span class="inline-block mt-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">STATUS: RESERVED</span>
            `}
          </div>

          <!-- Box 2: Displaced Patient State -->
          <div class="p-3 bg-white/90 rounded-xl border border-slate-200/80">
            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Inbound Patient Candidate</span>
            <div class="mt-1 font-mono font-bold text-slate-800 text-[11px] truncate" title="${lastReassignmentResult.displacedEmergencyId || 'Inbound Patient'}">
              ${lastReassignmentResult.displacedEmergencyId || 'Inbound P3 Patient'}
            </div>
            ${isApproved ? `
              <div class="text-[11px] text-rose-700 font-semibold">Reservation Displaced</div>
              <span class="inline-block mt-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800">RELEASED_FOR_REASSIGNMENT</span>
            ` : `
              <div class="text-[11px] text-emerald-700 font-semibold">Protected by Non-Disruption Policy</div>
              <span class="inline-block mt-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">RESERVATION RETAINED</span>
            `}
          </div>

          <!-- Box 3: Subsystem Reroute Coordination -->
          <div class="p-3 bg-white/90 rounded-xl border border-slate-200/80">
            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Ambulance Coordination (Nidhi)</span>
            ${lastReassignmentResult.rerouteRequired ? `
              <div class="mt-1 font-bold text-rose-700 flex items-center">
                <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                REROUTE REQUIRED
              </div>
              <div class="text-[11px] text-slate-700 mt-0.5">
                Next: <strong>${lastReassignmentResult.nextBestHospital?.name || 'Apollo Hospitals Bannerghatta'}</strong>
              </div>
            ` : `
              <div class="mt-1 font-bold text-slate-800">NO REROUTE REQUIRED</div>
              <div class="text-[11px] text-slate-500 mt-0.5">Ambulance continues toward reserved hospital</div>
            `}
          </div>

          <!-- Box 4: Audit & Ledger Integrity -->
          <div class="p-3 bg-white/90 rounded-xl border border-slate-200/80">
            <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Audit Ledger State</span>
            <div class="mt-1 font-bold text-emerald-700 flex items-center">
              <svg class="w-3.5 h-3.5 mr-1 text-emerald-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
              Persistent DB Entry
            </div>
            <div class="text-[11px] text-slate-500 mt-0.5">
              Available across refreshes &amp; API queries
            </div>
          </div>

        </div>

        <!-- Rationale Text -->
        <div class="p-3 rounded-xl bg-white/90 border border-slate-200/80 text-xs text-slate-700 leading-relaxed">
          <strong class="text-slate-900">Policy Rationale:</strong> ${lastReassignmentResult.reason}
        </div>

        <!-- Machine-Readable Rerouting Event Contract (Scenario C) -->
        ${lastReassignmentResult.rerouteEvent ? `
          <div class="rounded-xl border border-slate-300 bg-slate-900 p-4 text-xs font-mono">
            <div class="flex items-center justify-between text-slate-300 mb-2 pb-1 border-b border-slate-800">
              <div class="flex items-center space-x-2">
                <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                <span class="font-bold text-white text-[11px] uppercase tracking-wider">Subsystem Reroute Event Contract (For Nidhi's Ambulance Module)</span>
              </div>
              <span class="text-[10px] text-slate-400">EVENT_BED_REASSIGNMENT_REROUTE</span>
            </div>
            <pre class="text-emerald-400 overflow-x-auto text-[11px] leading-relaxed">${JSON.stringify(lastReassignmentResult.rerouteEvent, null, 2)}</pre>
          </div>
        ` : ''}

      </div>
    `;
  }

  container.innerHTML = `
    <div class="space-y-6">

      <!-- Mandatory Prototype Policy Disclaimer Banner -->
      <div class="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900">
        <div class="flex items-start space-x-3">
          <div class="w-8 h-8 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center shrink-0">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <h4 class="text-xs font-bold uppercase tracking-wider text-amber-800">40% Route-Progress Prototype Bed Reassignment Policy</h4>
            <p class="text-xs text-amber-700 mt-1 leading-relaxed">
              <strong>Notice:</strong> This policy is a configurable demonstration rule designed to illustrate dynamic resource re-allocation across autonomous subsystems.
              It is <strong>NOT</strong> a clinical, medical, legal, or scientifically validated protocol.
            </p>
          </div>
        </div>
      </div>

      <!-- 1-Click Interactive Demo Triggers -->
      <div class="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div>
            <h3 class="text-sm font-bold text-slate-900 tracking-tight">Evaluator Scenario Demonstrator</h3>
            <p class="text-xs text-slate-500">Test live backend reassignment evaluation against active database reservations</p>
          </div>
          <div class="flex items-center space-x-2">
            <button id="btn-scenario-c" class="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-sm transition-all flex items-center ${isEvaluating ? 'opacity-50 pointer-events-none' : ''}">
              <svg class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
              Trigger Scenario C (Route: 25% &lt; 40%)
            </button>
            <button id="btn-scenario-d" class="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs shadow-sm transition-all flex items-center ${isEvaluating ? 'opacity-50 pointer-events-none' : ''}">
              <svg class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/></svg>
              Trigger Scenario D (Route: 65% &ge; 40%)
            </button>
          </div>
        </div>

        <!-- Last Evaluation Result Card -->
        ${resultSection}
      </div>

      <!-- Audit History Table -->
      <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div class="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 class="text-sm font-bold text-slate-900 tracking-tight">Reassignment Policy Audit Trail</h3>
            <p class="text-xs text-slate-500">Persistent database ledger of all priority bed contention evaluations and reroute decisions</p>
          </div>
          <span class="px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 font-bold text-xs">
            ${(auditLogs || []).length} Logged Evaluations
          </span>
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200 text-left">
            <thead class="bg-slate-50/80 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
              <tr>
                <th scope="col" class="px-4 py-3">Event ID</th>
                <th scope="col" class="px-4 py-3">Decision</th>
                <th scope="col" class="px-4 py-3">Route Progress</th>
                <th scope="col" class="px-4 py-3">Displacing Case</th>
                <th scope="col" class="px-4 py-3">Displaced Candidate</th>
                <th scope="col" class="px-4 py-3">Reroute / Action</th>
                <th scope="col" class="px-4 py-3">Timestamp</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 bg-white">
              ${auditRows || '<tr><td colspan="7" class="p-8 text-center text-slate-400 text-xs">No audit logs recorded yet.</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `;

  // Bind scenario trigger buttons
  const btnC = container.querySelector('#btn-scenario-c');
  if (btnC) {
    btnC.addEventListener('click', () => onTriggerScenario(25.0));
  }

  const btnD = container.querySelector('#btn-scenario-d');
  if (btnD) {
    btnD.addEventListener('click', () => onTriggerScenario(65.0));
  }
}
