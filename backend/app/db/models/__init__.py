# models package — imports all model modules so SQLAlchemy metadata is complete
# and Alembic env.py can discover every table by importing this package.
from app.db.models.base import Base  # noqa: F401
from app.db.models.user import User  # noqa: F401
from app.db.models.institution import Institution  # noqa: F401
from app.db.models.bureau import Bureau  # noqa: F401
from app.db.models.complaint_case import ComplaintCase  # noqa: F401
from app.db.models.case_assignment import CaseAssignment  # noqa: F401
from app.db.models.case_event import CaseEvent  # noqa: F401
from app.db.models.case_relationship import CaseRelationship  # noqa: F401
from app.db.models.coordination_action import CoordinationAction  # noqa: F401
from app.db.models.audit_log import AuditLog  # noqa: F401

__all__ = [
    "Base",
    "User",
    "Institution",
    "Bureau",
    "ComplaintCase",
    "CaseAssignment",
    "CaseEvent",
    "CaseRelationship",
    "CoordinationAction",
    "AuditLog",
]
