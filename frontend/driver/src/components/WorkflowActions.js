/**
 * WorkflowActions Component
 * Provides driver operational lifecycle transition controls adhering
 * strictly to backend VALID_STATUS_TRANSITIONS state machine rules.
 */

import { escapeHtml } from '../utils.js';

// Mirrors backend VALID_STATUS_TRANSITIONS in backend/services/ambulance_service.py
const VALID_TRANSITIONS = {
  AVAILABLE: ['ASSIGNED', 'MAINTENANCE'],
  ASSIGNED: ['EN_ROUTE_PICKUP', 'AVAILABLE', 'MAINTENANCE'],
  EN_ROUTE_PICKUP: ['PATIENT_ONBOARD', 'AVAILABLE', 'MAINTENANCE'],
  PATIENT_ONBOARD: ['EN_ROUTE_HOSPITAL', 'ARRIVED', 'MAINTENANCE'],
  EN_ROUTE_HOSPITAL: ['ARRIVED', 'MAINTENANCE'],
  ARRIVED: ['AVAILABLE', 'MAINTENANCE'],
  MAINTENANCE: ['AVAILABLE'],
};

const STATUS_LABELS = {
  AVAILABLE: 'Mark Available',
  ASSIGNED: 'Confirm Assigned',
  EN_ROUTE_PICKUP: 'Depart to Pickup',
  PATIENT_ONBOARD: 'Patient Onboard',
  EN_ROUTE_HOSPITAL: 'En Route to Hospital',
  ARRIVED: 'Mark Arrived at Hospital',
  MAINTENANCE: 'Enter Maintenance',
};

const STEP_ORDER = [
  'ASSIGNED',
  'EN_ROUTE_PICKUP',
  'PATIENT_ONBOARD',
  'EN_ROUTE_HOSPITAL',
  'ARRIVED',
  'AVAILABLE',
];

export function renderWorkflowActions(state) {
  const ambulance = state.selectedAmbulance;
  if (!ambulance) return '';

  const currentStatus = ambulance.status;
  const allowedTransitions = VALID_TRANSITIONS[currentStatus] || [];
  const currentIndex = STEP_ORDER.indexOf(currentStatus);

  return `
    <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5 sm:p-6 space-y-5">

      <!-- Component Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-slate-100">
        <div>
          <h3 class="text-sm font-bold text-slate-900">Driver Operational Workflow</h3>
          <p class="text-xs text-slate-500">Validated status transition state machine controls</p>
        </div>
        <div class="text-xs text-slate-400 font-medium">
          Current State: <strong class="text-slate-800">${escapeHtml(currentStatus.replace(/_/g, ' '))}</strong>
        </div>
      </div>

      <!-- Lifecycle Stepper Visualizer -->
      <div class="overflow-x-auto pb-2 scrollbar-none">
        <div class="flex items-center min-w-[550px] justify-between text-center">
          ${STEP_ORDER.map((step, idx) => {
            const isCompleted = currentIndex > idx && currentStatus !== 'AVAILABLE';
            const isCurrent = currentStatus === step;
            let circleClass = 'bg-slate-100 text-slate-400 border-slate-200';
            let labelClass = 'text-slate-400 font-medium';

            if (isCurrent) {
              circleClass = 'bg-rose-600 text-white border-rose-600 ring-4 ring-rose-100';
              labelClass = 'text-rose-600 font-bold';
            } else if (isCompleted) {
              circleClass = 'bg-emerald-500 text-white border-emerald-500';
              labelClass = 'text-emerald-700 font-medium';
            }

            return `
              <div class="flex-1 flex flex-col items-center relative">
                <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border ${circleClass} z-10 transition">
                  ${isCompleted ? '✓' : idx + 1}
                </div>
                <span class="text-[10px] mt-1.5 leading-tight ${labelClass} max-w-[80px]">
                  ${escapeHtml(step.replace(/_/g, ' '))}
                </span>
                ${idx < STEP_ORDER.length - 1 ? `
                  <div class="absolute top-4 left-1/2 w-full h-0.5 ${currentIndex > idx ? 'bg-emerald-400' : 'bg-slate-200'} -z-0"></div>
                ` : ''}
              </div>
            `;
          }).join('')}
        </div>
      </div>

      <!-- Action Buttons Grid -->
      <div class="space-y-3 pt-2">
        <div class="text-xs font-semibold text-slate-700">Permitted Status Actions:</div>
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
          ${allowedTransitions.map(targetStatus => {
            const isPrimary = (
              (currentStatus === 'ASSIGNED' && targetStatus === 'EN_ROUTE_PICKUP') ||
              (currentStatus === 'EN_ROUTE_PICKUP' && targetStatus === 'PATIENT_ONBOARD') ||
              (currentStatus === 'PATIENT_ONBOARD' && targetStatus === 'EN_ROUTE_HOSPITAL') ||
              (currentStatus === 'EN_ROUTE_HOSPITAL' && targetStatus === 'ARRIVED') ||
              (currentStatus === 'ARRIVED' && targetStatus === 'AVAILABLE') ||
              (currentStatus === 'AVAILABLE' && targetStatus === 'ASSIGNED')
            );

            const btnStyle = isPrimary
              ? 'bg-rose-600 hover:bg-rose-700 text-white font-bold shadow-sm shadow-rose-600/30 ring-1 ring-rose-600'
              : (targetStatus === 'MAINTENANCE'
                ? 'bg-slate-100 hover:bg-rose-50 text-slate-700 hover:text-rose-700 border border-slate-200'
                : 'bg-slate-800 hover:bg-slate-900 text-white border border-slate-700 font-semibold');

            return `
              <button
                class="btn-status-transition px-3.5 py-2.5 rounded-lg text-xs transition flex items-center justify-between cursor-pointer ${btnStyle}"
                data-status="${escapeHtml(targetStatus)}"
                ${state.isSubmittingStatus ? 'disabled' : ''}
              >
                <span>${escapeHtml(STATUS_LABELS[targetStatus] || targetStatus)}</span>
                <span class="text-[10px] opacity-75 font-mono ml-1.5">&rarr;</span>
              </button>
            `;
          }).join('')}
        </div>
      </div>

      <!-- Optional Transition Notes -->
      <div class="pt-2">
        <label for="status-notes-input" class="block text-[11px] font-medium text-slate-500 mb-1">
          Optional Status Transition Note (synced to Hospital Queue Item):
        </label>
        <input
          type="text"
          id="status-notes-input"
          class="w-full text-xs px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-rose-500 text-slate-800 placeholder-slate-400"
          placeholder="e.g. Patient transfer complete, vitals stable en route to hospital"
          value="${escapeHtml(state.statusNotes || '')}"
        />
      </div>

    </div>
  `;
}
