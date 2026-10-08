import { api } from './api.js';
import { renderHeader } from './components/Header.js';
import { renderStatsOverview } from './components/StatsOverview.js';
import { renderBedGrid } from './components/BedGrid.js';
import { renderEmergencyQueue } from './components/EmergencyQueue.js';
import { renderReservationsTable } from './components/ReservationsTable.js';
import { renderRankingDemo } from './components/RankingDemo.js';
import { renderReassignmentAudit } from './components/ReassignmentAudit.js';

class HospitalDashboardApp {
  constructor() {
    this.state = {
      hospitals: [],
      selectedHospitalId: null,
      hospitalDetail: null,
      bedSummary: null,
      beds: [],
      queue: [],
      reservations: [],
      auditLogs: [],
      activeTab: 'overview',
      rankingResults: null,
      isRanking: false,
      lastReassignmentResult: null,
      isEvaluating: false,
      isRefreshing: false,
      bedFilters: { category: 'ALL', status: 'ALL' },
      rankingForm: {
        latitude: 12.9716,
        longitude: 77.5946,
        priority: 'P1_CRITICAL',
        requiredBedType: 'ICU',
        requiredCapabilities: ['CARDIAC_CATH_LAB', 'ICU_VENTILATOR']
      },
    };

    this.pollTimer = null;
  }

  async init() {
    try {
      this.showToast('Connecting to Hospital Intelligence Subsystem...', 'info');
      const hospitals = await api.getHospitals();
      this.state.hospitals = hospitals;

      if (hospitals.length > 0) {
        this.state.selectedHospitalId = hospitals[0].id;
      }

      await this.loadAllData();

      // Start 10-second polling (explicitly labeled in UI, not claimed as real-time)
      this.pollTimer = setInterval(() => {
        this.loadAllData(false);
      }, 10000);

      this.render();
    } catch (err) {
      console.error('Initialization failed:', err);
      this.showToast(`Failed to load hospital data: ${err.message}`, 'error');
      this.renderError(err.message);
    }
  }

  async loadAllData(showIndicator = true) {
    if (!this.state.selectedHospitalId) return;

    if (showIndicator) {
      this.state.isRefreshing = true;
      this.renderHeaderOnly();
    }

    try {
      const hospId = this.state.selectedHospitalId;
      const [detail, summary, beds, queue, reservations, audits] = await Promise.all([
        api.getHospitalDetails(hospId).catch(() => null),
        api.getHospitalBedSummary(hospId).catch(() => null),
        api.getHospitalBeds(hospId).catch(() => []),
        api.getHospitalQueue(hospId).catch(() => []),
        api.getHospitalReservations(hospId).catch(() => []),
        api.getReassignmentAudit().catch(() => []),
      ]);

      if (detail) this.state.hospitalDetail = detail;
      if (summary) this.state.bedSummary = summary;
      this.state.beds = beds || [];
      this.state.queue = queue || [];
      this.state.reservations = reservations || [];
      this.state.auditLogs = audits || [];

    } catch (err) {
      console.error('Error fetching dashboard state:', err);
      this.showToast(`Update error: ${err.message}`, 'error');
    } finally {
      this.state.isRefreshing = false;
      if (this.state.activeTab === 'ranking' && !showIndicator) {
        this.renderHeaderOnly();
      } else {
        this.render();
      }
    }
  }

