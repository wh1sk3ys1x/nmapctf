from datetime import datetime

from pydantic import BaseModel


class ScheduleCreate(BaseModel):
    name: str
    asset_id: int
    profile_id: int
    cron_expression: str
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    name: str | None = None
    asset_id: int | None = None
    profile_id: int | None = None
    cron_expression: str | None = None
    enabled: bool | None = None


class ScheduleOut(BaseModel):
    id: int
    name: str
    asset_id: int
    profile_id: int
    cron_expression: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
    last_run_at: datetime | None

    model_config = {"from_attributes": True}
