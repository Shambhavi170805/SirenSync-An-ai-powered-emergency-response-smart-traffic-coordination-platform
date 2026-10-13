/**
 * AssignmentCard Component
 * Displays the current assignment, destination hospital details,
 * next required driver action, route progress bar, or a graceful unassigned standby state.
 */

import { escapeHtml, formatCoordinate } from '../utils.js';

export function renderAssignmentCard(state) {
  const ambulance = state.selectedAmbulance;
  if (!ambulance) {
    return `
      <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-8 text-center text-slate-500">
        <p>No ambulance selected.</p>
      </div>
    `;
  }

  const isAssigned = Boolean(ambulance.assignedEmergencyId);
  const hospital = state.destinationHospital;

  if (!isAssigned) {
    const standbyLat = formatCoordinate(ambulance.currentLocation?.latitude, null);
    const standbyLng = formatCoordinate(ambulance.currentLocation?.longitude, null);
    const standbyCoords = (standbyLat !== null && standbyLng !== null)
      ? `${standbyLat}, ${standbyLng}`
      : 'Coordinates unavailable';

    const isAvailable = ambulance.status === 'AVAILABLE';
    const isMaintenance = ambulance.status === 'MAINTENANCE';

    let headerStatusText = `Vehicle Status: ${ambulance.status.replace(/_/g, ' ')}`;
    let badgeText = ambulance.status.replace(/_/g, ' ');
    let badgeClass = 'bg-slate-100 text-slate-800';
    let iconBoxClass = 'bg-slate-100 text-slate-600';
    let iconSvg = `
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    `;
    let subTitle = 'No Active Emergency Assignment';
    let bodyDescription = `This ambulance currently has status ${ambulance.status.replace(/_/g, ' ')}. It is not assigned to an active emergency.`;

    if (isAvailable) {
      headerStatusText = 'Vehicle Status: Ready on Standby';
      badgeText = 'AVAILABLE FOR DISPATCH';
      badgeClass = 'bg-emerald-100 text-emerald-800';
      iconBoxClass = 'bg-emerald-50 text-emerald-600';
      iconSvg = `
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      `;
      subTitle = 'No Active Emergency Assignment';
      bodyDescription = 'This ambulance is currently in available fleet reserve. When a patient emergency is matched and a hospital bed is locked, the backend dispatch coordinator automatically assigns the vehicle.';
    } else if (isMaintenance) {
      headerStatusText = 'Vehicle Status: Maintenance Offline';
      badgeText = 'MAINTENANCE';
      badgeClass = 'bg-rose-100 text-rose-800 border border-rose-200';
      iconBoxClass = 'bg-rose-50 text-rose-600';
      iconSvg = `
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      `;
      subTitle = 'Vehicle In Maintenance Mode';
      bodyDescription = 'This ambulance is currently offline for maintenance or mechanical servicing. It cannot be dispatched to emergencies until its operational status is restored to Available.';
    }

    return `
      <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 md:p-8">
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          <div class="flex items-center space-x-3">
            <div class="h-12 w-12 rounded-xl ${iconBoxClass} flex items-center justify-center font-bold">
              ${iconSvg}
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900">${escapeHtml(headerStatusText)}</h2>
              <p class="text-xs text-slate-500 font-mono">Vehicle ID: ${escapeHtml(ambulance.id)} • ${escapeHtml(ambulance.vehicleNumber)}</p>
            </div>
          </div>
          <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${badgeClass}">
            ${escapeHtml(badgeText)}
          </span>
        </div>

        <div class="py-8 text-center max-w-md mx-auto">
          <div class="mx-auto w-16 h-16 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mb-3">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 class="text-sm font-bold text-slate-800 mb-1">${escapeHtml(subTitle)}</h3>
          <p class="text-xs text-slate-500 leading-relaxed mb-4">
            ${escapeHtml(bodyDescription)}
          </p>
          <div class="inline-flex items-center space-x-2 text-[11px] text-slate-400 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
            <span>Standby Coordinates:</span>
            <span class="font-mono text-slate-600">${escapeHtml(standbyCoords)}</span>
          </div>
        </div>

        <!-- Equipment list -->
        <div class="pt-4 border-t border-slate-100">
          <span class="text-xs font-semibold text-slate-700 block mb-2">Onboard Life-Support Equipment:</span>
          <div class="flex flex-wrap gap-1.5">
            ${(ambulance.equipmentTags || []).length > 0
              ? ambulance.equipmentTags.map(tag => `
                <span class="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-[11px] font-medium border border-slate-200">
                  ${escapeHtml(tag)}
                </span>
              `).join('')
              : '<span class="text-xs text-slate-400">Standard Emergency Equipment</span>'
            }
          </div>
        </div>
      </div>
    `;
  }

  // Next action guidance based on lifecycle state
  const nextActions = {
    ASSIGNED: {
      action: 'Depart for Patient Pickup',
      guidance: 'Dispatch confirmed. Proceed immediately to patient origin location.',
      badge: 'bg-amber-100 text-amber-800 border-amber-300',
    },
    EN_ROUTE_PICKUP: {
      action: 'Approach & Transfer Patient',
      guidance: 'Navigating to patient coordinates. Once patient is secured onboard, transition status to Patient Onboard.',
      badge: 'bg-blue-100 text-blue-800 border-blue-300',
    },
    PATIENT_ONBOARD: {
      action: 'Transit to Coordinating Hospital',
      guidance: 'Patient is secured in vehicle. Transport toward destination emergency department.',
      badge: 'bg-purple-100 text-purple-800 border-purple-300',
    },
    EN_ROUTE_HOSPITAL: {
      action: 'Transit to Hospital Emergency Bay',
      guidance: 'Navigating to destination hospital. Maintain route progress streaming.',
      badge: 'bg-indigo-100 text-indigo-800 border-indigo-300',
    },
    ARRIVED: {
      action: 'Patient Handover & Mission Debrief',
      guidance: 'Ambulance has reached the emergency bay. Complete handover to hospital clinical team and transition back to Available.',
      badge: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    },
    MAINTENANCE: {
      action: 'Vehicle Servicing / Sterilization',
      guidance: 'Vehicle is marked for maintenance/sterilization. Clear vehicle to Available when service concludes.',
      badge: 'bg-rose-100 text-rose-800 border-rose-300',
    },
  };

  const actionInfo = nextActions[ambulance.status] || {
    action: 'Follow Operational Protocol',
    guidance: 'Proceed according to dispatch coordinator instructions.',
    badge: 'bg-slate-100 text-slate-800 border-slate-300',
  };

  const progress = Math.min(Math.max(Number.isFinite(ambulance.routeProgress) ? ambulance.routeProgress : 0.0, 0.0), 100.0);
  const activeLat = formatCoordinate(ambulance.currentLocation?.latitude, null);
  const activeLng = formatCoordinate(ambulance.currentLocation?.longitude, null);
  const activeCoords = (activeLat !== null && activeLng !== null)
    ? `${activeLat}, ${activeLng}`
    : 'Coordinates unavailable';

  return `
    <div class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">

      <!-- Assignment Header Bar -->
      <div class="bg-gradient-to-r from-slate-900 to-slate-800 text-white p-5 sm:p-6">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div class="flex items-center space-x-2 mb-1">
              <span class="h-2.5 w-2.5 rounded-full bg-rose-500 animate-ping"></span>
              <span class="text-xs font-bold uppercase tracking-wider text-rose-400">ACTIVE EMERGENCY DISPATCH</span>
              <span class="text-xs text-slate-400 font-mono">(${escapeHtml(ambulance.assignedEmergencyId)})</span>
            </div>
            <h2 class="text-lg sm:text-xl font-bold text-white tracking-tight">
              ${escapeHtml(hospital?.name || ambulance.destinationHospitalId || 'Assigned Coordinating Hospital')}
            </h2>
            <p class="text-xs text-slate-300 mt-0.5">
              ${escapeHtml(hospital?.address || 'Destination Hospital Facility')}
            </p>
          </div>

          <div class="flex flex-col sm:items-end">
            <span class="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Hospital Contact</span>
            <span class="text-sm font-bold text-rose-400 font-mono">
              ${escapeHtml(hospital?.contactNumber || '+91-80-EMERGENCY')}
            </span>
          </div>
        </div>
      </div>

      <!-- Action Guidance Card -->
      <div class="p-5 sm:p-6 space-y-6">

        <div class="bg-slate-50 rounded-xl p-4 border border-slate-200/80">
          <div class="flex items-start justify-between gap-2 mb-2">
            <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Next Required Action:</span>
            <span class="px-2.5 py-0.5 rounded-full text-xs font-bold border ${actionInfo.badge}">
              ${escapeHtml(actionInfo.action)}
            </span>
          </div>
          <p class="text-sm font-medium text-slate-800">
            ${escapeHtml(actionInfo.guidance)}
          </p>
        </div>

        <!-- Authoritative Route Progress Tracker -->
        <div class="space-y-2">
          <div class="flex items-center justify-between text-xs">
            <div class="flex items-center space-x-2">
              <span class="font-bold text-slate-700">Journey Route Progress:</span>
              <span class="font-bold text-rose-600 text-sm font-mono">${progress.toFixed(1)}%</span>
            </div>
            <span class="text-[11px] text-slate-400">
              ${progress < 40.0
                ? '<span class="text-amber-600 font-medium">Progress &lt; 40% (Reassignment Window Open)</span>'
                : '<span class="text-emerald-600 font-medium">Progress &ge; 40% (Journey Stabilized)</span>'}
            </span>
          </div>

          <!-- Progress Bar Track -->
          <div class="w-full bg-slate-100 rounded-full h-3.5 overflow-hidden border border-slate-200 p-0.5">
            <div
              class="h-full rounded-full transition-all duration-500 bg-gradient-to-r from-rose-500 via-amber-500 to-emerald-500"
              style="width: ${progress}%"
            ></div>
          </div>

          <div class="flex justify-between text-[11px] text-slate-400 font-medium pt-0.5">
            <span>0% (Origin/Dispatch)</span>
            <span class="text-amber-600">40% Prototype Threshold</span>
            <span>100% (Hospital Bay)</span>
          </div>
        </div>

        <!-- Details Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 text-xs border-t border-slate-100">
          <div>
            <span class="text-slate-400 block mb-0.5">Emergency ID</span>
            <span class="font-mono font-bold text-slate-800 select-all">${escapeHtml(ambulance.assignedEmergencyId)}</span>
          </div>
          <div>
            <span class="text-slate-400 block mb-0.5">Destination Hospital ID</span>
            <span class="font-mono font-bold text-slate-800">${escapeHtml(ambulance.destinationHospitalId || 'None')}</span>
          </div>
          <div>
            <span class="text-slate-400 block mb-0.5">Last Authoritative Telemetry</span>
            <span class="font-mono text-slate-700">
              ${escapeHtml(activeCoords)}
            </span>
            <span class="text-slate-500 text-[11px] block truncate" title="${escapeHtml(ambulance.currentLocation?.address || '')}">
              ${escapeHtml(ambulance.currentLocation?.address || 'Simulated Bengaluru Transit Corridor')}
            </span>
          </div>
          <div>
            <span class="text-slate-400 block mb-0.5">State Synchronization Version</span>
            <span class="font-mono text-slate-700">v${escapeHtml(ambulance.version)} (Updated: ${escapeHtml(new Date(ambulance.updatedAt).toLocaleTimeString())})</span>
          </div>
        </div>

      </div>

    </div>
  `;
}
