/**
 * SirenSync AI Green Corridor Command Center Dashboard.
 * Connects WebSocket telemetry, Google Maps JavaScript API, camera feeds,
 * and junction signal state visualization.
 */

let clientConfig = null;
let googleMap = null;
let trafficLayer = null;
let junctionMarkers = {};
let ambulanceMarker = null;
let routePolyline = null;
let ws = null;
let eventsCount = 0;

// ==============================================================================
// INITIALIZATION
// ==============================================================================

document.addEventListener("DOMContentLoaded", async () => {
  await fetchClientConfig();
  setupUIEventListeners();
  initWebSocket();
  pollInitialJunctions();
});

async function fetchClientConfig() {
  try {
    const res = await fetch("/api/config");
    clientConfig = await res.json();

    // Update Controller Badge
    const ctrlBadge = document.getElementById("controller-badge-text");
    if (clientConfig.signal_controller_type === "real") {
      ctrlBadge.innerText = "CONTROLLER: REAL TMC GATEWAY";
      document.getElementById("controller-badge").classList.remove("badge-simulated");
      document.getElementById("controller-badge").classList.add("badge-connected");
    } else {
      ctrlBadge.innerText = "CONTROLLER: SIMULATED (Zero Hardware)";
    }

    // Populate camera selector if configured
    const camSelect = document.getElementById("camera-select");
    if (clientConfig.cameras && clientConfig.cameras.length > 0) {
      camSelect.innerHTML = "";
      clientConfig.cameras.forEach(cam => {
        const opt = document.createElement("option");
        opt.value = cam.camera_id;
        opt.innerText = `${cam.name} (${cam.camera_id})`;
        camSelect.appendChild(opt);
      });
    }

    // Load Google Maps or Fallback View
    if (clientConfig.google_maps_api_key && clientConfig.google_maps_api_key !== "YOUR_GOOGLE_MAPS_API_KEY_HERE") {
      loadGoogleMapsScript(clientConfig.google_maps_api_key);
    } else {
      renderSvgFallbackMap();
    }
  } catch (err) {
    console.error("Failed to load client config:", err);
    renderSvgFallbackMap();
  }
}

function setupUIEventListeners() {
  // Camera dropdown change
  const camSelect = document.getElementById("camera-select");
  camSelect.addEventListener("change", (e) => {
    const camId = e.target.value;
    const img = document.getElementById("mjpeg-stream");
    img.src = `/video_feed/${camId}`;

    const camData = clientConfig?.cameras?.find(c => c.camera_id === camId);
    const tag = document.getElementById("video-feed-tag");
    tag.innerText = (camData && !camData.is_simulated) ? "LIVE RTSP FEED" : "SIMULATED FEED";
  });

  // Inject ambulance into camera
  document.getElementById("btn-trigger-amb-cam").addEventListener("click", async () => {
    const camId = camSelect.value;
    try {
      await fetch(`/demo/trigger_camera/${camId}`, { method: "POST" });
      addEventToLog("MANUAL_ACTION", `Ambulance dispatched on camera ${camId}`);
    } catch (e) {
      console.error(e);
    }
  });

  // Dispatch full demo corridor
  document.getElementById("btn-dispatch-demo").addEventListener("click", async () => {
    try {
      const res = await fetch("/demo/simulate", { method: "POST" });
      const data = await res.json();
      addEventToLog("DEMO_DISPATCH", data.message);
      // Start simulated ambulance movement on map
      simulateAmbulanceTransit();
    } catch (e) {
      console.error(e);
    }
  });

  // Reset signals
  document.getElementById("btn-reset-signals").addEventListener("click", async () => {
    if (clientConfig && clientConfig.junctions) {
      for (const j of clientConfig.junctions) {
        await fetch(`/signals/manual_override?junction_id=${j.junction_id}&state=RED`, { method: "POST" });
      }
      addEventToLog("MANUAL_ACTION", "All corridor signals reset to RED.");
      pollInitialJunctions();
    }
  });

  // Traffic layer toggle
  document.getElementById("toggle-traffic").addEventListener("change", (e) => {
    if (trafficLayer && googleMap) {
      trafficLayer.setMap(e.target.checked ? googleMap : null);
    }
  });
}

// ==============================================================================
// WEBSOCKET TELEMETRY
// ==============================================================================

function initWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/events`;
  const wsBadge = document.getElementById("ws-status-text");

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    wsBadge.innerText = "WS: CONNECTED";
    document.getElementById("ws-badge").classList.add("badge-connected");
  };

  ws.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      handleIncomingEvent(payload);
    } catch (err) {
      console.error("WS Parse error:", err);
    }
  };

  ws.onclose = () => {
    wsBadge.innerText = "WS: RECONNECTING...";
    document.getElementById("ws-badge").classList.remove("badge-connected");
    setTimeout(initWebSocket, 3000);
  };
}

function handleIncomingEvent(evt) {
  const eventType = evt.event_type || "UNKNOWN";

  if (eventType === "SIGNAL_CHANGED") {
    updateJunctionStateUI(evt.junction_id, evt.state, evt.reason, evt.ambulance_id);
    addEventToLog(
      "SIGNAL_CHANGED",
      `Junction ${evt.junction_id}: ${evt.previous_state} -> ${evt.state} (${evt.reason})`
    );
  } else if (eventType === "AMBULANCE_DETECTED") {
    addEventToLog(
      "AMBULANCE_DETECTED",
      `Camera ${evt.camera_id} confirmed emergency ambulance (${Math.round(evt.confidence * 100)}%)`
    );
  } else if (eventType === "ROUTE_UPDATED") {
    updateAmbulanceRouteUI(evt);
    addEventToLog(
      "ROUTE_UPDATED",
      `Ambulance ${evt.ambulance_id} at ${evt.progress_percent}% progress. Next: ${evt.next_junction_id || 'Cleared'}`
    );
  } else if (eventType === "CONFLICT_DETECTED") {
    addEventToLog(
      "CONFLICT_DETECTED",
      `CONFLICT at ${evt.junction_id}! Servicing: ${evt.prioritized_ambulance}. Queued: ${evt.ambulance_ids.join(', ')}`
    );
  }
}

// ==============================================================================
// JUNCTION UI & STATE
// ==============================================================================

async function pollInitialJunctions() {
  try {
    const res = await fetch("/junctions");
    const junctions = await res.json();
    renderJunctionsList(junctions);
  } catch (err) {
    console.error("Failed to fetch junctions:", err);
  }
}

function renderJunctionsList(junctions) {
  const listEl = document.getElementById("junctions-list");
  listEl.innerHTML = "";

  junctions.forEach(j => {
    const card = document.createElement("div");
    card.id = `jcard-${j.junction_id}`;
    card.className = `junction-card ${j.state === 'GREEN' ? 'active-corridor' : ''}`;

    card.innerHTML = `
      <div class="j-info">
        <h4>${j.name || j.junction_id}</h4>
        <p>ID: ${j.junction_id} | ${j.reason || 'Normal cycle'}</p>
      </div>
      <div class="j-signal">
        <span id="jpill-${j.junction_id}" class="signal-pill ${j.state}">${j.state}</span>
      </div>
    `;
    listEl.appendChild(card);

    // Update map marker if map active
    updateMapMarkerSignal(j.junction_id, j.state);
  });
}

function updateJunctionStateUI(junctionId, state, reason, ambulanceId) {
  const pill = document.getElementById(`jpill-${junctionId}`);
  if (pill) {
    pill.className = `signal-pill ${state}`;
    pill.innerText = state;
  }

  const card = document.getElementById(`jcard-${junctionId}`);
  if (card) {
    if (state === "GREEN" || state === "HOLD") {
      card.classList.add("active-corridor");
    } else {
      card.classList.remove("active-corridor");
    }
  }

  updateMapMarkerSignal(junctionId, state);
}

function updateAmbulanceRouteUI(evt) {
  document.getElementById("active-amb-id").innerText = evt.ambulance_id || "None";
  document.getElementById("active-amb-status").innerText = evt.status || "In Transit";
  document.getElementById("active-amb-percent").innerText = `${Math.round(evt.progress_percent)}%`;
  document.getElementById("route-progress-fill").style.width = `${evt.progress_percent}%`;

  if (googleMap && ambulanceMarker && evt.current_lat && evt.current_lng) {
    ambulanceMarker.setPosition({ lat: evt.current_lat, lng: evt.current_lng });
  }
}

function addEventToLog(type, text) {
  eventsCount++;
  document.getElementById("event-counter").innerText = `${eventsCount} events`;

  const container = document.getElementById("events-container");
  const row = document.createElement("div");
  row.className = "event-item";

  const timeStr = new Date().toLocaleTimeString();
  row.innerHTML = `
    <span class="event-time">${timeStr}</span>
    <span class="event-type ${type}">${type}</span>
    <span class="event-desc">${text}</span>
  `;

  container.insertBefore(row, container.firstChild);

  // Keep log capped at 60 items
  while (container.children.length > 60) {
    container.removeChild(container.lastChild);
  }
}

// ==============================================================================
// GOOGLE MAPS INTEGRATION
// ==============================================================================

function loadGoogleMapsScript(apiKey) {
  const script = document.createElement("script");
  script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&callback=initGoogleMap`;
  script.async = true;
  script.defer = true;
  window.initGoogleMap = initGoogleMap;
  document.head.appendChild(script);
}

