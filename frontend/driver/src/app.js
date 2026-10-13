/**
 * SirenSync Driver Interface Application (Member 3 - Nidhi)
 * Core application container managing state, real-time WebSocket telemetry,
 * REST fallback snapshots, status machine transitions, and prototype simulation.
 */

import { api } from './api.js';
import { renderDriverHeader } from './components/DriverHeader.js';
import { renderAssignmentCard } from './components/AssignmentCard.js';
import { renderWorkflowActions } from './components/WorkflowActions.js';
import { renderLocationSimulator } from './components/LocationSimulator.js';
import { renderRerouteBanner } from './components/RerouteBanner.js';

class DriverDashboardApp {
  constructor() {
    this.state = {
      fleet: [],
      selectedAmbulanceId: null,
      selectedAmbulance: null,
      destinationHospital: null,
      rerouteAlert: null,
      wsConnected: false,
      usingRestFallback: false,
      isRefreshing: false,
      isSubmittingStatus: false,
      statusNotes: '',
    };

    this.ws = null;
    this.wsHeartbeatTimer = null;
    this.wsReconnectTimer = null;
    this.restFallbackTimer = null;
  }

  async init() {
    try {
      this.showToast('Initializing SirenSync Driver Console...', 'info');
      await this.loadFleet();

      if (this.state.fleet.length > 0) {
        // Default to first active assigned ambulance, or first available
        const assignedAmb = this.state.fleet.find(a => Boolean(a.assignedEmergencyId));
        const initialId = assignedAmb ? assignedAmb.id : this.state.fleet[0].id;
        await this.selectAmbulance(initialId, false);
      } else {
        this.render();
      }
    } catch (err) {
      console.error('Initialization error:', err);
      this.showToast(`Initialization error: ${err.message}`, 'error');
      this.render();
    }
  }

  async loadFleet() {
    try {
      const fleet = await api.getAmbulances();
      this.state.fleet = fleet || [];
    } catch (err) {
      console.error('Failed to load fleet:', err);
      this.showToast(`Fleet load failed: ${err.message}`, 'error');
    }
  }

  async selectAmbulance(ambulanceId, shouldToast = true) {
    this.state.selectedAmbulanceId = ambulanceId;
    this.state.rerouteAlert = null;
    this.state.destinationHospital = null;

    // Immediately teardown previous socket and polling before initiating fetch
    this.stopRestFallbackPolling();
    this.cleanupWebSocket();

    try {
      this.state.isRefreshing = true;
      const amb = await api.getAmbulance(ambulanceId);

      // Guard against race conditions if another ambulance was selected while fetching
      if (this.state.selectedAmbulanceId !== ambulanceId) return;

      this.state.selectedAmbulance = amb;

      // Update fleet record
      const idx = this.state.fleet.findIndex(a => a.id === ambulanceId);
      if (idx !== -1) {
        this.state.fleet[idx] = amb;
      }

      // Load destination hospital details if assigned
      if (amb.destinationHospitalId) {
        try {
          const hosp = await api.getHospital(amb.destinationHospitalId);
          if (this.state.selectedAmbulanceId === ambulanceId) {
            this.state.destinationHospital = hosp;
          }
        } catch (e) {
          console.warn('Could not load hospital details:', e);
        }
      }

      // Reconnect WebSocket to new emergency channel if assigned
      if (this.state.selectedAmbulanceId === ambulanceId) {
        this.connectWebSocket();
      }

      if (shouldToast && this.state.selectedAmbulanceId === ambulanceId) {
        this.showToast(`Selected vehicle ${amb.vehicleNumber} (${amb.driverName})`, 'info');
      }
    } catch (err) {
      if (this.state.selectedAmbulanceId === ambulanceId) {
        console.error('Error selecting ambulance:', err);
        this.showToast(`Error: ${err.message}`, 'error');
      }
    } finally {
      if (this.state.selectedAmbulanceId === ambulanceId) {
        this.state.isRefreshing = false;
        this.render();
      }
    }
  }

