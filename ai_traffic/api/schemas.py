"""
Fixed Pydantic Event and API Schemas for SirenSync.
Standardized across Patient Intake, Hospital Ranking, Ambulance Coordination, and Green Corridor.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SignalStateEnum(str, Enum):
    RED = "RED"
    GREEN = "GREEN"
    HOLD = "HOLD"
    YELLOW = "YELLOW"


class EmergencySeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MODERATE = "MODERATE"


# ==============================================================================
# FIXED EVENT SCHEMAS (Broadcasted via WebSocket and recorded to SQLite)
# ==============================================================================

class AmbulanceDetectedEvent(BaseModel):
    """
    Emitted when YOLO or the fallback heuristic identifies an emergency ambulance on a junction camera.
    """
    event_type: str = "AMBULANCE_DETECTED"
    camera_id: str
    junction_id: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    bounding_box: Optional[List[int]] = None  # [x1, y1, x2, y2]
    heuristic_used: bool = False
    consecutive_frames: int = 1
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SignalChangedEvent(BaseModel):
    """
    Emitted when a traffic signal phase transitions (e.g. RED -> GREEN on approach).
    """
    event_type: str = "SIGNAL_CHANGED"
    junction_id: str
    previous_state: str
    state: str
    reason: str
    ambulance_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConflictDetectedEvent(BaseModel):
    """
    Emitted when two or more ambulances approach the same junction concurrently.
    """
    event_type: str = "CONFLICT_DETECTED"
    junction_id: str
    ambulance_ids: List[str]
    prioritized_ambulance: str
    reason: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RouteUpdatedEvent(BaseModel):
    """
    Emitted when ambulance location or transit progress updates along a corridor.
    """
    event_type: str = "ROUTE_UPDATED"
    ambulance_id: str
    progress_percent: float
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    next_junction_id: Optional[str] = None
    status: str = "ACTIVE"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ==============================================================================
# REST API REQUEST AND RESPONSE SCHEMAS
# ==============================================================================

class RoutePoint(BaseModel):
    lat: float
    lng: float
    speed_kmh: Optional[float] = None


class RouteInputRequest(BaseModel):
    """
    Accepted by POST /route from the upstream ambulance-routing module.
    """
    ambulance_id: str
    route_points: Optional[List[RoutePoint]] = None
    junctions: List[str] = Field(default_factory=list, description="Ordered list of junction IDs on path")
    progress_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    emergency_severity: str = Field(default="CRITICAL", description="CRITICAL, HIGH, or MODERATE")

    # Optional origin/destination for Google Maps Directions lookup
    origin: Optional[str] = None        # e.g., "12.9650,77.5850"
    destination: Optional[str] = None   # e.g., "12.9850,77.6150"


class RouteProgressUpdateRequest(BaseModel):
    ambulance_id: str
    progress_percent: float = Field(..., ge=0.0, le=100.0)
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None


class JunctionStatusResponse(BaseModel):
    junction_id: str
    name: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    state: str
    active_ambulance_id: Optional[str] = None
    reason: Optional[str] = None
    seconds_in_state: Optional[float] = None
    last_event_time: Optional[str] = None
    queued_ambulances: List[str] = Field(default_factory=list)


class CameraStatusItem(BaseModel):
    camera_id: str
    junction_id: str
    url: str
    status: str
    is_simulated: bool


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    controller_type: str
    controller_info: Dict[str, Any]
    cameras: Dict[str, CameraStatusItem]
    detector_custom_weights_loaded: bool
    active_routes_count: int
    timestamp: str
