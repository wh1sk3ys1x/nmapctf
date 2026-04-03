from datetime import datetime

from pydantic import BaseModel


class ProfileCreate(BaseModel):
    name: str
    nmap_args: str
    description: str | None = None


class ProfileUpdate(BaseModel):
    name: str | None = None
    nmap_args: str | None = None
    description: str | None = None


class ProfileOut(BaseModel):
    id: int
    name: str
    nmap_args: str
    description: str | None
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
