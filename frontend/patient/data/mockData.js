/**
 * SirenSync - Patient Portal Mock Data (Phase 2 Prototype)
 * Isolated mock data store ready for Phase 3 API replacement.
 */

export const initialPatientProfile = {
  id: "PAT-88219",
  name: "Aarav Sharma",
  age: 29,
  gender: "Male",
  phone: "+91 98765 43210",
  bloodGroup: "O+",
  emergencyContact: {
    name: "Dr. Sunita Sharma (Mother)",
    relation: "Mother",
    phone: "+91 94120 54321"
  },
  knownAllergies: ["Penicillin", "Sulfa drugs"],
  medicalConditions: ["Mild Asthma", "No prior cardiac history"],
  insuranceProvider: "Ayushman Bharat / Star Health",
  currentLocation: {
    address: "Astley Hall, Rajpur Road, Dehradun, Uttarakhand",
    city: "Dehradun",
    state: "Uttarakhand",
    pincode: "248001",
    coordinates: {
      lat: 30.3256,
      lng: 78.0437
    },
    accuracy: "GPS Lock ±6m"
  }
};

export const emergencyTypes = [
  { id: "accident", label: "Accident", icon: "Car", desc: "Vehicle crash, pedestrian collision, fall, injury" },
  { id: "medical", label: "Medical Emergency", icon: "HeartPulse", desc: "Chest pain, stroke, seizure, severe symptoms" },
  { id: "breathing", label: "Breathing Difficulty", icon: "Wind", desc: "Asthma, choking, severe breathlessness" },
  { id: "unconscious", label: "Unconscious Person", icon: "AlertCircle", desc: "Fainted, unresponsive, coma" },
  { id: "other", label: "Other", icon: "PlusCircle", desc: "Other acute emergency condition" }
];

export const whoNeedsHelpOptions = [
  { id: "me", label: "Me", sublabel: "I am the injured patient" },
  { id: "someone_else", label: "Someone else", sublabel: "Helping another person at the scene" }
];

export const patientConditionOptions = [
  { id: "conscious", label: "Conscious", desc: "Alert or responding" },
  { id: "unconscious", label: "Unconscious", desc: "Not responding to voice or touch" },
  { id: "not_sure", label: "Not sure", desc: "Unable to determine safely" }
];

export const severityLevels = [
  {
    level: "Critical",
    color: "#dc2626",
    badgeClass: "badge-critical",
    description: "Immediate life threat — zero dispatch delay required",
    etaTolerance: "< 12 min"
  },
  {
    level: "High",
    color: "#ea580c",
    badgeClass: "badge-high",
    description: "Urgent emergency requiring immediate clinical intervention",
    etaTolerance: "< 20 min"
  },
  {
    level: "Moderate",
    color: "#ca8a04",
    badgeClass: "badge-moderate",
    description: "Serious condition requiring medical escort and bed reservation",
    etaTolerance: "< 35 min"
  }
];

export const mockHospitals = [
  {
    id: "hosp-max-ddn",
    name: "Max Super Speciality Hospital",
    address: "Mussoorie Diversion Road, Malsi, Dehradun",
    distanceKm: 4.2,
    etaMinutes: 11,
    specialization: "Emergency Care & Advanced Cath Lab",
    specializationsList: ["Emergency Care", "Cardiology", "Neuro Trauma", "Level-1 ICU"],
    availableBeds: {
      icu: 3,
      emergency: 8,
      total: 11
    },
    trafficCondition: "Moderate traffic",
    trafficLevel: "moderate",
    trafficRouteDetail: "Clear via Rajpur Rd; Green corridor corridor possible with Smart Traffic lights",
    recommendationScore: 94,
    isRecommended: true,
    rating: 4.8,
    doctorOnDuty: "Dr. V. Singhal (Chief Emergency Physician)",
    contactNumber: "+91 135 667 3000",
    ambulanceUnitsAvailable: 3,
    recommendationReason: "AI Ranked #1: Fastest ETA (11 min) with verified Cath Lab availability matching patient triage."
  },
  {
    id: "hosp-synergy",
    name: "Synergy Institute of Medical Sciences",
    address: "Canal Road, Ballupur Chowk, Dehradun",
    distanceKm: 6.1,
    etaMinutes: 14,
    specialization: "Cardiology & Intensive Critical Care",
    specializationsList: ["Cardiology", "Critical Care", "Vascular Surgery"],
    availableBeds: {
      icu: 5,
      emergency: 12,
      total: 17
    },
    trafficCondition: "Low traffic",
    trafficLevel: "low",
    trafficRouteDetail: "Express transit via Canal Road; minimal congestion",
    recommendationScore: 87,
    isRecommended: false,
    rating: 4.6,
    doctorOnDuty: "Dr. Amit Nautiyal (Emergency Lead)",
    contactNumber: "+91 135 222 6000",
    ambulanceUnitsAvailable: 4,
    recommendationReason: "High ICU bed reserve (5 beds) & steady flow route with Low Traffic."
  },
  {
    id: "hosp-cmi",
    name: "Combined Medical Institute (CMI Hospital)",
    address: "Haridwar Road, Dharampur, Dehradun",
    distanceKm: 5.4,
    etaMinutes: 16,
    specialization: "Trauma Care & Orthopaedic Emergency",
    specializationsList: ["Trauma Care", "Orthopaedics", "Emergency Surgery"],
    availableBeds: {
      icu: 2,
      emergency: 6,
      total: 8
    },
    trafficCondition: "Moderate traffic",
    trafficLevel: "moderate",
    trafficRouteDetail: "Moderate flow around Prince Chowk bypass",
    recommendationScore: 81,
    isRecommended: false,
    rating: 4.4,
    doctorOnDuty: "Dr. R. K. Joshi (Trauma Specialist)",
    contactNumber: "+91 135 265 4700",
    ambulanceUnitsAvailable: 2,
    recommendationReason: "Optimal backup facility for surgical & polytrauma emergencies."
  },
  {
    id: "hosp-aiims-rishikesh",
    name: "Government Doon Medical College Hospital",
    address: "Parade Ground, Dehradun",
    distanceKm: 8.4,
    etaMinutes: 19,
    specialization: "General Emergency & Multi-Trauma Center",
    specializationsList: ["Trauma Center", "Emergency Medicine", "Burns Unit"],
    availableBeds: {
      icu: 2,
      emergency: 15,
      total: 17
    },
    trafficCondition: "High traffic",
    trafficLevel: "high",
    trafficRouteDetail: "Heavy rush near Clock Tower intersection; rerouting recommended",
    recommendationScore: 72,
    isRecommended: false,
    rating: 4.2,
    doctorOnDuty: "Dr. N. Rawat (CMO on Emergency Duty)",
    contactNumber: "+91 135 271 2100",
    ambulanceUnitsAvailable: 1,
    recommendationReason: "Government tertiary hospital with highest bed volume, but longer ETA due to traffic."
  }
];

