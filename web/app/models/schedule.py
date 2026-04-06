from datetime import datetime, timezone

from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), default=None)
    asset_group_id: Mapped[int | None] = mapped_column(ForeignKey("asset_groups.id"), default=None)
    profile_id: Mapped[int] = mapped_column(ForeignKey("scan_profiles.id"))
    cron_expression: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_run_at: Mapped[datetime | None] = mapped_column(default=None)

    asset: Mapped["Asset"] = relationship(back_populates="schedules")  # noqa: F821
    profile: Mapped["ScanProfile"] = relationship(back_populates="schedules")  # noqa: F821
    asset_group: Mapped["AssetGroup | None"] = relationship(back_populates="schedules")  # noqa: F821
