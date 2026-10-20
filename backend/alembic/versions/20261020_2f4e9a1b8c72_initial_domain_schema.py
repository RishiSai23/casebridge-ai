"""initial domain schema

Revision ID: 2f4e9a1b8c72
Revises: None
Create Date: 2026-10-20 00:00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2f4e9a1b8c72"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bureaus",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False, comment="UUID primary key."),
        sa.Column("code", sa.String(length=50), nullable=False, comment="Stable, uppercase machine-readable code (e.g. 'PGRS', 'LEGAL')."),
        sa.Column("name", sa.String(length=300), nullable=False, comment="Full human-readable bureau name."),
        sa.Column("description", sa.Text(), nullable=True, comment="Optional description of the bureau's mandate and scope."),
        sa.Column("is_active", sa.Boolean(), nullable=False, comment="Inactive bureaus are hidden from assignment UIs but retained for history."),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="UTC timestamp set by the database at row creation."),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="UTC timestamp refreshed by the database on every update."),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_bureaus_code", "bureaus", ["code"], unique=False)
    op.create_index("ix_bureaus_is_active", "bureaus", ["is_active"], unique=False)

    op.create_table(
        "institutions",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False, comment="UUID primary key."),
        sa.Column(
            "aicte_institution_id",
            sa.String(length=100),
            nullable=True,
            comment="External AICTE institution identifier when known. Unique across non-null values (enforced via partial index).",
        ),
        sa.Column("name", sa.String(length=500), nullable=False, comment="Official institution name as received."),
        sa.Column("normalized_name", sa.String(length=500), nullable=False, comment="Lowercase, whitespace-normalised version of name for fast matching."),
        sa.Column("institution_type", sa.String(length=100), nullable=True, comment="E.g. 'university', 'college', 'polytechnic'."),
        sa.Column("state", sa.String(length=100), nullable=True, comment="Indian state / union territory."),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="UTC timestamp set by the database at row creation."),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="UTC timestamp refreshed by the database on every update."),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_institutions_normalized_name", "institutions", ["normalized_name"], unique=False)
    op.create_index("ix_institutions_state_district", "institutions", ["state", "district"], unique=False)
    op.create_index(
        "uq_institutions_aicte_id_notnull",
        "institutions",
        ["aicte_institution_id"],
        unique=True,
        postgresql_where=sa.text("aicte_institution_id IS NOT NULL"),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False, comment="UUID primary key."),
        sa.Column("display_name", sa.String(length=200), nullable=False, comment="Human-readable name shown in the UI."),
        sa.Column("email", sa.String(length=320), nullable=False, comment="Unique email address used for identification."),
        sa.Column(
            "role",
            sa.Enum(
                "admin",
                "bureau_officer",
                "analyst",
                "viewer",
                name="user_role",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            comment="Platform role: admin | bureau_officer | analyst | viewer.",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, comment="False means the account is disabled; the row is retained for audit continuity."),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="UTC timestamp set by the database at row creation."),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="UTC timestamp refreshed by the database on every update."),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_role_active", "users", ["role", "is_active"], unique=False)

    op.create_table(
        "complaint_cases",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False, comment="UUID primary key."),
        sa.Column("case_reference", sa.String(length=100), nullable=False, comment="Human-readable unique reference (e.g. 'AICTE-PGRS-2026-001234')."),
        sa.Column("institution_id", postgresql.UUID(as_uuid=False), nullable=False, comment="The institution this complaint concerns."),
        sa.Column("subject", sa.String(length=500), nullable=False, comment="Short subject line of the complaint."),
        sa.Column("description", sa.Text(), nullable=True, comment="Full complaint description. May be lengthy."),
        sa.Column("category", sa.String(length=100), nullable=True, comment="Optional complaint category (e.g. 'fee_refund', 'infrastructure')."),
        sa.Column(
            "priority",
            sa.Enum(
                "low",
                "medium",
                "high",
                "critical",
                name="case_priority",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            comment="Priority: low | medium | high | critical.",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "under_review",
                "pending_info",
                "escalated",
                "resolved",
                "closed",
                "withdrawn",
                name="case_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            comment="Case status: open | under_review | pending_info | escalated | resolved | closed | withdrawn.",
        ),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, comment="When the complaint was received by the platform (UTC)."),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True, comment="Resolution deadline (UTC). Null if not yet set."),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True, comment="When the case reached a terminal status (closed / withdrawn). UTC."),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="UTC timestamp set by the database at row creation."),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="UTC timestamp refreshed by the database on every update."),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_reference"),
    )
    op.create_index("ix_complaint_cases_case_reference", "complaint_cases", ["case_reference"], unique=False)
    op.create_index("ix_complaint_cases_due_at", "complaint_cases", ["due_at"], unique=False)
    op.create_index("ix_complaint_cases_institution_id", "complaint_cases", ["institution_id"], unique=False)
    op.create_index("ix_complaint_cases_institution_status", "complaint_cases", ["institution_id", "status"], unique=False)
    op.create_index("ix_complaint_cases_priority", "complaint_cases", ["priority"], unique=False)
    op.create_index("ix_complaint_cases_received_at", "complaint_cases", ["received_at"], unique=False)
    op.create_index("ix_complaint_cases_status", "complaint_cases", ["status"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=False), nullable=True, comment="User who performed the action. NULL for system-initiated actions."),
        sa.Column("action", sa.String(length=100), nullable=False, comment="Machine-readable action identifier (e.g. 'case.status_changed')."),
        sa.Column("entity_type", sa.String(length=100), nullable=False, comment="Type of the entity affected (e.g. 'ComplaintCase', 'Bureau')."),
        sa.Column("entity_id", sa.String(length=100), nullable=False, comment="Primary key of the affected entity as a string. No FK constraint — records must survive entity deletion."),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="UTC timestamp of the action."),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Structured audit context. Must not contain credentials, secrets, or unrestricted copies of sensitive documents."),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"], unique=False)
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"], unique=False)
    op.create_index("ix_audit_logs_occurred_at", "audit_logs", ["occurred_at"], unique=False)

    op.create_table(
        "case_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=False), nullable=False, comment="The complaint case being assigned."),
        sa.Column("bureau_id", postgresql.UUID(as_uuid=False), nullable=False, comment="The bureau taking ownership."),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, comment="When this assignment became effective (UTC)."),
        sa.Column("unassigned_at", sa.DateTime(timezone=True), nullable=True, comment="When this assignment ended (transfer or completion). NULL = still active."),
        sa.Column(
            "assignment_status",
            sa.Enum(
                "active",
                "transferred",
                "completed",
                name="assignment_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            comment="active | transferred | completed",
        ),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=False), nullable=True, comment="User who created this assignment record (optional)."),
        sa.Column("notes", sa.Text(), nullable=True, comment="Free-text notes recorded at assignment or transfer time."),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="UTC timestamp set by the database at row creation."),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="UTC timestamp refreshed by the database on every update."),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["bureau_id"], ["bureaus.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["case_id"], ["complaint_cases.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_case_assignments_bureau_id", "case_assignments", ["bureau_id"], unique=False)
    op.create_index("ix_case_assignments_case_id", "case_assignments", ["case_id"], unique=False)
    op.create_index("ix_case_assignments_status", "case_assignments", ["assignment_status"], unique=False)
    op.create_index(
        "uq_case_assignments_one_active",
        "case_assignments",
        ["case_id"],
        unique=True,
        postgresql_where=sa.text("assignment_status = 'active' AND unassigned_at IS NULL"),
    )

    op.create_table(
        "case_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=False), nullable=False, comment="The case this event belongs to."),
        sa.Column(
            "event_type",
            sa.Enum(
                "created",
                "status_changed",
                "priority_changed",
                "assigned",
                "transferred",
                "note_added",
                "evidence_requested",
                "evidence_received",
                "relationship_flagged",
                "coordination_initiated",
                "closed",
                "withdrawn",
                name="case_event_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            comment="Event classification: created | status_changed | priority_changed | assigned | transferred | note_added | evidence_requested | evidence_received | relationship_flagged | coordination_initiated | closed | withdrawn.",
        ),
        sa.Column("description", sa.Text(), nullable=False, comment="Human-readable summary of what happened."),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=False), nullable=True, comment="User who triggered this event. NULL for system-generated events."),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, comment="When the event occurred (UTC). Set explicitly, not a server default."),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Optional structured context for this event type. Must not contain credentials, passwords, or sensitive PII."),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["case_id"], ["complaint_cases.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_case_events_case_id", "case_events", ["case_id"], unique=False)
    op.create_index("ix_case_events_case_occurred", "case_events", ["case_id", "occurred_at"], unique=False)
    op.create_index("ix_case_events_event_type", "case_events", ["event_type"], unique=False)
    op.create_index("ix_case_events_occurred_at", "case_events", ["occurred_at"], unique=False)

    op.create_table(
        "case_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("source_case_id", postgresql.UUID(as_uuid=False), nullable=False, comment="Lexicographically smaller UUID of the pair. Application MUST normalise the order before insert."),
        sa.Column("target_case_id", postgresql.UUID(as_uuid=False), nullable=False, comment="Lexicographically larger UUID of the pair."),
        sa.Column(
            "relationship_type",
            sa.Enum(
                "same_institution",
                "similar_subject",
                "repeated_complaint",
                "coordinated_action",
                "evidence_shared",
                name="relationship_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            comment="Nature of the link: same_institution | similar_subject | repeated_complaint | coordinated_action | evidence_shared.",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "potential",
                "confirmed",
                "dismissed",
                name="relationship_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            comment="potential | confirmed | dismissed. Changed only by human reviewers.",
        ),
        sa.Column("confidence_score", sa.Numeric(precision=4, scale=3), nullable=True, comment="System-computed similarity score in [0.000, 1.000]. For human reference only — never triggers automatic confirmation."),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Structured explanation of the signals that produced this relationship. E.g. {'signals': [{'type': 'subject_overlap', 'score': 0.87}]}. Must not contain sensitive personal data."),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=False), nullable=True, comment="User who last reviewed this relationship."),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True, comment="When the most recent review action occurred (UTC)."),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="UTC timestamp set by the database at row creation."),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="UTC timestamp refreshed by the database on every update."),
        sa.CheckConstraint("confidence_score IS NULL OR (confidence_score >= 0.000 AND confidence_score <= 1.000)", name="ck_case_relationships_score_range"),
        sa.CheckConstraint("source_case_id != target_case_id", name="ck_case_relationships_no_self"),
        sa.CheckConstraint("source_case_id < target_case_id", name="ck_case_relationships_canonical_order"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_case_id"], ["complaint_cases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_case_id"], ["complaint_cases.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_case_id", "target_case_id", "relationship_type", name="uq_case_relationships_pair_type"),
    )
    op.create_index("ix_case_relationships_source", "case_relationships", ["source_case_id"], unique=False)
    op.create_index("ix_case_relationships_status", "case_relationships", ["status"], unique=False)
    op.create_index("ix_case_relationships_target", "case_relationships", ["target_case_id"], unique=False)
    op.create_index("ix_case_relationships_type", "case_relationships", ["relationship_type"], unique=False)

    op.create_table(
        "coordination_actions",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=False), nullable=False, comment="Primary case this action addresses."),
        sa.Column("related_case_id", postgresql.UUID(as_uuid=False), nullable=True, comment="Optional secondary case involved in this coordination (e.g. suspected duplicate)."),
        sa.Column(
            "action_type",
            sa.Enum(
                "review_overlap",
                "follow_up_transfer",
                "joint_investigation",
                "evidence_consolidation",
                "escalation_review",
                name="coordination_action_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            comment="Type: review_overlap | follow_up_transfer | joint_investigation | evidence_consolidation | escalation_review.",
        ),
        sa.Column("title", sa.String(length=300), nullable=False, comment="Brief task title shown in coordination queues."),
        sa.Column("description", sa.Text(), nullable=True, comment="Detailed description of the coordination work required."),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "in_progress",
                "completed",
                "cancelled",
                name="coordination_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            comment="pending | in_progress | completed | cancelled.",
        ),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=False), nullable=True, comment="User responsible for completing this action."),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True, comment="Target completion deadline (UTC)."),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True, comment="When the action was completed or cancelled (UTC)."),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="UTC timestamp set by the database at row creation."),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="UTC timestamp refreshed by the database on every update."),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["case_id"], ["complaint_cases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["related_case_id"], ["complaint_cases.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coordination_actions_assigned_to", "coordination_actions", ["assigned_to"], unique=False)
    op.create_index("ix_coordination_actions_case_id", "coordination_actions", ["case_id"], unique=False)
    op.create_index("ix_coordination_actions_due_at", "coordination_actions", ["due_at"], unique=False)
    op.create_index("ix_coordination_actions_related_case_id", "coordination_actions", ["related_case_id"], unique=False)
    op.create_index("ix_coordination_actions_status", "coordination_actions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_coordination_actions_status", table_name="coordination_actions")
    op.drop_index("ix_coordination_actions_related_case_id", table_name="coordination_actions")
    op.drop_index("ix_coordination_actions_due_at", table_name="coordination_actions")
    op.drop_index("ix_coordination_actions_case_id", table_name="coordination_actions")
    op.drop_index("ix_coordination_actions_assigned_to", table_name="coordination_actions")
    op.drop_table("coordination_actions")

    op.drop_index("ix_case_relationships_type", table_name="case_relationships")
    op.drop_index("ix_case_relationships_target", table_name="case_relationships")
    op.drop_index("ix_case_relationships_status", table_name="case_relationships")
    op.drop_index("ix_case_relationships_source", table_name="case_relationships")
    op.drop_table("case_relationships")

    op.drop_index("ix_case_events_occurred_at", table_name="case_events")
    op.drop_index("ix_case_events_event_type", table_name="case_events")
    op.drop_index("ix_case_events_case_occurred", table_name="case_events")
    op.drop_index("ix_case_events_case_id", table_name="case_events")
    op.drop_table("case_events")

    op.drop_index("uq_case_assignments_one_active", table_name="case_assignments")
    op.drop_index("ix_case_assignments_status", table_name="case_assignments")
    op.drop_index("ix_case_assignments_case_id", table_name="case_assignments")
    op.drop_index("ix_case_assignments_bureau_id", table_name="case_assignments")
    op.drop_table("case_assignments")

    op.drop_index("ix_audit_logs_occurred_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_complaint_cases_status", table_name="complaint_cases")
    op.drop_index("ix_complaint_cases_received_at", table_name="complaint_cases")
    op.drop_index("ix_complaint_cases_priority", table_name="complaint_cases")
    op.drop_index("ix_complaint_cases_institution_status", table_name="complaint_cases")
    op.drop_index("ix_complaint_cases_institution_id", table_name="complaint_cases")
    op.drop_index("ix_complaint_cases_due_at", table_name="complaint_cases")
    op.drop_index("ix_complaint_cases_case_reference", table_name="complaint_cases")
    op.drop_table("complaint_cases")

    op.drop_index("ix_users_role_active", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.drop_index("uq_institutions_aicte_id_notnull", table_name="institutions")
    op.drop_index("ix_institutions_state_district", table_name="institutions")
    op.drop_index("ix_institutions_normalized_name", table_name="institutions")
    op.drop_table("institutions")

    op.drop_index("ix_bureaus_is_active", table_name="bureaus")
    op.drop_index("ix_bureaus_code", table_name="bureaus")
    op.drop_table("bureaus")
