from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScanResult(Base):
    __tablename__ = "scan_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("scan_jobs.id"), index=True)
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer)
    protocol: Mapped[str] = mapped_column(String(10))
    state: Mapped[str] = mapped_column(String(20))
    service: Mapped[str | None] = mapped_column(String(255), default=None)
    version: Mapped[str | None] = mapped_column(String(255), default=None)

    job: Mapped["ScanJob"] = relationship(back_populates="results")  # noqa: F821
