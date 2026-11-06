/**
 * MapView Component (Member 3 - Nidhi)
 * Interactive, free real-time telemetry map using Leaflet.js and OpenStreetMap tiles.
 *
 * Requirements:
 * - Zero external API keys or paid mapping services.
 * - Single Leaflet map instance lifecycle (initialized exactly once).
 * - Persistent across dashboard re-renders and polling cycles.
 * - In-place marker coordinate updates (setLatLng).
 * - Distinguishable Ambulance DivIcon (clearly labeled simulated if prototype mode).
 * - Distinguishable Hospital DivIcon for assigned destination facility.
 * - Non-disruptive bounds adjustment (avoids jarring zooms on routine coordinate updates).
 * - Safe handling of missing or invalid coordinates.
 * - Strict HTML escaping for popup / tooltip safety.
 */

import { escapeHtml, formatCoordinate } from '../utils.js';

export class MapView {
  constructor() {
    this.map = null;
    this.ambulanceMarker = null;
    this.hospitalMarker = null;
    this.routePolyline = null;

    this.isInitialized = false;
    this.currentAmbulanceId = null;
    this.currentHospitalId = null;
    this.hasInitialBounds = false;
    this.containerId = 'driver-leaflet-map';
  }

  /**
   * Mounts the MapView HTML card shell into the dedicated persistent DOM container slot.
   * Invokes L.map() initialization exactly once.
   */
  mount(slotId = 'map-view-slot') {
    const slot = document.getElementById(slotId);
    if (!slot) {
      console.warn(`[MapView] Slot element #${slotId} not found.`);
      return;
    }

    // Only render the card template shell if not already mounted
    if (!document.getElementById(this.containerId)) {
      slot.innerHTML = `
        <div class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <!-- Card Header Bar -->
          <div class="p-4 sm:p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-50/60">
            <div class="flex items-center space-x-2.5">
              <div class="h-8 w-8 rounded-lg bg-rose-600 text-white flex items-center justify-center shadow-sm">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                </svg>
              </div>
              <div>
                <div class="flex items-center space-x-2">
                  <h3 class="text-sm font-bold text-slate-900">Interactive Navigation & Telemetry Map</h3>
                  <span id="map-telemetry-badge" class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-100 text-amber-800 border border-amber-300">
                    Prototype Telemetry
                  </span>
                </div>
                <p id="map-subtext" class="text-xs text-slate-500">
                  OpenStreetMap tiles • Real-time vehicle & hospital positioning
                </p>
              </div>
            </div>

            <!-- Dynamic Coordinate Status Pill -->
            <div class="flex items-center space-x-2 text-[11px] font-mono bg-white px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 shadow-xs">
              <span class="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span id="map-coords-indicator">Coordinates: Initializing...</span>
            </div>
          </div>

          <!-- Leaflet Map Canvas Container -->
          <div class="relative w-full bg-slate-950">
            <div
              id="${this.containerId}"
              class="w-full h-80 sm:h-96 z-0"
              style="min-height: 320px;"
            ></div>

            <!-- Coordinate Missing / Standby Overlay Notice -->
            <div
              id="map-standby-overlay"
              class="hidden absolute inset-0 z-10 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 text-center pointer-events-none"
            >
              <div class="bg-white/95 rounded-xl px-4 py-3 shadow-lg border border-slate-200 max-w-sm pointer-events-auto">
                <p class="text-xs font-bold text-slate-800 mb-0.5">Ambulance Telemetry Pending</p>
                <p class="text-[11px] text-slate-500">No valid coordinates transmitted yet. Use the telemetry simulator below to transmit coordinates.</p>
              </div>
            </div>
          </div>

          <!-- Card Legend & OpenStreetMap Attribution Footer -->
          <div class="p-3 sm:px-5 bg-slate-50 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-500">
            <div class="flex flex-wrap items-center gap-4">
              <div class="flex items-center space-x-1.5">
                <span class="h-3 w-3 rounded-full bg-rose-600 inline-block border border-white shadow-xs"></span>
                <span class="font-medium text-slate-700">Ambulance (Vehicle Marker)</span>
              </div>
              <div class="flex items-center space-x-1.5">
                <span class="h-3 w-3 rounded-full bg-emerald-600 inline-block border border-white shadow-xs"></span>
                <span class="font-medium text-slate-700">Destination Hospital</span>
              </div>
              <div class="flex items-center space-x-1.5">
                <span class="w-4 h-0.5 border-t-2 border-dashed border-indigo-500 inline-block"></span>
                <span class="text-slate-600">Transit Corridor</span>
              </div>
            </div>

            <div class="text-[10px] text-slate-400">
              Free OpenStreetMap Engine • Zero Paid Mapping APIs
            </div>
          </div>
        </div>
      `;
    }

    this.initMap();
  }

