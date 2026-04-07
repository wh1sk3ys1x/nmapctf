import enum
from datetime import datetime, timezone

from sqlalchemy import String, Text, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AssetType(str, enum.Enum):
    host = "host"
    ip = "ip"
    subnet = "subnet"
    range = "range"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    type: Mapped[AssetType] = mapped_column(Enum(AssetType))
    address: Mapped[str] = mapped_column(String(255))
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    scan_jobs: Mapped[list["ScanJob"]] = relationship(back_populates="asset", cascade="all, delete-orphan")  # noqa: F821
    schedules: Mapped[list["Schedule"]] = relationship(back_populates="asset", cascade="all, delete-orphan")  # noqa: F821
    groups: Mapped[list["AssetGroup"]] = relationship(  # noqa: F821
        secondary="asset_group_members", back_populates="assets",
    )
    addresses: Mapped[list["AssetAddress"]] = relationship(  # noqa: F821
        back_populates="asset", cascade="all, delete-orphan",
    )
