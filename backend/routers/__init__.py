from backend.routers.hospitals import router as hospitals_router
from backend.routers.beds import router as beds_router
from backend.routers.ranking import router as ranking_router
from backend.routers.reservations import router as reservations_router
from backend.routers.reassignment import router as reassignment_router
from backend.routers.dashboard import router as dashboard_router

__all__ = [
    "hospitals_router",
    "beds_router",
    "ranking_router",
    "reservations_router",
    "reassignment_router",
    "dashboard_router",
]

