import math
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from backend.config import settings
from backend.models.hospital import Hospital
from backend.models.bed import Bed
from backend.models.enums import BedStatusEnum, BedTypeEnum, PriorityEnum
from backend.schemas.ranking import (
    RankingRequest,
    RankedHospitalItem,
    RankedHospitalsResponse,
    RankingBreakdown,
)
from backend.schemas.bed import BedCategoryCount
from backend.services.traffic_provider import ITrafficProvider, default_traffic_provider
from backend.shared.contracts import CoordinatesContract

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes Great Circle distance between two points in kilometers.
    Earth radius: 6,371.0 km.
    """
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r * c, 2)

class HospitalRankingEngine:
    """
    Deterministic, explainable 4-factor hospital ranking engine.
    Factors:
      1. Distance (Geographic proximity via Haversine)
      2. Capability Match (Required clinical specializations vs hospital profile)
      3. Live Traffic Factor (Transit delay multiplier via MockTrafficProvider)
      4. Bed Availability (Available beds in requested category)
    """

    def __init__(self, traffic_provider: ITrafficProvider = default_traffic_provider):
        self.traffic_provider = traffic_provider

    def rank_hospitals(self, db: Session, request: RankingRequest) -> RankedHospitalsResponse:
        # Step 1: Query all active hospitals with their capabilities and beds
        hospitals = db.query(Hospital).filter(Hospital.is_active == True).all()

        evaluated_items: List[RankedHospitalItem] = []

        w_dist = settings.WEIGHT_DISTANCE
        w_cap = settings.WEIGHT_CAPABILITY
        w_traffic = settings.WEIGHT_TRAFFIC
        w_bed = settings.WEIGHT_BED_AVAILABILITY

        p_lat = request.patientLocation.latitude
        p_lng = request.patientLocation.longitude

        for hospital in hospitals:
            # 1. Distance Calculation
            dist_km = calculate_haversine_distance(p_lat, p_lng, hospital.latitude, hospital.longitude)
            if dist_km > settings.MAX_RANKING_RADIUS_KM:
                s_dist = 0.0
            else:
                s_dist = max(0.0, 1.0 - (dist_km / settings.MAX_RANKING_RADIUS_KM))

            # 2. Capability Matching
            hospital_caps = {c.capability_code for c in hospital.capabilities}
            req_caps = set(request.requiredCapabilities)

            if req_caps:
                matched_caps = sorted(list(req_caps.intersection(hospital_caps)))
                missing_caps = sorted(list(req_caps.difference(hospital_caps)))
                s_cap = len(matched_caps) / len(req_caps)
            else:
                matched_caps = []
                missing_caps = []
                s_cap = 1.0

            # 3. Traffic Factor
            congestion_factor, traffic_desc = self.traffic_provider.get_traffic_factor(
                p_lat, p_lng, hospital.latitude, hospital.longitude
            )
            s_traffic = 1.0 / congestion_factor

            # 4. Bed Availability Summary
            bed_counts_by_cat: Dict[str, BedCategoryCount] = {}
            for bt in BedTypeEnum:
                bed_counts_by_cat[bt.value] = BedCategoryCount(available=0, reserved=0, occupied=0, total=0)

            for bed in hospital.beds:
                btype = bed.bed_type.value
                bed_counts_by_cat[btype].total += 1
                if bed.status == BedStatusEnum.AVAILABLE:
                    bed_counts_by_cat[btype].available += 1
                elif bed.status == BedStatusEnum.RESERVED:
                    bed_counts_by_cat[btype].reserved += 1
                elif bed.status == BedStatusEnum.OCCUPIED:
                    bed_counts_by_cat[btype].occupied += 1

            requested_cat = request.requiredBedType.value
            available_beds = bed_counts_by_cat[requested_cat].available

            # S_bed scales with available beds up to a buffer threshold of 5 beds
            s_bed = min(1.0, available_beds / 5.0)

            # Eligibility assessment:
            # Must have at least 1 available bed in the requested category
            # and critical priorities (P1) cannot tolerate 0% capability match
            is_eligible = True
            eligibility_notes = []

            if available_beds == 0:
                is_eligible = False
                eligibility_notes.append(f"No available {requested_cat} beds.")

            if req_caps and len(missing_caps) > 0 and request.priority == PriorityEnum.P1_CRITICAL:
                is_eligible = False
                eligibility_notes.append(f"Missing critical capability: {', '.join(missing_caps)}.")

            # Weighted composite score
            composite = (w_dist * s_dist) + (w_cap * s_cap) + (w_traffic * s_traffic) + (w_bed * s_bed)
            composite_score = round(composite, 3)

            # Build explainable narrative
            explanation_parts = [
                f"Distance: {dist_km} km (score: {round(s_dist, 2)}).",
                f"Capability Match: {int(s_cap * 100)}% ({len(matched_caps)}/{len(req_caps)} matched).",
                f"Traffic: {traffic_desc} (delay factor: {congestion_factor}).",
                f"Bed Availability: {available_beds} {requested_cat} beds available."
            ]
            if eligibility_notes:
                explanation_parts.append(f"Eligibility Issue: {' '.join(eligibility_notes)}")

            breakdown = RankingBreakdown(
                distanceKm=dist_km,
                distanceScore=round(s_dist, 3),
                capabilityMatchScore=round(s_cap, 3),
                matchedCapabilities=matched_caps,
                missingCapabilities=missing_caps,
                trafficCongestionFactor=round(congestion_factor, 2),
                trafficScore=round(s_traffic, 3),
                bedAvailabilityScore=round(s_bed, 3),
                availableBedsCount=available_beds,
                explanation=" ".join(explanation_parts)
            )

            evaluated_items.append(
                RankedHospitalItem(
                    hospitalId=hospital.id,
                    name=hospital.name,
                    location=CoordinatesContract(
                        latitude=hospital.latitude,
                        longitude=hospital.longitude,
                        address=hospital.address
                    ),
                    contactNumber=hospital.contact_number,
                    compositeScore=composite_score,
                    rank=0, # populated after sorting
                    isEligible=is_eligible,
                    breakdown=breakdown,
                    bedSummary=bed_counts_by_cat
                )
            )

        # Deterministic sorting:
        # 1. Eligible hospitals first (isEligible == True)
        # 2. Highest composite score
        # 3. Higher capability score (tie breaker)
        # 4. Shorter distance (tie breaker)
        # 5. Deterministic hospital_id (tie breaker)
        evaluated_items.sort(
            key=lambda x: (
                1 if x.isEligible else 0,
                x.compositeScore,
                x.breakdown.capabilityMatchScore,
                -x.breakdown.distanceKm,
                x.hospitalId
            ),
            reverse=True
        )

        for idx, item in enumerate(evaluated_items):
            item.rank = idx + 1

        eligible_count = sum(1 for x in evaluated_items if x.isEligible)

        return RankedHospitalsResponse(
            emergencyId=request.emergencyId,
            rankedHospitals=evaluated_items,
            weightsApplied={
                "distance": w_dist,
                "capability": w_cap,
                "traffic": w_traffic,
                "bedAvailability": w_bed
            },
            totalHospitalsEvaluated=len(evaluated_items),
            eligibleHospitalsCount=eligible_count
        )