  /**
   * WebSocket Connection Management
   * Strictly subscribes to the specific emergency channel immediately upon connection.
   * Never subscribes to global "all" from an individual driver screen.
   */
  connectWebSocket() {
    // Teardown any existing socket
    this.cleanupWebSocket();

    const currentAmb = this.state.selectedAmbulance;
    const ambId = currentAmb?.id;
    const emgId = currentAmb?.assignedEmergencyId;

    if (!ambId || !emgId) {
      // Unassigned vehicle: no emergency channel to subscribe to
      this.state.wsConnected = false;
      this.state.usingRestFallback = false;
      this.stopRestFallbackPolling();
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/v1/tracking/ws`;

    try {
      const socket = new WebSocket(wsUrl);
      this.ws = socket;

      socket.onopen = () => {
        // Obsolete socket check: ignore if socket is superseded or ambulance selection changed
        if (this.ws !== socket || this.state.selectedAmbulanceId !== ambId) {
          try { socket.close(); } catch (e) {}
          return;
        }

        this.state.wsConnected = true;
        this.state.usingRestFallback = false;
        this.stopRestFallbackPolling();

        // Immediately subscribe to the specific emergency channel
        socket.send(JSON.stringify({
          action: 'subscribe',
          emergency_id: emgId,
        }));

        // Start ping heartbeat for this active socket
        this.wsHeartbeatTimer = setInterval(() => {
          if (this.ws === socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ action: 'ping' }));
          }
        }, 20000);

        this.renderHeaderOnly();
      };

      socket.onmessage = (event) => {
        if (this.ws !== socket || this.state.selectedAmbulanceId !== ambId) {
          return;
        }
        try {
          const msg = JSON.parse(event.data);
          this.handleWebSocketMessage(msg, ambId, emgId);
        } catch (e) {
          console.error('Failed to parse WS message:', e);
        }
      };

      socket.onerror = (err) => {
        if (this.ws !== socket || this.state.selectedAmbulanceId !== ambId) {
          return;
        }
        console.warn('WebSocket error, switching to REST fallback:', err);
        this.handleWebSocketDisconnect(socket, ambId, emgId);
      };

      socket.onclose = () => {
        if (this.ws !== socket || this.state.selectedAmbulanceId !== ambId) {
          return;
        }
        console.log('WebSocket connection closed.');
        this.handleWebSocketDisconnect(socket, ambId, emgId);
      };

    } catch (err) {
      console.error('Failed to instantiate WebSocket:', err);
      if (this.state.selectedAmbulanceId === ambId) {
        this.handleWebSocketDisconnect(null, ambId, emgId);
      }
    }
  }

  handleWebSocketDisconnect(socket = null, ambId = null, emgId = null) {
    // If a specific socket was passed, ensure it is the active one
    if (socket && this.ws !== socket) {
      return;
    }
    // Ensure the ambulance context matches current selection
    if (ambId && this.state.selectedAmbulanceId !== ambId) {
      return;
    }

    this.state.wsConnected = false;
    this.state.usingRestFallback = true;
    this.renderHeaderOnly();

    // Start REST snapshot polling fallback
    this.startRestFallbackPolling();

    // Attempt WS reconnection after 5 seconds if still on the same emergency
    if (!this.wsReconnectTimer) {
      this.wsReconnectTimer = setTimeout(() => {
        this.wsReconnectTimer = null;
        const targetAmbId = ambId || this.state.selectedAmbulanceId;
        const targetEmgId = emgId || this.state.selectedAmbulance?.assignedEmergencyId;
        if (
          this.state.selectedAmbulanceId === targetAmbId &&
          this.state.selectedAmbulance?.assignedEmergencyId === targetEmgId
        ) {
          this.connectWebSocket();
        }
      }, 5000);
    }
  }

  cleanupWebSocket() {
    if (this.wsHeartbeatTimer) {
      clearInterval(this.wsHeartbeatTimer);
      this.wsHeartbeatTimer = null;
    }
    if (this.wsReconnectTimer) {
      clearTimeout(this.wsReconnectTimer);
      this.wsReconnectTimer = null;
    }
    if (this.ws) {
      const socket = this.ws;
      this.ws = null;
      socket.onopen = null;
      socket.onmessage = null;
      socket.onerror = null;
      socket.onclose = null;
      try {
        socket.close();
      } catch (e) {}
    }
    this.state.wsConnected = false;
  }

  startRestFallbackPolling() {
    if (this.restFallbackTimer) return;
    this.pollRestSnapshot();
    this.restFallbackTimer = setInterval(() => {
      this.pollRestSnapshot();
    }, 6000);
  }

  stopRestFallbackPolling() {
    if (this.restFallbackTimer) {
      clearInterval(this.restFallbackTimer);
      this.restFallbackTimer = null;
    }
  }

  async pollRestSnapshot() {
    const currentAmb = this.state.selectedAmbulance;
    const emgId = currentAmb?.assignedEmergencyId;
    const ambId = currentAmb?.id;
    if (!emgId || !ambId) return;

    try {
      const snapshot = await api.getTrackingSnapshot(emgId);
      // Validate that snapshot identity matches the active emergency and ambulance
      if (
        snapshot &&
        snapshot.ambulanceId === ambId &&
        snapshot.emergencyId === emgId &&
        this.state.selectedAmbulanceId === ambId &&
        this.state.selectedAmbulance &&
        this.state.selectedAmbulance.id === ambId &&
        this.state.selectedAmbulance.assignedEmergencyId === emgId
      ) {
        if (typeof snapshot.routeProgress === 'number' && Number.isFinite(snapshot.routeProgress)) {
          this.state.selectedAmbulance.routeProgress = snapshot.routeProgress;
        }
        if (snapshot.status) {
          this.state.selectedAmbulance.status = snapshot.status;
        }
        if (snapshot.currentLocation) {
          this.state.selectedAmbulance.currentLocation = snapshot.currentLocation;
        }
        if (snapshot.destinationHospitalId) {
          this.state.selectedAmbulance.destinationHospitalId = snapshot.destinationHospitalId;
        }
        this.render();
      }
    } catch (e) {
      // Silently catch polling errors
    }
  }

  handleWebSocketMessage(msg, targetAmbId, targetEmgId) {
    const type = msg.type;
    const payload = msg.payload;

    if (!payload || !this.state.selectedAmbulance) return;
    if (this.state.selectedAmbulanceId !== targetAmbId) return;
    const activeAmb = this.state.selectedAmbulance;
    if (activeAmb.id !== targetAmbId) return;

    if (type === 'SNAPSHOT') {
      // Backend guarantees emergencyId and ambulanceId on TrackingSnapshotResponse
      if (!payload.emergencyId || !payload.ambulanceId) return;
      if (payload.emergencyId !== targetEmgId || payload.ambulanceId !== targetAmbId) return;

      if (typeof payload.routeProgress === 'number' && Number.isFinite(payload.routeProgress)) {
        activeAmb.routeProgress = payload.routeProgress;
      }
      if (payload.status) {
        activeAmb.status = payload.status;
      }
      if (payload.currentLocation) {
        activeAmb.currentLocation = payload.currentLocation;
      }
      if (payload.destinationHospitalId) {
        activeAmb.destinationHospitalId = payload.destinationHospitalId;
      }
      if (payload.destinationHospitalName && this.state.destinationHospital) {
        this.state.destinationHospital.name = payload.destinationHospitalName;
      }
      this.render();
    } else if (type === 'LOCATION_UPDATE') {
      if (payload.ambulanceId !== targetAmbId) return;
      activeAmb.currentLocation = {
        latitude: payload.latitude,
        longitude: payload.longitude,
        address: payload.address,
      };
      this.render();
    } else if (type === 'ROUTE_PROGRESS_UPDATE') {
      if (payload.ambulanceId !== targetAmbId) return;
      if (typeof payload.routeProgress === 'number' && Number.isFinite(payload.routeProgress)) {
        activeAmb.routeProgress = payload.routeProgress;
      }
      this.render();
    } else if (type === 'STATUS_CHANGE') {
      if (payload.ambulanceId !== targetAmbId) return;
      activeAmb.status = payload.status;
      this.showToast(`Status updated: ${payload.status}`, 'info');
      this.render();
    } else if (type === 'REROUTE_ALERT') {
      if (payload.ambulanceId && payload.ambulanceId !== targetAmbId) return;
      if (!payload.emergencyId || payload.emergencyId !== targetEmgId) return;

      this.state.rerouteAlert = payload;
      this.showToast('🚨 URGENT REROUTE: Destination hospital reassigned!', 'warning');
      // Refresh destination hospital from authoritative backend
      if (payload.newHospitalId) {
        api.getHospital(payload.newHospitalId).then(hosp => {
          if (
            this.state.selectedAmbulanceId === targetAmbId &&
            this.state.selectedAmbulance &&
            this.state.selectedAmbulance.id === targetAmbId &&
            this.state.selectedAmbulance.assignedEmergencyId === targetEmgId
          ) {
            this.state.destinationHospital = hosp;
            this.state.selectedAmbulance.destinationHospitalId = payload.newHospitalId;
            this.state.selectedAmbulance.routeProgress = 0.0;
            this.render();
          }
        }).catch(() => {
          if (this.state.selectedAmbulanceId === targetAmbId) {
            this.render();
          }
        });
      } else {
        this.render();
      }
    }
  }

  async handleStatusTransition(targetStatus) {
    const ambId = this.state.selectedAmbulanceId;
    if (!ambId) return;

    this.state.isSubmittingStatus = true;
    this.render();

    try {
      const notes = this.state.statusNotes ? this.state.statusNotes.trim() : null;
      const updated = await api.updateStatus(ambId, targetStatus, notes);

      // Refresh fleet records in the background
      await this.loadFleet();

      // Verify that the same ambulance is still selected before updating selection-specific state
      if (this.state.selectedAmbulanceId === ambId) {
        this.state.selectedAmbulance = updated;
        this.state.statusNotes = '';

        // If finished mission (transitioned to AVAILABLE), clear emergency channel
        if (targetStatus === 'AVAILABLE') {
          this.state.rerouteAlert = null;
          this.state.destinationHospital = null;
          this.cleanupWebSocket();
        }

        this.showToast(`Status successfully changed to ${targetStatus}`, 'success');
      }
    } catch (err) {
      if (this.state.selectedAmbulanceId === ambId) {
        console.error('Status transition rejected:', err);
        this.showToast(`Transition failed: ${err.message}`, 'error');
      }
    } finally {
      if (this.state.selectedAmbulanceId === ambId) {
        this.state.isSubmittingStatus = false;
        this.render();
      }
    }
  }

  async handleLocationUpdate(lat, lng, address) {
    const ambId = this.state.selectedAmbulanceId;
    if (!ambId) return;

    if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
      this.showToast('Latitude must be a valid number between -90 and 90.', 'error');
      return;
    }
    if (!Number.isFinite(lng) || lng < -180 || lng > 180) {
      this.showToast('Longitude must be a valid number between -180 and 180.', 'error');
      return;
    }

    try {
      const updated = await api.updateLocation(ambId, {
        latitude: lat,
        longitude: lng,
        address,
        isSimulated: true,
      });

      // Update fleet list item
      const idx = this.state.fleet.findIndex(a => a.id === ambId);
      if (idx !== -1) {
        this.state.fleet[idx] = updated;
      }

      // Verify that the same ambulance is still selected before updating selection-specific state
      if (this.state.selectedAmbulanceId === ambId) {
        this.state.selectedAmbulance = updated;
        this.showToast('Simulated coordinates transmitted successfully', 'success');
        this.render();
      }
    } catch (err) {
      if (this.state.selectedAmbulanceId === ambId) {
        console.error('Failed to update location:', err);
        this.showToast(`Location update error: ${err.message}`, 'error');
      }
    }
  }

  async handleProgressUpdate(newProgress) {
    const amb = this.state.selectedAmbulance;
    const ambId = this.state.selectedAmbulanceId;
    if (!amb || !ambId) return;

    if (!Number.isFinite(newProgress) || newProgress < 0 || newProgress > 100) {
      this.showToast('Route progress must be a number between 0% and 100%.', 'error');
      return;
    }

    const currentProg = (typeof amb.routeProgress === 'number' && Number.isFinite(amb.routeProgress))
      ? amb.routeProgress
      : 0.0;

    // Guard monotonic progression locally before submitting
    if (newProgress < currentProg) {
      this.showToast(
        `Route progress cannot move backward (current: ${currentProg.toFixed(1)}%, target: ${newProgress.toFixed(1)}%)`,
        'error'
      );
      return;
    }

    try {
      const updated = await api.updateRouteProgress(ambId, {
        routeProgress: newProgress,
        emergencyId: amb.assignedEmergencyId,
        isSimulated: true,
      });

      // Update fleet list item
      const idx = this.state.fleet.findIndex(a => a.id === ambId);
      if (idx !== -1) {
        this.state.fleet[idx] = updated;
      }

      // Verify that the same ambulance is still selected before updating selection-specific state
      if (this.state.selectedAmbulanceId === ambId) {
        this.state.selectedAmbulance = updated;
        this.showToast(`Route progress updated to ${newProgress.toFixed(1)}%`, 'success');
        this.render();
      }
    } catch (err) {
      if (this.state.selectedAmbulanceId === ambId) {
        console.error('Failed to update progress:', err);
        this.showToast(`Progress update error: ${err.message}`, 'error');
      }
    }
  }

  async handleAcknowledgeReroute() {
    const ambId = this.state.selectedAmbulanceId;
    this.state.rerouteAlert = null;
    this.showToast('Reroute acknowledged. Destination synchronized.', 'success');
    if (ambId) {
      await this.selectAmbulance(ambId, false);
    }
  }

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    const borderColors = {
      success: 'border-emerald-500 bg-emerald-950/90 text-emerald-200',
      error: 'border-rose-500 bg-rose-950/90 text-rose-200',
      warning: 'border-amber-500 bg-amber-950/90 text-amber-200',
      info: 'border-blue-500 bg-slate-900/90 text-slate-200',
    };

    toast.className = `px-4 py-3 rounded-xl shadow-xl border text-xs font-medium max-w-sm pointer-events-auto transition-all duration-300 transform translate-y-2 opacity-0 flex items-center justify-between gap-3 ${borderColors[type] || borderColors.info}`;

    const contentWrapper = document.createElement('div');
    contentWrapper.className = 'flex items-center space-x-2';
    const textSpan = document.createElement('span');
    textSpan.textContent = String(message);
    contentWrapper.appendChild(textSpan);

    const closeBtn = document.createElement('button');
    closeBtn.className = 'text-slate-400 hover:text-white font-bold ml-2 cursor-pointer';
    closeBtn.innerHTML = '&times;';
    closeBtn.setAttribute('aria-label', 'Close toast');
    closeBtn.addEventListener('click', () => {
      toast.remove();
    });

    toast.appendChild(contentWrapper);
    toast.appendChild(closeBtn);

    container.appendChild(toast);
    requestAnimationFrame(() => {
      toast.classList.remove('translate-y-2', 'opacity-0');
    });

    setTimeout(() => {
      toast.classList.add('opacity-0', 'translate-y-2');
      setTimeout(() => toast.remove(), 300);
    }, 4500);
  }

  renderHeaderOnly() {
    const headerRoot = document.getElementById('header-root');
    if (headerRoot) {
      headerRoot.innerHTML = renderDriverHeader(
        this.state,
        (id) => this.selectAmbulance(id),
        () => this.loadFleet()
      );
      this.attachHeaderListeners();
    }
  }

  render() {
    this.renderHeaderOnly();

    const mainContent = document.getElementById('main-content');
    if (!mainContent) return;

    mainContent.innerHTML = `
      ${renderRerouteBanner(this.state, () => this.handleAcknowledgeReroute())}
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <!-- Left Column: Assignment & Workflow Actions (7 cols) -->
        <div class="lg:col-span-7 space-y-6">
          ${renderAssignmentCard(this.state)}
          ${renderWorkflowActions(this.state)}
        </div>

        <!-- Right Column: Location & Progress Telemetry Simulator (5 cols) -->
        <div class="lg:col-span-5 space-y-6">
          ${renderLocationSimulator(this.state)}
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  attachHeaderListeners() {
    const selector = document.getElementById('ambulance-selector');
    if (selector) {
      selector.addEventListener('change', (e) => {
        this.selectAmbulance(e.target.value);
      });
    }

    const refreshBtn = document.getElementById('btn-refresh-state');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        if (this.state.selectedAmbulanceId) {
          this.selectAmbulance(this.state.selectedAmbulanceId);
        } else {
          this.loadFleet();
        }
      });
    }
  }

  attachEventListeners() {
    // Status transition buttons
    document.querySelectorAll('.btn-status-transition').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const targetStatus = e.currentTarget.getAttribute('data-status');
        if (targetStatus) {
          this.handleStatusTransition(targetStatus);
        }
      });
    });

    // Notes input
    const notesInput = document.getElementById('status-notes-input');
    if (notesInput) {
      notesInput.addEventListener('input', (e) => {
        this.state.statusNotes = e.target.value;
      });
    }

    // Acknowledge Reroute Banner
    const ackBtn = document.getElementById('btn-ack-reroute');
    if (ackBtn) {
      ackBtn.addEventListener('click', () => {
        this.handleAcknowledgeReroute();
      });
    }

    // Waypoint preset pills
    document.querySelectorAll('.btn-apply-waypoint').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const lat = parseFloat(e.currentTarget.getAttribute('data-lat'));
        const lng = parseFloat(e.currentTarget.getAttribute('data-lng'));
        const addr = e.currentTarget.getAttribute('data-addr');
        const latInput = document.getElementById('sim-lat');
        const lngInput = document.getElementById('sim-lng');
        const addrInput = document.getElementById('sim-addr');
        if (latInput && Number.isFinite(lat)) latInput.value = lat.toFixed(4);
        if (lngInput && Number.isFinite(lng)) lngInput.value = lng.toFixed(4);
        if (addrInput) addrInput.value = addr || '';
      });
    });

    // Location update form
    const locForm = document.getElementById('form-location-update');
    if (locForm) {
      locForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const lat = parseFloat(document.getElementById('sim-lat')?.value);
        const lng = parseFloat(document.getElementById('sim-lng')?.value);
        const addr = document.getElementById('sim-addr')?.value?.trim() || null;
        if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
          this.showToast('Please enter a valid latitude between -90 and 90.', 'error');
          return;
        }
        if (!Number.isFinite(lng) || lng < -180 || lng > 180) {
          this.showToast('Please enter a valid longitude between -180 and 180.', 'error');
          return;
        }
        this.handleLocationUpdate(lat, lng, addr);
      });
    }

    // Route progress range slider input synchronization
    const rangeSlider = document.getElementById('sim-progress-range');
    const valLabel = document.getElementById('progress-val-label');
    if (rangeSlider && valLabel) {
      rangeSlider.addEventListener('input', (e) => {
        valLabel.textContent = `${parseFloat(e.target.value).toFixed(1)}%`;
      });
    }

    // Quick increment step buttons
    document.querySelectorAll('.btn-step-progress').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const add = parseFloat(e.currentTarget.getAttribute('data-add') || 0);
        if (rangeSlider && valLabel) {
          const current = parseFloat(rangeSlider.value) || 0;
          const min = parseFloat(rangeSlider.min) || 0;
          const next = Math.max(min, Math.min(100.0, current + add));
          rangeSlider.value = next.toFixed(1);
          valLabel.textContent = `${next.toFixed(1)}%`;
        }
      });
    });

    // Progress update form
    const progForm = document.getElementById('form-progress-update');
    if (progForm && rangeSlider) {
      progForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const targetVal = parseFloat(rangeSlider.value);
        if (!Number.isFinite(targetVal) || targetVal < 0 || targetVal > 100) {
          this.showToast('Please select a valid progress percentage between 0% and 100%.', 'error');
          return;
        }
        this.handleProgressUpdate(targetVal);
      });
    }
  }
}

// Instantiate and start app on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  const app = new DriverDashboardApp();
  app.init();
});
