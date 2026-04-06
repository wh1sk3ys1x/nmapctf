from datetime import datetime, timezone

from sqlalchemy import String, Text, Column, Table, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

asset_group_members = Table(
    "asset_group_members",
    Base.metadata,
    Column("asset_group_id", Integer, ForeignKey("asset_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("asset_id", Integer, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True),
)


class AssetGroup(Base):
    __tablename__ = "asset_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    assets: Mapped[list["Asset"]] = relationship(  # noqa: F821
        secondary=asset_group_members, back_populates="groups",
    )
    schedules: Mapped[list["Schedule"]] = relationship(back_populates="asset_group")  # noqa: F821