function initGoogleMap() {
  const mapPlaceholder = document.getElementById("map-placeholder");
  if (mapPlaceholder) mapPlaceholder.style.display = "none";

  const centerCoords = { lat: 12.9758, lng: 77.6012 }; // Central Bengaluru Corridor
  googleMap = new google.maps.Map(document.getElementById("map-container"), {
    center: centerCoords,
    zoom: 14,
    styles: getDarkMapStyles(),
    disableDefaultUI: false,
    zoomControl: true,
  });

  // Traffic Layer
  trafficLayer = new google.maps.TrafficLayer();
  trafficLayer.setMap(googleMap);

  // Add Junction Signal Markers
  if (clientConfig && clientConfig.junctions) {
    clientConfig.junctions.forEach(j => {
      const marker = new google.maps.Marker({
        position: { lat: j.lat, lng: j.lng },
        map: googleMap,
        title: `${j.name} [${j.junction_id}]`,
        icon: createSignalIcon("RED"),
      });

      const infoWindow = new google.maps.InfoWindow({
        content: `<div style="color:#000;padding:4px;"><strong>${j.name}</strong><br/>ID: ${j.junction_id}</div>`
      });
      marker.addListener("click", () => infoWindow.open(googleMap, marker));

      junctionMarkers[j.junction_id] = marker;
    });
  }

  // Draw Initial Corridor Route Polyline
  const routePath = [
    { lat: 12.9660, lng: 77.5880 },
    { lat: 12.9716, lng: 77.5946 }, // J-101
    { lat: 12.9758, lng: 77.6012 }, // J-102
    { lat: 12.9812, lng: 77.6085 }, // J-103
  ];

  routePolyline = new google.maps.Polyline({
    path: routePath,
    geodesic: true,
    strokeColor: "#3b82f6",
    strokeOpacity: 0.8,
    strokeWeight: 5,
    map: googleMap
  });

  // Ambulance Marker
  ambulanceMarker = new google.maps.Marker({
    position: routePath[0],
    map: googleMap,
    title: "Ambulance AMB-DEMO-99",
    icon: {
      path: google.maps.SymbolPath.CIRCLE,
      scale: 9,
      fillColor: "#ef4444",
      fillOpacity: 1.0,
      strokeColor: "#ffffff",
      strokeWeight: 2,
    }
  });
}

function updateMapMarkerSignal(junctionId, state) {
  const marker = junctionMarkers[junctionId];
  if (marker && googleMap) {
    marker.setIcon(createSignalIcon(state));
  }
}

function createSignalIcon(state) {
  const color = state === "GREEN" ? "#10b981" : state === "HOLD" ? "#f59e0b" : "#ef4444";
  return {
    path: google.maps.SymbolPath.CIRCLE,
    scale: 11,
    fillColor: color,
    fillOpacity: 1,
    strokeColor: "#ffffff",
    strokeWeight: 2,
  };
}

function getDarkMapStyles() {
  return [
    { elementType: "geometry", stylers: [{ color: "#1d2c4d" }] },
    { elementType: "labels.text.fill", stylers: [{ color: "#8ec3b9" }] },
    { elementType: "labels.text.stroke", stylers: [{ color: "#1a3646" }] },
    { featureType: "road", elementType: "geometry", stylers: [{ color: "#304a7d" }] },
    { featureType: "water", elementType: "geometry", stylers: [{ color: "#0e1626" }] }
  ];
}

// ==============================================================================
// ZERO-KEY FALLBACK INTERACTIVE MAP
// ==============================================================================

