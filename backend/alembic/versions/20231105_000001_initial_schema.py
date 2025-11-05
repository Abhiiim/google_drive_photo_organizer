"""Initial database schema for service layer."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20231105_000001"
down_revision = None
branch_labels = None
depends_on = None


job_status_enum = sa.Enum("pending", "processing", "completed", "failed", name="job_status")
job_phase_enum = sa.Enum(
    "initialization",
    "face_detection",
    "clustering",
    "organizing",
    name="job_phase",
)
photo_status_enum = sa.Enum(
    "pending",
    "processing",
    "completed",
    "failed",
    name="photo_processing_status",
)


def upgrade() -> None:
    bind = op.get_bind()
    job_status_enum.create(bind, checkfirst=True)
    job_phase_enum.create(bind, checkfirst=True)
    photo_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("google_drive_token", sa.Text(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("folder_id", sa.String(length=255), nullable=True),
        sa.Column("folder_name", sa.String(length=255), nullable=True),
        sa.Column("status", job_status_enum, nullable=False, server_default="pending"),
        sa.Column("phase", job_phase_enum, nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_photos", sa.Integer(), nullable=True),
        sa.Column("processed_photos", sa.Integer(), nullable=True),
        sa.Column("faces_detected", sa.Integer(), nullable=True),
        sa.Column("persons_found", sa.Integer(), nullable=True),
        sa.Column("result_metadata", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("celery_task_id", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_deleted_at", "jobs", ["deleted_at"])

    op.create_table(
        "persons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False, server_default="Person"),
        sa.Column("folder_id", sa.String(length=255), nullable=True),
        sa.Column("sample_face_path", sa.String(length=512), nullable=True),
        sa.Column("face_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_persons_job_id", "persons", ["job_id"])
    op.create_index("ix_persons_user_id", "persons", ["user_id"])
    op.create_index("ix_persons_deleted_at", "persons", ["deleted_at"])

    op.create_table(
        "photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("drive_id", sa.String(length=255), nullable=False),
        sa.Column("original_folder_id", sa.String(length=255), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("is_multi_face", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("face_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processing_status", photo_status_enum, nullable=False, server_default="pending"),
        sa.Column("processing_metadata", sa.JSON(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_photos_job_id", "photos", ["job_id"])
    op.create_index("ix_photos_user_id", "photos", ["user_id"])
    op.create_index("ix_photos_drive_id", "photos", ["drive_id"], unique=True)
    op.create_index("ix_photos_original_folder_id", "photos", ["original_folder_id"])
    op.create_index("ix_photos_deleted_at", "photos", ["deleted_at"])

    op.create_table(
        "photo_persons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("photo_id", sa.Integer(), sa.ForeignKey("photos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("person_id", sa.Integer(), sa.ForeignKey("persons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_original_location", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_photo_persons_photo_id", "photo_persons", ["photo_id"])
    op.create_index("ix_photo_persons_person_id", "photo_persons", ["person_id"])
    op.create_unique_constraint(
        "uq_photo_persons_photo_id_person_id",
        "photo_persons",
        ["photo_id", "person_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_photo_persons_photo_id_person_id", "photo_persons", type_="unique")
    op.drop_index("ix_photo_persons_person_id", table_name="photo_persons")
    op.drop_index("ix_photo_persons_photo_id", table_name="photo_persons")
    op.drop_table("photo_persons")

    op.drop_index("ix_photos_deleted_at", table_name="photos")
    op.drop_index("ix_photos_original_folder_id", table_name="photos")
    op.drop_index("ix_photos_drive_id", table_name="photos")
    op.drop_index("ix_photos_user_id", table_name="photos")
    op.drop_index("ix_photos_job_id", table_name="photos")
    op.drop_table("photos")

    op.drop_index("ix_persons_deleted_at", table_name="persons")
    op.drop_index("ix_persons_user_id", table_name="persons")
    op.drop_index("ix_persons_job_id", table_name="persons")
    op.drop_table("persons")

    op.drop_index("ix_jobs_deleted_at", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_user_id", table_name="jobs")
    op.drop_table("jobs")

    op.drop_index("ix_users_deleted_at", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    photo_status_enum.drop(bind, checkfirst=True)
    job_phase_enum.drop(bind, checkfirst=True)
    job_status_enum.drop(bind, checkfirst=True)