export const quickScenarios = [
  {
    name: "Cardiac Emergency",
    patientName: "Aarav Sharma",
    age: 29,
    contactNumber: "+91 98765 43210",
    location: "Astley Hall, Rajpur Road, Dehradun, Uttarakhand",
    emergencyType: "Cardiac Emergency",
    symptoms: "Sudden sharp substernal chest pressure radiating to left shoulder and jaw; profuse sweating and shortness of breath.",
    severity: "Critical"
  },
  {
    name: "Road Accident Trauma",
    patientName: "Rohit Negi",
    age: 34,
    contactNumber: "+91 94111 88200",
    location: "Clock Tower Chowk, Dehradun, Uttarakhand",
    emergencyType: "Accident",
    symptoms: "Two-wheeler collision impact, deep laceration on right forearm with active bleeding, suspected left clavicle fracture.",
    severity: "High"
  },
  {
    name: "Acute Asthma / Breathing",
    patientName: "Meera Sen",
    age: 24,
    contactNumber: "+91 98970 33412",
    location: "Jakhan, Rajpur Road, Dehradun, Uttarakhand",
    emergencyType: "Breathing Problem",
    symptoms: "Severe respiratory distress, wheezing, inhaler non-responsive, oxygen saturation feeling low.",
    severity: "Critical"
  }
];

export const defaultTimelineSteps = [
  {
    id: 1,
    title: "Emergency Request Created",
    status: "completed",
    timestamp: "10:48:02 AM",
    description: "Triage request received and telemetry logged in SirenSync network."
  },
  {
    id: 2,
    title: "Hospitals Ranked",
    status: "completed",
    timestamp: "10:48:15 AM",
    description: "AI evaluated distance, bed availability, trauma tier, and traffic congestion."
  },
  {
    id: 3,
    title: "Hospital Selected",
    status: "completed",
    timestamp: "10:48:40 AM",
    description: "Patient confirmed final hospital destination. Facility alerted."
  },
  {
    id: 4,
    title: "Ambulance Coordination",
    status: "active",
    timestamp: "In Progress",
    description: "Assigning closest advanced life support (ALS) unit and alerting traffic signals."
  },
  {
    id: 5,
    title: "Ambulance Dispatched",
    status: "pending",
    timestamp: "Pending",
    description: "Unit UK-07-EA-4412 will mobilize with dual emergency medics on board."
  },
  {
    id: 6,
    title: "Ambulance En Route",
    status: "pending",
    timestamp: "Pending",
    description: "Real-time green light wave synchronization activated on corridor."
  },
  {
    id: 7,
    title: "Arrived at Hospital",
    status: "pending",
    timestamp: "Pending",
    description: "Emergency room bay prepped and handoff initiated."
  }
];

export const mockAssignedAmbulance = {
  unitId: "ALS-UK-07-4412",
  type: "Advanced Life Support (ALS) Ambulance",
  baseStation: "Max Hospital Emergency Depo, Dehradun",
  driverName: "Rajesh Kumar (Grade 1 EMS Driver)",
  paramedic: "Dr. Priya Verma (Emergency Med Tech)",
  phone: "+91 94120 12345",
  equipment: ["Cardiac Defibrillator", "Oxygen Resuscitator", "Telemetry Monitor", "IV Infusion"],
  liveEtaMin: 7
};
