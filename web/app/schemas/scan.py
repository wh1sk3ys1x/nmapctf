from datetime import datetime

from pydantic import BaseModel

from app.models.scan_job import ScanStatus, ScanTrigger


class ScanCreate(BaseModel):
    asset_id: int
    profile_id: int


class ScanResultOut(BaseModel):
    id: int
    host: str
    port: int
    protocol: str
    state: str
    service: str | None
    version: str | None

    model_config = {"from_attributes": True}


class ScanOut(BaseModel):
    id: str
    asset_id: int
    profile_id: int
    status: ScanStatus
    trigger: ScanTrigger
    schedule_id: int | None
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None

    model_config = {"from_attributes": True}


class ScanDetailOut(ScanOut):
    results: list[ScanResultOut] = []
    raw_xml: str | None = None