  showToast(message, tone = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    const bg = tone === 'error' ? 'bg-rose-600 text-white' : tone === 'success' ? 'bg-emerald-600 text-white' : 'bg-slate-900 text-white';
    toast.className = `${bg} px-4 py-2.5 rounded-xl shadow-lg text-xs font-semibold flex items-center space-x-2 transition-all duration-300 transform translate-y-2 opacity-0`;
    toast.innerHTML = `<span>${message}</span>`;
    
    container.appendChild(toast);
    requestAnimationFrame(() => {
      toast.classList.remove('translate-y-2', 'opacity-0');
    });

    setTimeout(() => {
      toast.classList.add('opacity-0', 'translate-y-2');
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  handleSelectHospital(newId) {
    this.state.selectedHospitalId = newId;
    this.showToast(`Switched hospital desk to ${newId}`, 'info');
    this.loadAllData(true);
  }

  async handleUpdateBedStatus(bedId, targetStatus) {
    try {
      this.showToast(`Updating bed ${bedId} to ${targetStatus}...`, 'info');
      await api.updateBedStatus(this.state.selectedHospitalId, bedId, targetStatus);
      this.showToast(`Bed updated to ${targetStatus} successfully!`, 'success');
      await this.loadAllData(false);
    } catch (err) {
      this.showToast(`Failed to update bed: ${err.message}`, 'error');
    }
  }

  async handleRankHospitals(payload) {
    if (payload) {
      this.state.rankingForm = {
        latitude: payload.patientLocation?.latitude ?? this.state.rankingForm.latitude,
        longitude: payload.patientLocation?.longitude ?? this.state.rankingForm.longitude,
        priority: payload.priority || this.state.rankingForm.priority,
        requiredBedType: payload.requiredBedType || this.state.rankingForm.requiredBedType,
        requiredCapabilities: Array.isArray(payload.requiredCapabilities) ? [...payload.requiredCapabilities] : []
      };
    }
    this.state.isRanking = true;
    this.render();
    try {
      this.showToast('Evaluating deterministic hospital ranking...', 'info');
      const results = await api.rankHospitals(payload);
      this.state.rankingResults = results;
      this.showToast(`Ranking complete! Top recommendation: ${results.rankedHospitals[0]?.name}`, 'success');
    } catch (err) {
      this.showToast(`Ranking evaluation failed: ${err.message}`, 'error');
    } finally {
      this.state.isRanking = false;
      this.render();
    }
  }

  async handleTriggerScenario(routeProgress) {
    this.state.isEvaluating = true;
    this.render();

    try {
      const hospId = this.state.selectedHospitalId;
      const isScenarioC = routeProgress < 40.0;
      this.showToast(`Evaluating Reassignment for Scenario (Progress: ${routeProgress}%)...`, 'info');

      // Setup contention context with simulated route progress
      const payload = {
        displacingEmergencyId: `emg-demo-p1-${Date.now().toString(36)}`,
        displacingPriority: 'P1_CRITICAL',
        requiredBedType: 'ICU',
        targetHospitalId: hospId,
        patientLocation: { latitude: 12.9716, longitude: 77.5946, address: 'Demo Evaluation Location' },
        simulatedRouteProgress: routeProgress
      };

      const result = await api.evaluateReassignment(payload);
      this.state.lastReassignmentResult = result;

      // Immediately fetch fresh persisted audit logs from database
      const freshAudits = await api.getReassignmentAudit().catch(() => null);
      if (freshAudits) {
        this.state.auditLogs = freshAudits;
      }

      if (result.decision === 'REASSIGNMENT_APPROVED') {
        this.showToast(`Scenario C Approved: Reassigned bed at ${routeProgress}% progress (< 40% threshold)!`, 'success');
      } else {
        this.showToast(`Scenario D Rejected: Reservation retained at ${routeProgress}% progress (>= 40% threshold)!`, 'info');
      }

      await this.loadAllData(false);

    } catch (err) {
      this.showToast(`Reassignment trigger failed: ${err.message}`, 'error');
    } finally {
      this.state.isEvaluating = false;
      this.render();
    }
  }

  renderHeaderOnly() {
    const headerContainer = document.getElementById('header-root');
    if (!headerContainer) return;

    renderHeader(headerContainer, {
      hospitals: this.state.hospitals,
      selectedHospitalId: this.state.selectedHospitalId,
      hospitalDetail: this.state.hospitalDetail,
      onSelectHospital: (id) => this.handleSelectHospital(id),
      onRefresh: () => this.loadAllData(true),
      isRefreshing: this.state.isRefreshing
    });
  }

  render() {
    this.renderHeaderOnly();

    // Render Tab Navigation
    const navContainer = document.getElementById('tab-navigation');
    if (navContainer) {
      const tabs = [
        { id: 'overview', label: 'Operations Overview', icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/>' },
        { id: 'beds', label: 'Bed Inventory Matrix', count: this.state.beds.length, icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>' },
        { id: 'queue', label: 'Emergency Priority Queue', count: this.state.queue.length, badgeColor: 'bg-rose-500', icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>' },
        { id: 'reservations', label: 'Bed Reservations', count: this.state.reservations.length, icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>' },
        { id: 'ranking', label: '4-Factor Ranking Evaluator', icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>' },
        { id: 'reassignment', label: '40% Policy & Audit', count: this.state.auditLogs.length, icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>' },
      ];

      navContainer.innerHTML = tabs.map(tab => {
        const isActive = this.state.activeTab === tab.id;
        const activeClasses = isActive 
          ? 'border-rose-600 text-rose-600 bg-rose-50/50 font-bold'
          : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300 font-medium';

        return `
          <button class="tab-nav-btn whitespace-nowrap py-3 px-3.5 border-b-2 text-xs flex items-center space-x-2 transition-all cursor-pointer ${activeClasses}" data-tab="${tab.id}">
            <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">${tab.icon}</svg>
            <span>${tab.label}</span>
            ${tab.count !== undefined ? `
              <span class="ml-1.5 py-0.5 px-2 rounded-full text-[10px] font-bold ${isActive ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-600'}">
                ${tab.count}
              </span>
            ` : ''}
          </button>
        `;
      }).join('');

      navContainer.querySelectorAll('.tab-nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          this.state.activeTab = btn.dataset.tab;
          this.render();
        });
      });
    }

    // Render Tab Content View
    const contentContainer = document.getElementById('tab-content');
    if (!contentContainer) return;

    if (this.state.activeTab === 'overview') {
      renderStatsOverview(contentContainer, {
        bedSummary: this.state.bedSummary,
        queueCount: this.state.queue.length,
        activeReservationsCount: this.state.reservations.filter(r => r.status === 'RESERVED').length,
      });
    } else if (this.state.activeTab === 'beds') {
      renderBedGrid(contentContainer, {
        beds: this.state.beds,
        selectedCategory: this.state.bedFilters.category,
        selectedStatus: this.state.bedFilters.status,
        onFilterChange: (newFilters) => {
          this.state.bedFilters = newFilters;
          this.render();
        },
        onUpdateStatus: (bedId, targetStatus) => this.handleUpdateBedStatus(bedId, targetStatus)
      });
    } else if (this.state.activeTab === 'queue') {
      renderEmergencyQueue(contentContainer, {
        queue: this.state.queue
      });
    } else if (this.state.activeTab === 'reservations') {
      renderReservationsTable(contentContainer, {
        reservations: this.state.reservations
      });
    } else if (this.state.activeTab === 'ranking') {
      renderRankingDemo(contentContainer, {
        rankingForm: this.state.rankingForm,
        rankingResults: this.state.rankingResults,
        isRanking: this.state.isRanking,
        onRank: (payload) => this.handleRankHospitals(payload),
        onFormChange: (formUpdate) => {
          this.state.rankingForm = { ...this.state.rankingForm, ...formUpdate };
        }
      });
    } else if (this.state.activeTab === 'reassignment') {
      renderReassignmentAudit(contentContainer, {
        auditLogs: this.state.auditLogs,
        lastReassignmentResult: this.state.lastReassignmentResult,
        isEvaluating: this.state.isEvaluating,
        onTriggerScenario: (progress) => this.handleTriggerScenario(progress)
      });
    }
  }

  renderError(msg) {
    const contentContainer = document.getElementById('tab-content');
    if (contentContainer) {
      contentContainer.innerHTML = `
        <div class="bg-rose-50 border border-rose-200 p-6 rounded-2xl text-center">
          <h3 class="text-sm font-bold text-rose-800">Connection Failed</h3>
          <p class="text-xs text-rose-600 mt-1">${msg}</p>
          <button onclick="location.reload()" class="mt-4 px-4 py-1.5 rounded-lg bg-rose-600 text-white text-xs font-bold shadow-sm">
            Retry Connection
          </button>
        </div>
      `;
    }
  }
}

// Start application on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  const app = new HospitalDashboardApp();
  app.init();
});
