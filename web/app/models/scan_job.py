import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScanStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class ScanTrigger(str, enum.Enum):
    manual = "manual"
    scheduled = "scheduled"


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), default=None)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    profile_id: Mapped[int] = mapped_column(ForeignKey("scan_profiles.id"))
    status: Mapped[ScanStatus] = mapped_column(Enum(ScanStatus), default=ScanStatus.pending)
    trigger: Mapped[ScanTrigger] = mapped_column(Enum(ScanTrigger), default=ScanTrigger.manual)
    schedule_id: Mapped[int | None] = mapped_column(ForeignKey("schedules.id"), default=None)
    asset_group_id: Mapped[int | None] = mapped_column(ForeignKey("asset_groups.id"), default=None)
    queued_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    raw_xml: Mapped[str | None] = mapped_column(Text, default=None)

    asset: Mapped["Asset"] = relationship(back_populates="scan_jobs")  # noqa: F821
    profile: Mapped["ScanProfile"] = relationship(back_populates="scan_jobs")  # noqa: F821
    schedule: Mapped["Schedule | None"] = relationship()  # noqa: F821
    results: Mapped[list["ScanResult"]] = relationship(back_populates="job", cascade="all, delete-orphan")  # noqa: F821
