"""
Central Configuration Parser for SirenSync AI-Traffic Module.
Loads and validates settings from config.yaml and environment variables (.env).
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env if present
load_dotenv()


class LocationConfig(BaseModel):
    lat: float
    lng: float
    address: Optional[str] = None


class CameraConfig(BaseModel):
    camera_id: str
    name: str = "Junction Camera"
    junction_id: str
    url: str  # "demo", "0", "1", "rtsp://...", "http://..."
    is_simulated: bool = False
    reconnect_interval_seconds: float = 5.0
    max_fps: int = 25
    location: Optional[LocationConfig] = None


class JunctionConfig(BaseModel):
    junction_id: str
    name: str
    lat: float
    lng: float
    default_state: str = "RED"
    connected_cameras: List[str] = Field(default_factory=list)


class HeuristicConfig(BaseModel):
    vehicle_classes: List[int] = Field(default_factory=lambda: [2, 5, 7])
    min_flashing_variance: float = 15.0
    red_hue_range_1: List[int] = Field(default_factory=lambda: [0, 10])
    red_hue_range_2: List[int] = Field(default_factory=lambda: [170, 180])
    blue_hue_range: List[int] = Field(default_factory=lambda: [100, 130])
    min_saturation: int = 120
    min_value: int = 140


class DetectionConfig(BaseModel):
    base_model: str = "yolov10n.pt"
    custom_weights: str = "weights/yolov10n_ambulance.pt"
    confidence_threshold: float = 0.50
    iou_threshold: float = 0.45
    img_size: int = 640
    temporal_smoothing_frames: int = 4
    heuristic: HeuristicConfig = Field(default_factory=HeuristicConfig)


class SignalsConfig(BaseModel):
    safety_timeout_seconds: float = 45.0
    hold_duration_seconds: float = 8.0
    preemption_lead_time_seconds: float = 25.0
    preemption_distance_meters: float = 350.0
    yellow_clearance_seconds: float = 4.0


class ConflictConfig(BaseModel):
    strategy: str = "priority"
    starvation_timeout_seconds: float = 60.0


class AppSettings(BaseModel):
    name: str = "SirenSync Green Corridor"
    version: str = "1.0.0"
    environment: str = "development"
    host: str = Field(default_factory=lambda: os.getenv("SERVER_HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("SERVER_PORT", "8000")))
    debug: bool = Field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    google_maps_api_key: str = Field(default_factory=lambda: os.getenv("GOOGLE_MAPS_API_KEY", ""))
    signal_controller_type: str = Field(default_factory=lambda: os.getenv("SIGNAL_CONTROLLER_TYPE", "simulated"))
    real_controller_endpoint: str = Field(default_factory=lambda: os.getenv("REAL_CONTROLLER_ENDPOINT", ""))
    real_controller_api_key: str = Field(default_factory=lambda: os.getenv("REAL_CONTROLLER_API_KEY", ""))
    database_url: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./sirensync_traffic.db"))

    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    signals: SignalsConfig = Field(default_factory=SignalsConfig)
    conflict_resolution: ConflictConfig = Field(default_factory=ConflictConfig)
    cameras: List[CameraConfig] = Field(default_factory=list)
    junctions: List[JunctionConfig] = Field(default_factory=list)


def load_yaml_config(file_path: Path) -> Dict[str, Any]:
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache()
def get_settings(config_file: str = "config.yaml") -> AppSettings:
    """
    Loads config.yaml and overlays environment variables.
    """
    config_path = Path(config_file)
    yaml_data = load_yaml_config(config_path)

    # Allow custom weights path override from env
    env_custom_weights = os.getenv("CUSTOM_WEIGHTS_PATH")
    if env_custom_weights and "detection" in yaml_data:
        yaml_data["detection"]["custom_weights"] = env_custom_weights

    # Combine configurations
    app_data = yaml_data.get("app", {})
    return AppSettings(
        name=app_data.get("name", "SirenSync Green Corridor"),
        version=app_data.get("version", "1.0.0"),
        environment=app_data.get("environment", "development"),
        detection=DetectionConfig(**yaml_data.get("detection", {})),
        signals=SignalsConfig(**yaml_data.get("signals", {})),
        conflict_resolution=ConflictConfig(**yaml_data.get("conflict_resolution", {})),
        cameras=[CameraConfig(**c) for c in yaml_data.get("cameras", [])],
        junctions=[JunctionConfig(**j) for j in yaml_data.get("junctions", [])]
    )