  /**
   * Initializes the Leaflet map instance once.
   */
  initMap() {
    if (this.isInitialized || this.map) return;

    if (typeof window.L === 'undefined') {
      console.warn('[MapView] Leaflet library (window.L) is not loaded.');
      const container = document.getElementById(this.containerId);
      if (container) {
        container.innerHTML = `
          <div class="h-full w-full flex items-center justify-center bg-slate-900 text-slate-400 p-6 text-center text-xs">
            <div>
              <p class="font-semibold text-slate-200 mb-1">Leaflet Mapping Engine Loading...</p>
              <p class="text-slate-400 text-[11px]">Connecting to OpenStreetMap tile servers.</p>
            </div>
          </div>
        `;
      }
      return;
    }

    try {
      // Default initial view centered on Bengaluru transit coordinates
      const defaultCenter = [12.9716, 77.5946];
      this.map = window.L.map(this.containerId, {
        zoomControl: true,
        attributionControl: true,
        scrollWheelZoom: true,
      }).setView(defaultCenter, 13);

      // OpenStreetMap standard tile layer with mandatory attribution
      window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
      }).addTo(this.map);

      this.isInitialized = true;

      // Invalidate map size after DOM layout settles to prevent blank tiles
      setTimeout(() => {
        if (this.map) {
          this.map.invalidateSize();
        }
      }, 150);
    } catch (err) {
      console.error('[MapView] Error instantiating Leaflet map:', err);
    }
  }

  /**
   * Safely updates markers, polyline, and indicators from existing state without recreating the map.
   */
  update(state) {
    // If map was not initialized yet (e.g. Leaflet script loaded late), attempt init now
    if (!this.isInitialized || !this.map) {
      this.initMap();
      if (!this.isInitialized || !this.map) return;
    }

    const amb = state?.selectedAmbulance;
    const hosp = state?.destinationHospital;

    // 1. Validate Ambulance Coordinates
    const ambLat = (typeof amb?.currentLocation?.latitude === 'number')
      ? amb.currentLocation.latitude
      : parseFloat(amb?.currentLocation?.latitude);
    const ambLng = (typeof amb?.currentLocation?.longitude === 'number')
      ? amb.currentLocation.longitude
      : parseFloat(amb?.currentLocation?.longitude);

    const hasAmbCoords = Number.isFinite(ambLat) && Number.isFinite(ambLng) &&
      ambLat >= -90.0 && ambLat <= 90.0 && ambLng >= -180.0 && ambLng <= 180.0;

    // 2. Validate Hospital Coordinates
    const hospLat = (typeof hosp?.latitude === 'number')
      ? hosp.latitude
      : parseFloat(hosp?.latitude);
    const hospLng = (typeof hosp?.longitude === 'number')
      ? hosp.longitude
      : parseFloat(hosp?.longitude);

    const hasHospCoords = Number.isFinite(hospLat) && Number.isFinite(hospLng) &&
      hospLat >= -90.0 && hospLat <= 90.0 && hospLng >= -180.0 && hospLng <= 180.0;

    // Update Telemetry Header & Indicator Pill
    const coordsIndicator = document.getElementById('map-coords-indicator');
    if (coordsIndicator) {
      if (hasAmbCoords) {
        coordsIndicator.textContent = `${ambLat.toFixed(4)}°N, ${ambLng.toFixed(4)}°E`;
      } else {
        coordsIndicator.textContent = 'Standby / Coordinates Pending';
      }
    }

    const telemetryBadge = document.getElementById('map-telemetry-badge');
    if (telemetryBadge) {
      const isSim = amb?.isSimulated !== false;
      if (isSim) {
        telemetryBadge.textContent = 'Simulated Coordinates';
        telemetryBadge.className = 'px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-100 text-amber-800 border border-amber-300';
      } else {
        telemetryBadge.textContent = 'Live Telemetry';
        telemetryBadge.className = 'px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-100 text-emerald-800 border border-emerald-300';
      }
    }

    const subtextElem = document.getElementById('map-subtext');
    if (subtextElem) {
      if (amb && hosp && hasHospCoords) {
        subtextElem.textContent = `En route to ${hosp.name || 'Assigned Hospital'} • Transit corridor monitored`;
      } else if (amb) {
        subtextElem.textContent = `Vehicle ${amb.vehicleNumber || amb.id} • Status: ${amb.status ? amb.status.replace(/_/g, ' ') : 'Ready'}`;
      } else {
        subtextElem.textContent = 'OpenStreetMap tiles • Real-time vehicle & hospital positioning';
      }
    }

    const overlay = document.getElementById('map-standby-overlay');
    if (overlay) {
      if (!hasAmbCoords) {
        overlay.classList.remove('hidden');
      } else {
        overlay.classList.add('hidden');
      }
    }

    // 3. Update Ambulance Marker
    if (hasAmbCoords) {
      const isSim = amb?.isSimulated !== false;
      const simLabel = isSim ? '<span class="text-amber-600 font-bold">[SIMULATED GPS]</span> ' : '';
      const progressVal = Number.isFinite(amb?.routeProgress) ? amb.routeProgress.toFixed(1) : '0.0';

      const ambPopupContent = `
        <div class="text-xs p-1 space-y-1 font-sans">
          <div class="flex items-center space-x-1.5 pb-1 border-b border-slate-200">
            <span class="h-2 w-2 rounded-full bg-rose-600"></span>
            <strong class="text-slate-900">${simLabel}${escapeHtml(amb?.vehicleNumber || 'Ambulance')}</strong>
          </div>
          <div class="text-slate-600">
            <div><strong>Type:</strong> ${escapeHtml(amb?.ambulanceType || 'ALS')}</div>
            <div><strong>Driver:</strong> ${escapeHtml(amb?.driverName || 'N/A')} (${escapeHtml(amb?.driverContact || '')})</div>
            <div><strong>Status:</strong> <span class="font-bold text-rose-700">${escapeHtml(amb?.status || 'N/A')}</span></div>
            <div><strong>Journey Progress:</strong> ${progressVal}%</div>
            <div class="text-[11px] text-slate-500 font-mono mt-1 pt-1 border-t border-slate-100">
              ${ambLat.toFixed(4)}°N, ${ambLng.toFixed(4)}°E
            </div>
          </div>
        </div>
      `;

      if (this.ambulanceMarker) {
        // Reuse existing marker instance
        this.ambulanceMarker.setLatLng([ambLat, ambLng]);
        const popup = this.ambulanceMarker.getPopup();
        if (popup) {
          popup.setContent(ambPopupContent);
        } else {
          this.ambulanceMarker.bindPopup(ambPopupContent);
        }
      } else {
        // Create marker with custom DivIcon once
        const ambDivIcon = window.L.divIcon({
          className: 'sirensync-amb-marker-icon',
          html: `
            <div class="relative flex items-center justify-center cursor-pointer" style="width: 36px; height: 36px;">
              <span class="absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-60 animate-ping"></span>
              <div class="h-9 w-9 rounded-full bg-rose-600 text-white shadow-lg border-2 border-white flex items-center justify-center">
                <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
            </div>
          `,
          iconSize: [36, 36],
          iconAnchor: [18, 18],
          popupAnchor: [0, -18],
        });

        this.ambulanceMarker = window.L.marker([ambLat, ambLng], {
          icon: ambDivIcon,
          title: `Ambulance ${amb?.vehicleNumber || ''}`,
          zIndexOffset: 1000,
        }).addTo(this.map);

        this.ambulanceMarker.bindPopup(ambPopupContent);
        this.ambulanceMarker.bindTooltip(
          `${isSim ? '[SIM] ' : ''}${escapeHtml(amb?.vehicleNumber || 'Ambulance')}`,
          { direction: 'top', offset: [0, -18], permanent: false }
        );
      }
    } else if (this.ambulanceMarker) {
      this.map.removeLayer(this.ambulanceMarker);
      this.ambulanceMarker = null;
    }

    // 4. Update Hospital Marker
    if (hasHospCoords && hosp) {
      const hospPopupContent = `
        <div class="text-xs p-1 space-y-1 font-sans">
          <div class="flex items-center space-x-1.5 pb-1 border-b border-slate-200">
            <span class="h-2 w-2 rounded-full bg-emerald-600"></span>
            <strong class="text-slate-900">${escapeHtml(hosp.name || 'Coordinating Hospital')}</strong>
          </div>
          <div class="text-slate-600">
            <div><strong>Address:</strong> ${escapeHtml(hosp.address || 'Facility Address')}</div>
            <div><strong>Contact:</strong> ${escapeHtml(hosp.contact_number || hosp.contactNumber || 'Emergency Desk')}</div>
            <div class="text-[11px] text-slate-500 font-mono mt-1 pt-1 border-t border-slate-100">
              ${hospLat.toFixed(4)}°N, ${hospLng.toFixed(4)}°E
            </div>
          </div>
        </div>
      `;

      if (this.hospitalMarker) {
        // Reuse existing marker instance
        this.hospitalMarker.setLatLng([hospLat, hospLng]);
        const popup = this.hospitalMarker.getPopup();
        if (popup) {
          popup.setContent(hospPopupContent);
        } else {
          this.hospitalMarker.bindPopup(hospPopupContent);
        }
      } else {
        const hospDivIcon = window.L.divIcon({
          className: 'sirensync-hosp-marker-icon',
          html: `
            <div class="relative flex items-center justify-center cursor-pointer" style="width: 36px; height: 36px;">
              <div class="h-9 w-9 rounded-full bg-emerald-600 text-white shadow-lg border-2 border-white flex items-center justify-center">
                <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v4h4a1 1 0 110 2h-4v4a1 1 0 11-2 0v-4H5a1 1 0 110-2h4V4a1 1 0 011-1z" clip-rule="evenodd" />
                </svg>
              </div>
            </div>
          `,
          iconSize: [36, 36],
          iconAnchor: [18, 18],
          popupAnchor: [0, -18],
        });

        this.hospitalMarker = window.L.marker([hospLat, hospLng], {
          icon: hospDivIcon,
          title: hosp.name || 'Hospital',
          zIndexOffset: 500,
        }).addTo(this.map);

        this.hospitalMarker.bindPopup(hospPopupContent);
        this.hospitalMarker.bindTooltip(
          escapeHtml(hosp.name || 'Hospital'),
          { direction: 'top', offset: [0, -18], permanent: false }
        );
      }
    } else if (this.hospitalMarker) {
      this.map.removeLayer(this.hospitalMarker);
      this.hospitalMarker = null;
    }

    // 5. Update Direct Transit Polyline
    if (hasAmbCoords && hasHospCoords) {
      const latlngs = [
        [ambLat, ambLng],
        [hospLat, hospLng],
      ];
      if (this.routePolyline) {
        this.routePolyline.setLatLngs(latlngs);
      } else {
        this.routePolyline = window.L.polyline(latlngs, {
          color: '#6366f1',
          weight: 3,
          dashArray: '6, 8',
          opacity: 0.8,
        }).addTo(this.map);
      }
    } else if (this.routePolyline) {
      this.map.removeLayer(this.routePolyline);
      this.routePolyline = null;
    }

    // 6. Viewport Management (Strictly Avoid Unnecessary Automatic Zooming)
    const ambulanceChanged = amb?.id && amb.id !== this.currentAmbulanceId;
    const hospitalChanged = hosp?.id !== this.currentHospitalId;

    if (ambulanceChanged || hospitalChanged || !this.hasInitialBounds) {
      this.currentAmbulanceId = amb?.id || null;
      this.currentHospitalId = hosp?.id || null;

      if (hasAmbCoords && hasHospCoords) {
        // Adjust bounds to frame both ambulance and destination hospital
        const bounds = window.L.latLngBounds([
          [ambLat, ambLng],
          [hospLat, hospLng],
        ]);
        this.map.fitBounds(bounds, { padding: [45, 45], maxZoom: 15 });
        this.hasInitialBounds = true;
      } else if (hasAmbCoords) {
        this.map.setView([ambLat, ambLng], 14);
        this.hasInitialBounds = true;
      }
    } else if (hasAmbCoords) {
      // Routine location update: only pan if vehicle leaves current visible viewport
      const currentBounds = this.map.getBounds();
      if (!currentBounds.contains([ambLat, ambLng])) {
        this.map.panTo([ambLat, ambLng]);
      }
    }
  }
}
