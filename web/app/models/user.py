import enum
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"


class OrgRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.admin)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), default=None)
    org_role: Mapped[OrgRole | None] = mapped_column(Enum(OrgRole), default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    organization: Mapped["Organization | None"] = relationship(back_populates="users")  # noqa: F821
