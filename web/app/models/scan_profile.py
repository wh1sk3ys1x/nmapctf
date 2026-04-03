from datetime import datetime, timezone

from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScanProfile(Base):
    __tablename__ = "scan_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    nmap_args: Mapped[str] = mapped_column(String(1024))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    scan_jobs: Mapped[list["ScanJob"]] = relationship(back_populates="profile")  # noqa: F821
    schedules: Mapped[list["Schedule"]] = relationship(back_populates="profile")  # noqa: F821