function renderSvgFallbackMap() {
  const container = document.getElementById("map-container");
  container.innerHTML = `
    <div style="position:relative; width:100%; height:100%; background:#101726; overflow:hidden;">
      <svg id="corridor-svg" width="100%" height="100%" viewBox="0 0 800 500">
        <!-- City Grid Background Lines -->
        <line x1="50" y1="120" x2="750" y2="120" stroke="#1e293b" stroke-width="2"/>
        <line x1="50" y1="260" x2="750" y2="260" stroke="#1e293b" stroke-width="2"/>
        <line x1="50" y1="380" x2="750" y2="380" stroke="#1e293b" stroke-width="2"/>
        <line x1="180" y1="30" x2="180" y2="470" stroke="#1e293b" stroke-width="2"/>
        <line x1="400" y1="30" x2="400" y2="470" stroke="#1e293b" stroke-width="2"/>
        <line x1="620" y1="30" x2="620" y2="470" stroke="#1e293b" stroke-width="2"/>

        <!-- Green Corridor Main Arterial Path -->
        <path id="svg-route-path" d="M 80 420 L 220 340 L 420 230 L 680 120"
              fill="none" stroke="#2563eb" stroke-width="8" stroke-linecap="round" stroke-dasharray="8 6"/>

        <!-- Junction 1: MG Road -->
        <g id="svg-j1" transform="translate(220, 340)">
          <circle id="svg-j1-light" r="16" fill="#ef4444" stroke="#ffffff" stroke-width="2"/>
          <text x="0" y="32" fill="#94a3b8" font-size="12" text-anchor="middle" font-family="sans-serif">J-101 (MG Rd)</text>
        </g>

        <!-- Junction 2: Trinity Circle -->
        <g id="svg-j2" transform="translate(420, 230)">
          <circle id="svg-j2-light" r="16" fill="#ef4444" stroke="#ffffff" stroke-width="2"/>
          <text x="0" y="32" fill="#94a3b8" font-size="12" text-anchor="middle" font-family="sans-serif">J-102 (Trinity)</text>
        </g>

        <!-- Junction 3: Hospital Gate -->
        <g id="svg-j3" transform="translate(680, 120)">
          <circle id="svg-j3-light" r="16" fill="#ef4444" stroke="#ffffff" stroke-width="2"/>
          <text x="0" y="32" fill="#94a3b8" font-size="12" text-anchor="middle" font-family="sans-serif">J-103 (Hospital Entry)</text>
        </g>

        <!-- Moving Ambulance Entity -->
        <g id="svg-ambulance" transform="translate(80, 420)">
          <circle r="14" fill="#dc2626" stroke="#ffffff" stroke-width="2"/>
          <text x="0" y="5" fill="#ffffff" font-size="12" text-anchor="middle" font-weight="bold">🚑</text>
        </g>
      </svg>
      <div style="position:absolute; bottom:12px; left:16px; font-size:11px; color:#64748b; background:rgba(0,0,0,0.6); padding:4px 8px; border-radius:4px;">
        Vector Corridor Canvas (Set GOOGLE_MAPS_API_KEY in .env for Satellite & Traffic Tile Mode)
      </div>
    </div>
  `;
}

// Fallback visual simulation for SVG map
function simulateAmbulanceTransit() {
  const ambEl = document.getElementById("svg-ambulance");
  if (!ambEl) return;

  const steps = [
    { x: 80, y: 420, p: 0 },
    { x: 150, y: 380, p: 15 },
    { x: 220, y: 340, p: 30, j: "J-101" },
    { x: 320, y: 285, p: 50 },
    { x: 420, y: 230, p: 65, j: "J-102" },
    { x: 550, y: 175, p: 80 },
    { x: 680, y: 120, p: 100, j: "J-103" }
  ];

  let i = 0;
  const interval = setInterval(async () => {
    if (i >= steps.length) {
      clearInterval(interval);
      return;
    }
    const step = steps[i];
    ambEl.setAttribute("transform", `translate(${step.x}, ${step.y})`);

    // Report progress to server
    try {
      await fetch("/route/progress", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ambulance_id: "AMB-DEMO-99",
          progress_percent: step.p
        })
      });
    } catch (e) {}

    // Update SVG signal lights
    if (step.j === "J-101") {
      const l = document.getElementById("svg-j1-light");
      if (l) l.setAttribute("fill", "#10b981");
    } else if (step.j === "J-102") {
      const l = document.getElementById("svg-j2-light");
      if (l) l.setAttribute("fill", "#10b981");
    } else if (step.j === "J-103") {
      const l = document.getElementById("svg-j3-light");
      if (l) l.setAttribute("fill", "#10b981");
    }

    i++;
  }, 1800);
}
