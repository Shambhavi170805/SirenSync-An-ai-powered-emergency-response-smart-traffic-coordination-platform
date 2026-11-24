import os
from pathlib import Path
from pydantic import BaseModel

_REPO_ROOT = Path(__file__).resolve().parents[1]
_EXTERNAL_DATABASE_DIR = _REPO_ROOT.parent / "database"
_DATABASE_DIR = _EXTERNAL_DATABASE_DIR if _EXTERNAL_DATABASE_DIR.exists() else _REPO_ROOT / "database"

class Settings(BaseModel):
    # Service Information
    APP_NAME: str = "SirenSync Hospital Intelligence & Bed Management"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Database Configuration (Default: SQLite WAL mode in database/sirensync_hospital.db)
    DATABASE_URL: str = os.getenv(
        "HOSPITAL_DATABASE_URL",
        f"sqlite:///{(_DATABASE_DIR / 'sirensync_hospital.db').as_posix()}"
    )

    # Deterministic Hospital Ranking Engine Weights (Sum must equal 1.0)
    WEIGHT_DISTANCE: float = float(os.getenv("WEIGHT_DISTANCE", "0.30"))
    WEIGHT_CAPABILITY: float = float(os.getenv("WEIGHT_CAPABILITY", "0.35"))
    WEIGHT_TRAFFIC: float = float(os.getenv("WEIGHT_TRAFFIC", "0.20"))
    WEIGHT_BED_AVAILABILITY: float = float(os.getenv("WEIGHT_BED_AVAILABILITY", "0.15"))

    # Maximum Distance Boundary for Candidate Evaluation (Default: 30 km)
    MAX_RANKING_RADIUS_KM: float = float(os.getenv("MAX_RANKING_RADIUS_KM", "30.0"))

    # Configurable 40% Route-Progress Prototype Bed Reassignment Policy
    # IMPORTANT: This is a configurable prototype system rule for the demonstration.
    # It is NOT a clinical, medical, legal, or scientifically validated protocol.
    REASSIGNMENT_ROUTE_THRESHOLD_PERCENT: float = float(
        os.getenv("REASSIGNMENT_ROUTE_THRESHOLD_PERCENT", "40.0")
    )

    # Traffic Provider: "mock" (default, deterministic, zero external dependency)
    TRAFFIC_PROVIDER: str = os.getenv("TRAFFIC_PROVIDER", "mock")

settings = Settings()
