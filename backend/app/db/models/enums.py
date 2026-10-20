"""
Domain enumerations for controlled-value columns.

Keeping all enums in one module prevents circular imports and makes it easy
for the Pydantic schema layer to import the same values without depending on
SQLAlchemy model modules.

All string enum values are lowercase-with-underscores so they are:
  - stable across Python renames
  - readable in database queries
  - safe to expose in API responses without re-mapping
"""

from __future__ import annotations

import enum


# --------------------------------------------------------------------------- #
# Complaint case lifecycle
# --------------------------------------------------------------------------- #

class CaseStatus(str, enum.Enum):
    """Lifecycle status of a ComplaintCase.

    Transitions (simplified):
        open → under_review → pending_info → under_review (loop)
             → escalated → resolved → closed
             → withdrawn (at any open stage)
    """
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    PENDING_INFO = "pending_info"   # awaiting supplementary evidence
    ESCALATED = "escalated"         # escalated to a senior bureau or authority
    RESOLVED = "resolved"           # action taken; awaiting complainant closure
    CLOSED = "closed"               # final terminal state
    WITHDRAWN = "withdrawn"         # complainant retracted the complaint


class CasePriority(str, enum.Enum):
    """Priority of a ComplaintCase.

    Set initially based on complaint category and institution risk profile.
    May be elevated manually by a bureau officer.
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# --------------------------------------------------------------------------- #
# Bureau assignment
# --------------------------------------------------------------------------- #

class AssignmentStatus(str, enum.Enum):
    """Whether a CaseAssignment record is currently active or historical.

    Only one assignment per case may be 'active' at any given time.
    Transfers are represented by setting the current active record to
    'transferred' and inserting a new 'active' record.
    """
    ACTIVE = "active"           # this bureau currently owns the case
    TRANSFERRED = "transferred" # ownership has been moved to another bureau
    COMPLETED = "completed"     # bureau finished its work; case subsequently closed


# --------------------------------------------------------------------------- #
# Case events
# --------------------------------------------------------------------------- #

class CaseEventType(str, enum.Enum):
    """Type of event recorded in CaseEvent.

    This is an append-only log; events are never modified or deleted.
    """
    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    PRIORITY_CHANGED = "priority_changed"
    ASSIGNED = "assigned"
    TRANSFERRED = "transferred"
    NOTE_ADDED = "note_added"
    EVIDENCE_REQUESTED = "evidence_requested"
    EVIDENCE_RECEIVED = "evidence_received"
    RELATIONSHIP_FLAGGED = "relationship_flagged"
    COORDINATION_INITIATED = "coordination_initiated"
    CLOSED = "closed"
    WITHDRAWN = "withdrawn"


# --------------------------------------------------------------------------- #
# Case relationships (overlap detection)
# --------------------------------------------------------------------------- #

class RelationshipType(str, enum.Enum):
    """Nature of the connection between two ComplaintCases.

    These are purely informational labels.  The existence of a relationship
    record does not trigger any automated action.
    """
    SAME_INSTITUTION = "same_institution"      # both cases concern the same institution
    SIMILAR_SUBJECT = "similar_subject"        # textual/semantic subject overlap
    REPEATED_COMPLAINT = "repeated_complaint"  # likely same underlying grievance, re-filed
    COORDINATED_ACTION = "coordinated_action"  # requires joint bureau action
    EVIDENCE_SHARED = "evidence_shared"        # share supporting documents or witnesses


class RelationshipStatus(str, enum.Enum):
    """Review lifecycle of a CaseRelationship.

    IMPORTANT: A confidence_score alone NEVER changes this status.
    All transitions from 'potential' require explicit human action.

    potential  → confirmed  (reviewer accepts the link)
    potential  → dismissed  (reviewer rejects the link)
    confirmed  → dismissed  (reviewer later reverses decision)
    """
    POTENTIAL = "potential"   # system-generated or manually proposed; awaiting review
    CONFIRMED = "confirmed"   # a reviewer has validated the relationship
    DISMISSED = "dismissed"   # a reviewer determined the relationship is not useful


# --------------------------------------------------------------------------- #
# Coordination actions
# --------------------------------------------------------------------------- #

class CoordinationActionType(str, enum.Enum):
    """Type of coordination work item."""
    REVIEW_OVERLAP = "review_overlap"             # review a suspected case overlap
    FOLLOW_UP_TRANSFER = "follow_up_transfer"     # follow up on a stalled transfer
    JOINT_INVESTIGATION = "joint_investigation"   # bureaus conduct a joint review
    EVIDENCE_CONSOLIDATION = "evidence_consolidation"  # merge evidence across cases
    ESCALATION_REVIEW = "escalation_review"       # review a bureau-escalated case


class CoordinationStatus(str, enum.Enum):
    """Lifecycle of a CoordinationAction."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #

class UserRole(str, enum.Enum):
    """Platform role for a User.

    Does not implement fine-grained permissions — that is deferred to the
    authentication task.  Role is stored here for data-model completeness.
    """
    ADMIN = "admin"               # full platform access
    BUREAU_OFFICER = "bureau_officer"  # manages cases within their bureau
    ANALYST = "analyst"           # read-only analytics access
    VIEWER = "viewer"             # read-only access to assigned cases
