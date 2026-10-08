# SirenSync — Deterministic 4-Factor Hospital Ranking Algorithm

**Subsystem:** Hospital Intelligence + Bed Management  
**Author:** Samriddhi (EquiMed Team)  
**Configuration File:** `backend/config.py`  
**Service Implementation:** `backend/services/ranking_service.py`

---

## 1. Overview & Objectives

In an emergency healthcare system, transporting a patient to the "nearest" hospital often leads to secondary transfers if the hospital lacks required clinical facilities (e.g. Cath Lab for cardiac arrest, neuro-trauma suite for craniotomy).

SirenSync replaces distance-only selection with a **deterministic, explainable 4-factor ranking algorithm**:

$$Score = w_{\text{dist}} \cdot S_{\text{dist}} + w_{\text{cap}} \cdot S_{\text{cap}} + w_{\text{traffic}} \cdot S_{\text{traffic}} + w_{\text{bed}} \cdot S_{\text{bed}}$$

All individual component scores $S \in [0.0, 1.0]$. The final composite score is bounded in $[0.0, 1.0]$.

---

## 2. Configurable Weights

The default weights prioritize clinical capability and proximity, with live traffic and bed availability acting as operational modifiers:

| Factor | Weight Variable | Default Weight | Rationale |
|---|---|---|---|
| **Capability Match** | `WEIGHT_CAPABILITY` | `0.35` | Prevents deadly secondary transfers due to lack of facilities |
| **Geographic Distance** | `WEIGHT_DISTANCE` | `0.30` | Minimizes physical transit distance |
| **Live Traffic Factor** | `WEIGHT_TRAFFIC` | `0.20` | Penalizes severely congested corridors |
| **Bed Availability** | `WEIGHT_BED_AVAILABILITY` | `0.15` | Ensures receiving facility has active bed buffers |

Weights are fully configurable via `.env` or `backend/config.py`. Their sum must equal `1.0`.

---

## 3. Factor Formulations & Normalization

### Factor 1: Distance ($S_{\text{dist}}$)
Distance between patient coordinates $(\phi_1, \lambda_1)$ and hospital coordinates $(\phi_2, \lambda_2)$ is computed using the Great Circle Haversine formula (Earth radius $R = 6,371.0\text{ km}$):

$$d = 2 R \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)}\right)$$

The normalized score is:

$$S_{\text{dist}} = \max\left(0.0, 1.0 - \frac{d}{\text{MAX\_RANKING\_RADIUS\_KM}}\right)$$

Where `MAX_RANKING_RADIUS_KM` defaults to `30.0 km`.

### Factor 2: Capability Match ($S_{\text{cap}}$)
Clinical specializations requested by the intake module (e.g., `CARDIAC_CATH_LAB`, `ICU_VENTILATOR`, `TRAUMA_LEVEL_1`) are evaluated against the hospital's registered capabilities:

$$S_{\text{cap}} = \frac{|\text{Hospital Capabilities} \cap \text{Required Capabilities}|}{|\text{Required Capabilities}|}$$

If no specific capabilities are requested, $S_{\text{cap}} = 1.0$.

**Hard Ineligibility Rule:** If an incoming emergency is classified as `P1_CRITICAL` and the candidate hospital lacks one or more required clinical capabilities, the hospital is flagged with `isEligible = False`.

### Factor 3: Live Traffic Factor ($S_{\text{traffic}}$)
Obtained via the pluggable `ITrafficProvider`.  
The default implementation is `MockTrafficProvider`, which provides deterministic, zero-credential transit delay factors $C \ge 1.0$ (where $1.0 = \text{no delay}$, $1.35 = +35\%\text{ delay}$):

$$S_{\text{traffic}} = \frac{1.0}{C}$$

### Factor 4: Bed Availability ($S_{\text{bed}}$)
Evaluates currently available beds in the requested bed category (`ICU`, `TRAUMA_EMERGENCY`, `OXYGEN_HDU`, `GENERAL_WARD`, `PEDIATRIC_ICU`):

$$S_{\text{bed}} = \min\left(1.0, \frac{\text{Available Beds in Requested Category}}{5.0}\right)$$

A buffer of 5 available beds achieves a maximum score of `1.0`.

**Zero Bed Ineligibility Rule:** If a candidate hospital has `0` available beds in the requested category, $S_{\text{bed}} = 0.0$ and `isEligible` is set to `False`.

---

## 4. Deterministic Sorting & Tie-Breaking

Candidate hospitals are sorted by:
1. `isEligible` (Eligible hospitals always precede ineligible hospitals)
2. `compositeScore` (Descending)
3. `capabilityMatchScore` (Descending tie-breaker)
4. `distanceKm` (Ascending tie-breaker — closer is preferred)
5. `hospitalId` (Deterministic lexicographical tie-breaker)

---

## 5. Explainability Breakdown Structure

Every item in `RankedHospitalsResponse` includes a transparent `breakdown` object:
```json
{
  "distanceKm": 4.82,
  "distanceScore": 0.839,
  "capabilityMatchScore": 1.0,
  "matchedCapabilities": ["CARDIAC_CATH_LAB", "ICU_VENTILATOR"],
  "missingCapabilities": [],
  "trafficCongestionFactor": 1.15,
  "trafficScore": 0.87,
  "bedAvailabilityScore": 0.8,
  "availableBedsCount": 4,
  "explanation": "Distance: 4.82 km (score: 0.84). Capability Match: 100% (2/2 matched). Traffic: Moderate arterial traffic (+15% delay) (delay factor: 1.15). Bed Availability: 4 ICU beds available."
}
```
This enables Shambhavi's Patient UI to clearly display **why** a hospital was recommended.
