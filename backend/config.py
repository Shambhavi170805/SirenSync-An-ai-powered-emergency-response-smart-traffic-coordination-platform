import os
from pydantic import BaseModel

class Settings(BaseModel):
    # Service Information
    APP_NAME: str = "SirenSync Hospital Intelligence & Bed Management"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Database Configuration (Default: SQLite WAL mode in database/sirensync_hospital.db)
    DATABASE_URL: str = os.getenv(
        "HOSPITAL_DATABASE_URL",
        "sqlite:////Users/shambhavisingh/Desktop/SirenSync/database/sirensync_hospital.db"
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
