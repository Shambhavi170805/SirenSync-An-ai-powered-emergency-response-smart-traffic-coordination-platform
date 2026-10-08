export const AVAILABLE_CAPABILITIES = [
  { id: 'CARDIAC_CATH_LAB', label: 'Cardiac Cath Lab' },
  { id: 'ICU_VENTILATOR', label: 'ICU Ventilator' },
  { id: 'TRAUMA_LEVEL_1', label: 'Trauma Center' },
  { id: 'PEDIATRIC_EMERGENCY', label: 'Pediatric ICU' },
];

export function renderRankingDemo(container, { rankingForm, onRank, onFormChange, rankingResults, isRanking }) {
  const presets = [
    {
      label: 'Cardiac Arrest (MG Road - P1)',
      payload: {
        emergencyId: 'demo-cardiac-01',
        patientLocation: { latitude: 12.9716, longitude: 77.5946, address: 'MG Road Metro Station' },
        emergencyType: 'CARDIAC_ARREST',
        priority: 'P1_CRITICAL',
        requiredBedType: 'ICU',
        requiredCapabilities: ['CARDIAC_CATH_LAB', 'ICU_VENTILATOR']
      }
    },
    {
      label: 'Highway Trauma (Hebbal - P1)',
      payload: {
        emergencyId: 'demo-trauma-02',
        patientLocation: { latitude: 13.0354, longitude: 77.5898, address: 'Hebbal Flyover Junction' },
        emergencyType: 'SEVERE_POLYTRAUMA',
        priority: 'P1_CRITICAL',
        requiredBedType: 'TRAUMA_EMERGENCY',
        requiredCapabilities: ['TRAUMA_LEVEL_1', 'ICU_VENTILATOR']
      }
    },
    {
      label: 'Pediatric Distress (Bannerghatta - P1)',
      payload: {
        emergencyId: 'demo-pediatric-03',
        patientLocation: { latitude: 12.8942, longitude: 77.5990, address: 'Bannerghatta Road' },
        emergencyType: 'PEDIATRIC_RESPIRATORY_DISTRESS',
        priority: 'P1_CRITICAL',
        requiredBedType: 'PEDIATRIC_ICU',
        requiredCapabilities: ['PEDIATRIC_EMERGENCY', 'ICU_VENTILATOR']
      }
    }
  ];

  const currentForm = rankingForm || {
    latitude: 12.9716,
    longitude: 77.5946,
    priority: 'P1_CRITICAL',
    requiredBedType: 'ICU',
    requiredCapabilities: ['CARDIAC_CATH_LAB', 'ICU_VENTILATOR']
  };

  const selectedCaps = Array.isArray(currentForm.requiredCapabilities)
    ? currentForm.requiredCapabilities
    : [];

  const capabilityCheckboxesHtml = AVAILABLE_CAPABILITIES.map(cap => {
    const isChecked = selectedCaps.includes(cap.id);
    return `
      <label class="inline-flex items-center space-x-1.5 cursor-pointer bg-slate-50 hover:bg-slate-100 px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs transition-colors">
        <input type="checkbox" class="rank-cap rounded text-indigo-600 focus:ring-indigo-500" value="${cap.id}" ${isChecked ? 'checked' : ''} />
        <span class="font-medium text-slate-800">${cap.label}</span>
      </label>
    `;
  }).join('');

  let resultsHtml = '';
  if (isRanking) {
    resultsHtml = `
      <div class="bg-white p-12 text-center rounded-2xl border border-slate-200">
        <div class="w-10 h-10 border-4 border-rose-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
        <p class="text-xs font-semibold text-slate-700">Evaluating 4-Factor Deterministic Ranking...</p>
        <p class="text-[11px] text-slate-400">Computing Haversine distance, capability match, traffic factor, and live bed inventory...</p>
      </div>
    `;
  } else if (rankingResults) {
    const cards = (rankingResults.rankedHospitals || []).map(h => {
      const b = h.breakdown;
      const compPct = Math.round(h.compositeScore * 100);

      const matchedBadges = (b.matchedCapabilities || []).map(c => 
        `<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">✓ ${c}</span>`
      ).join(' ');

      const missingBadges = (b.missingCapabilities || []).map(c => 
        `<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">✗ ${c}</span>`
      ).join(' ');

      let eligBadge = '<span class="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">ELIGIBLE</span>';
      let cardBorder = 'border-slate-200 hover:border-indigo-300';
      if (!h.isEligible) {
        eligBadge = '<span class="px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800">INELIGIBLE</span>';
        cardBorder = 'border-rose-200 bg-rose-50/10 opacity-75';
      } else if (h.rank === 1) {
        eligBadge = '<span class="px-2.5 py-1 rounded-full text-xs font-bold bg-rose-600 text-white shadow-sm">#1 TOP RECOMMENDATION</span>';
        cardBorder = 'border-rose-400 bg-rose-50/20 shadow-md';
      }

      return `
        <div class="bg-white p-5 rounded-2xl border ${cardBorder} transition-all space-y-3">
          <div class="flex items-start justify-between">
            <div>
              <div class="flex items-center space-x-2">
                <span class="w-6 h-6 rounded-lg bg-slate-900 text-white inline-flex items-center justify-center font-bold text-xs">
                  #${h.rank}
                </span>
                <h4 class="text-sm font-bold text-slate-900">${h.name}</h4>
              </div>
              <p class="text-xs text-slate-500 mt-1">${h.location.address} • ${b.distanceKm} km</p>
            </div>
            ${eligBadge}
          </div>

          <!-- Composite Score Gauge -->
          <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
            <div class="flex items-center justify-between text-xs mb-1">
              <span class="font-bold text-slate-700 uppercase tracking-wider text-[11px]">Composite Match Score</span>
              <span class="font-extrabold text-slate-900 text-sm">${h.compositeScore.toFixed(3)} <span class="text-xs font-normal text-slate-400">/ 1.000</span></span>
            </div>
            <div class="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
              <div class="bg-gradient-to-r from-rose-500 to-indigo-600 h-2" style="width: ${compPct}%"></div>
            </div>
          </div>

          <!-- Factor Breakdown Grid -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            <div class="p-2 bg-slate-50 rounded-lg">
              <span class="text-slate-400 block text-[10px] font-bold">1. DISTANCE (w=0.30)</span>
              <span class="font-bold text-slate-900">${b.distanceKm} km</span>
              <span class="text-[10px] text-slate-500 block">score: ${b.distanceScore.toFixed(2)}</span>
            </div>
            <div class="p-2 bg-slate-50 rounded-lg">
              <span class="text-slate-400 block text-[10px] font-bold">2. CAPABILITY (w=0.35)</span>
              <span class="font-bold text-indigo-700">${Math.round(b.capabilityMatchScore * 100)}% Match</span>
              <span class="text-[10px] text-slate-500 block">score: ${b.capabilityMatchScore.toFixed(2)}</span>
            </div>
            <div class="p-2 bg-slate-50 rounded-lg">
              <span class="text-slate-400 block text-[10px] font-bold">3. TRAFFIC (w=0.20)</span>
              <span class="font-bold text-amber-700">${b.trafficCongestionFactor}x Delay</span>
              <span class="text-[10px] text-slate-500 block">score: ${b.trafficScore.toFixed(2)}</span>
            </div>
            <div class="p-2 bg-slate-50 rounded-lg">
              <span class="text-slate-400 block text-[10px] font-bold">4. BEDS (w=0.15)</span>
              <span class="font-bold text-emerald-700">${b.availableBedsCount} Available</span>
              <span class="text-[10px] text-slate-500 block">score: ${b.bedAvailabilityScore.toFixed(2)}</span>
            </div>
          </div>

          <!-- Capabilities Tags -->
          <div class="text-xs pt-1 flex items-center flex-wrap gap-1">
            ${matchedBadges}
            ${missingBadges}
          </div>

          <!-- Explainable Narrative -->
          <div class="p-3 bg-slate-50/80 rounded-xl border border-slate-100 text-[11px] text-slate-600 leading-relaxed">
            <span class="font-bold text-slate-700">Algorithm Explanation:</span> ${b.explanation}
          </div>
        </div>
      `;
    }).join('');

    const evaluatedCaps = rankingResults.requiredCapabilities || [];
    const evaluatedCapsBadges = evaluatedCaps.length > 0
      ? evaluatedCaps.map(c => `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-100 text-indigo-800 border border-indigo-200 font-mono">${c}</span>`).join(' ')
      : '<span class="text-[11px] italic text-indigo-500 font-medium">None requested (General baseline matching — 100% baseline capability score)</span>';

    resultsHtml = `
      <div class="space-y-4">
        <div class="bg-indigo-50/50 p-4 rounded-2xl border border-indigo-100 text-xs text-indigo-900 space-y-2">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
            <span>Evaluated <strong>${rankingResults.totalHospitalsEvaluated}</strong> candidate facilities • <strong>${rankingResults.eligibleHospitalsCount}</strong> deemed clinically eligible</span>
            <span class="font-mono text-[11px] text-indigo-700">Weights: Dist=0.30 • Cap=0.35 • Traffic=0.20 • Bed=0.15</span>
          </div>
          <div class="pt-2 border-t border-indigo-200/50 flex items-center space-x-2 flex-wrap gap-y-1">
            <span class="font-bold text-[11px] uppercase tracking-wider text-indigo-800 shrink-0">Evaluated Target Capabilities:</span>
            <div class="flex items-center space-x-1.5 flex-wrap gap-y-1">
              ${evaluatedCapsBadges}
            </div>
          </div>
        </div>
        <div class="space-y-3">
          ${cards}
        </div>
      </div>
    `;
  }

  container.innerHTML = `
    <div class="space-y-6">
      
      <!-- Ranking Header -->
      <div class="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
        <h3 class="text-sm font-bold text-slate-900 tracking-tight">4-Factor Deterministic Hospital Ranking Demonstration</h3>
        <p class="text-xs text-slate-500 mt-0.5">
          Simulates the decision engine consumed by Shambhavi's intake module. Ranks hospitals by Proximity, Specialization Match, Traffic Delays, and Live Bed Buffers.
        </p>
        
        <!-- Preset Scenario Buttons -->
        <div class="mt-4 pt-3 border-t border-slate-100">
          <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">Evaluator Presets</span>
          <div class="flex items-center space-x-2 flex-wrap gap-y-2">
            ${presets.map((p, i) => `
              <button class="btn-preset px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-xs font-semibold text-slate-700 transition-colors" data-preset="${i}">
                ${p.label}
              </button>
            `).join('')}
          </div>
        </div>

        <!-- Custom Query Form -->
        <form id="ranking-form" class="mt-4 pt-4 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          <div>
            <label class="font-bold text-slate-700 block mb-1">Patient Latitude</label>
            <input type="number" step="0.0001" id="rank-lat" value="${currentForm.latitude}" class="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-xs" required />
          </div>
          <div>
            <label class="font-bold text-slate-700 block mb-1">Patient Longitude</label>
            <input type="number" step="0.0001" id="rank-lng" value="${currentForm.longitude}" class="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-xs" required />
          </div>
          <div>
            <label class="font-bold text-slate-700 block mb-1">Triage Priority</label>
            <select id="rank-priority" class="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-xs">
              <option value="P1_CRITICAL" ${currentForm.priority === 'P1_CRITICAL' ? 'selected' : ''}>P1 CRITICAL (Resuscitation)</option>
              <option value="P2_EMERGENCY" ${currentForm.priority === 'P2_EMERGENCY' ? 'selected' : ''}>P2 EMERGENCY (Severe)</option>
              <option value="P3_URGENT" ${currentForm.priority === 'P3_URGENT' ? 'selected' : ''}>P3 URGENT</option>
              <option value="P4_NON_URGENT" ${currentForm.priority === 'P4_NON_URGENT' ? 'selected' : ''}>P4 NON-URGENT</option>
            </select>
          </div>
          <div>
            <label class="font-bold text-slate-700 block mb-1">Required Bed Type</label>
            <select id="rank-bed-type" class="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-xs">
              <option value="ICU" ${currentForm.requiredBedType === 'ICU' ? 'selected' : ''}>ICU</option>
              <option value="TRAUMA_EMERGENCY" ${currentForm.requiredBedType === 'TRAUMA_EMERGENCY' ? 'selected' : ''}>TRAUMA_EMERGENCY</option>
              <option value="OXYGEN_HDU" ${currentForm.requiredBedType === 'OXYGEN_HDU' ? 'selected' : ''}>OXYGEN_HDU</option>
              <option value="GENERAL_WARD" ${currentForm.requiredBedType === 'GENERAL_WARD' ? 'selected' : ''}>GENERAL_WARD</option>
              <option value="PEDIATRIC_ICU" ${currentForm.requiredBedType === 'PEDIATRIC_ICU' ? 'selected' : ''}>PEDIATRIC_ICU</option>
            </select>
          </div>
          <div class="sm:col-span-2 lg:col-span-3 flex items-center space-x-2 flex-wrap gap-y-1.5">
            <span class="font-bold text-slate-700 block mr-2 text-xs">Mandatory Capabilities:</span>
            ${capabilityCheckboxesHtml}
          </div>
          <div class="sm:col-span-2 lg:col-span-1 flex items-end">
            <button type="submit" id="btn-submit-ranking" class="w-full py-2 px-4 rounded-lg bg-gradient-to-r from-rose-600 to-indigo-600 hover:from-rose-700 hover:to-indigo-700 text-white font-bold text-xs shadow-md transition-all">
              Evaluate Ranking API
            </button>
          </div>
        </form>

      </div>

      <!-- Results Container -->
      <div id="ranking-results-container">
        ${resultsHtml}
      </div>

    </div>
  `;

  // Bind Form Submit - Current Checkboxes are the single source of truth!
  container.querySelector('#ranking-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const lat = parseFloat(container.querySelector('#rank-lat').value);
    const lng = parseFloat(container.querySelector('#rank-lng').value);
    const priority = container.querySelector('#rank-priority').value;
    const requiredBedType = container.querySelector('#rank-bed-type').value;
    const requiredCapabilities = Array.from(container.querySelectorAll('.rank-cap:checked')).map(c => c.value);

    const payload = {
      emergencyId: `eval-${Date.now().toString(36)}`,
      patientLocation: { latitude: lat, longitude: lng, address: 'Custom Coordinates' },
      emergencyType: 'DEMO_EVALUATION',
      priority,
      requiredBedType,
      requiredCapabilities
    };

    if (onFormChange) {
      onFormChange({
        latitude: lat,
        longitude: lng,
        priority,
        requiredBedType,
        requiredCapabilities
      });
    }

    onRank(payload);
  });

  // Track live checkbox changes to keep state authoritative
  container.querySelectorAll('.rank-cap').forEach(cb => {
    cb.addEventListener('change', () => {
      const activeCaps = Array.from(container.querySelectorAll('.rank-cap:checked')).map(c => c.value);
      if (onFormChange) {
        onFormChange({ requiredCapabilities: activeCaps });
      }
    });
  });

  // Track live field changes to keep state authoritative
  ['#rank-lat', '#rank-lng', '#rank-priority', '#rank-bed-type'].forEach(sel => {
    const el = container.querySelector(sel);
    if (!el) return;
    el.addEventListener('change', () => {
      if (onFormChange) {
        onFormChange({
          latitude: parseFloat(container.querySelector('#rank-lat').value) || 0,
          longitude: parseFloat(container.querySelector('#rank-lng').value) || 0,
          priority: container.querySelector('#rank-priority').value,
          requiredBedType: container.querySelector('#rank-bed-type').value,
        });
      }
    });
  });

  // Bind Presets - Updates DOM inputs, authoritative state, and runs evaluation
  container.querySelectorAll('.btn-preset').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.dataset.preset, 10);
      const preset = presets[idx];
      if (!preset) return;

      const payload = preset.payload;
      container.querySelector('#rank-lat').value = payload.patientLocation.latitude;
      container.querySelector('#rank-lng').value = payload.patientLocation.longitude;
      container.querySelector('#rank-priority').value = payload.priority;
      container.querySelector('#rank-bed-type').value = payload.requiredBedType;
      container.querySelectorAll('.rank-cap').forEach(cb => {
        cb.checked = (payload.requiredCapabilities || []).includes(cb.value);
      });

      if (onFormChange) {
        onFormChange({
          latitude: payload.patientLocation.latitude,
          longitude: payload.patientLocation.longitude,
          priority: payload.priority,
          requiredBedType: payload.requiredBedType,
          requiredCapabilities: payload.requiredCapabilities || []
        });
      }

      onRank(payload);
    });
  });
}
