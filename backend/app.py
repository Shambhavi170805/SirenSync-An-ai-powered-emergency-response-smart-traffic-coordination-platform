from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.database.init_db import init_db
from backend.routers import (
    hospitals_router,
    beds_router,
    ranking_router,
    reservations_router,
    reassignment_router,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is initialized on startup
    init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "SirenSync Hospital Intelligence + Bed Management Subsystem API.\n\n"
        "Responsible: Samriddhi (EquiMed Team)\n"
        "- Deterministic 4-Factor Hospital Ranking Engine (Distance, Capability, Traffic, Bed Availability)\n"
        "- Concurrency-Safe Transactional Bed Reservation (Atomic Compare-and-Swap Locking)\n"
        "- Configurable 40% Route-Progress Prototype Bed Reassignment Engine\n"
        "- Machine-Readable Rerouting Event Contract for Ambulance Subsystem (Nidhi)\n"
        "- Clean Integration Contracts for Patient Experience (Shambhavi)"
    ),
    lifespan=lifespan
)

# Enable CORS for cross-module integration (Patient UI, Ambulance Tracker, Operations Dashboard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers under /api/v1 prefix
app.include_router(hospitals_router, prefix=settings.API_V1_PREFIX)
app.include_router(beds_router, prefix=settings.API_V1_PREFIX)
app.include_router(ranking_router, prefix=settings.API_V1_PREFIX)
app.include_router(reservations_router, prefix=settings.API_V1_PREFIX)
app.include_router(reassignment_router, prefix=settings.API_V1_PREFIX)

@app.get("/", tags=["System Health"])
def root():
    return {
        "service": settings.APP_NAME,
        "subsystem": "Hospital Intelligence + Bed Management",
        "owner": "Samriddhi",
        "version": settings.APP_VERSION,
        "status": "OPERATIONAL",
        "documentation": "/docs",
        "apiPrefix": settings.API_V1_PREFIX,
        "policy": {
            "rankingWeights": {
                "distance": settings.WEIGHT_DISTANCE,
                "capability": settings.WEIGHT_CAPABILITY,
                "traffic": settings.WEIGHT_TRAFFIC,
                "bedAvailability": settings.WEIGHT_BED_AVAILABILITY
            },
            "reassignmentThreshold": f"{settings.REASSIGNMENT_ROUTE_THRESHOLD_PERCENT}% route progress (prototype policy)",
            "trafficProvider": settings.TRAFFIC_PROVIDER
        }
    }

@app.get("/health", tags=["System Health"])
def health_check():
    return {"status": "HEALTHY", "service": "hospital-intelligence"}
