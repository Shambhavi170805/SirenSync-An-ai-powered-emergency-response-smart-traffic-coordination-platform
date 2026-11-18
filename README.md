# SirenSync: AI-Powered Emergency Response & Smart Traffic Coordination Platform

## Overview
SirenSync is a real-time smart emergency response system designed to streamline communication and navigation between patients, emergency medical services (EMS/ambulances), and hospitals.

### Project Architecture
- **frontend/patient/**: Patient portal for raising emergency requests, viewing hospital availability, selecting receiving facilities, and tracking status (Phase 2 Prototype).
- **backend/**: Core microservices, dispatch algorithms, traffic coordination APIs (Phase 3).
- **database/**: Data persistence models and migrations (Phase 3).

---

## Phase 2: Patient Frontend Prototype
The patient frontend is an independent, responsive, and production-grade prototype running on mock data without backend dependencies.

### Demo Flow
1. **Patient Dashboard**: Overview of profile, live location (mock Dehradun, UK), active emergency banner, quick triage guidelines.
2. **Emergency Request**: One-click emergency wizard capturing symptoms, severity (Critical / High / Moderate), emergency category, and live contact info.
3. **Hospital Recommendations**: Intelligent multi-criteria ranked hospital options with recommendation scores, ETA, specialized emergency units, available beds, and real-time traffic condition indicators.
4. **Hospital Selection**: Final conscious decision by the patient, displaying instant confirmation with unique emergency identifier (e.g. `EMG-2026-001`).
5. **Emergency Status & Timeline**: Live progress tracker reflecting end-to-end emergency response milestones from hospital acceptance to ambulance coordination.
