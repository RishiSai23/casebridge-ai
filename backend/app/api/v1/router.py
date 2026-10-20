"""
API v1 router.

All feature routers for version 1 are registered here and then included
into the main FastAPI application in app/main.py.  Future modules (complaints,
institutions, relationships, coordination, audit) should add their router to
this file only — main.py does not need to change.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import health
from app.api.v1 import institutions

# The prefix "/api/v1" is added by main.py when this router is mounted.
# Individual sub-routers add their own sub-prefix (e.g. "/health").
api_v1_router = APIRouter()

api_v1_router.include_router(health.router)
api_v1_router.include_router(institutions.router)

# Future routers — uncomment as each module is implemented:
# from app.api.v1 import complaints, coordination, audit
# api_v1_router.include_router(complaints.router)
# api_v1_router.include_router(coordination.router)
# api_v1_router.include_router(audit.router)
