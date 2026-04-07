from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AssetAddress(Base):
    __tablename__ = "asset_addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    address: Mapped[str] = mapped_column(String(255))
    label: Mapped[str | None] = mapped_column(String(100), default=None)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    asset: Mapped["Asset"] = relationship(back_populates="addresses")  # noqa: F821
