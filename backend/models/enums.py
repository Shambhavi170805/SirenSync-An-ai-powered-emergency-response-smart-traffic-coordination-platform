from enum import Enum

class PriorityEnum(str, Enum):
    P1_CRITICAL = "P1_CRITICAL"       # Immediate / Resuscitation required
    P2_EMERGENCY = "P2_EMERGENCY"     # Emergent / Severe condition
    P3_URGENT = "P3_URGENT"           # Urgent condition
    P4_NON_URGENT = "P4_NON_URGENT"   # Standard / Non-urgent condition

class BedTypeEnum(str, Enum):
    ICU = "ICU"
    TRAUMA_EMERGENCY = "TRAUMA_EMERGENCY"
    OXYGEN_HDU = "OXYGEN_HDU"
    GENERAL_WARD = "GENERAL_WARD"
    PEDIATRIC_ICU = "PEDIATRIC_ICU"

class BedStatusEnum(str, Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    OCCUPIED = "OCCUPIED"
    MAINTENANCE = "MAINTENANCE"

class ReservationStatusEnum(str, Enum):
    RESERVED = "RESERVED"
    OCCUPIED = "OCCUPIED"
    RELEASED_FOR_REASSIGNMENT = "RELEASED_FOR_REASSIGNMENT"
    CANCELLED = "CANCELLED"

class QueueStatusEnum(str, Enum):
    COORDINATING = "COORDINATING"
    DISPATCHED = "DISPATCHED"
    EN_ROUTE = "EN_ROUTE"
    ARRIVED = "ARRIVED"
    REROUTED = "REROUTED"
    CANCELLED = "CANCELLED"

class AmbulanceStatusEnum(str, Enum):
    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    EN_ROUTE_PICKUP = "EN_ROUTE_PICKUP"
    PATIENT_ONBOARD = "PATIENT_ONBOARD"
    EN_ROUTE_HOSPITAL = "EN_ROUTE_HOSPITAL"
    ARRIVED = "ARRIVED"
    MAINTENANCE = "MAINTENANCE"

class AmbulanceTypeEnum(str, Enum):
    BLS = "BLS"   # Basic Life Support
    ALS = "ALS"   # Advanced Life Support
    MICU = "MICU" # Mobile Intensive Care Unit
