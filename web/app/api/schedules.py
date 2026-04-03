from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.models import Schedule, Asset, ScanProfile
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ScheduleOut

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("/", response_model=list[ScheduleOut])
def list_schedules(db: DbSession):
    return db.query(Schedule).order_by(Schedule.name).all()


@router.get("/{schedule_id}", response_model=ScheduleOut)
def get_schedule(schedule_id: int, db: DbSession):
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    return schedule


@router.post("/", response_model=ScheduleOut, status_code=201)
def create_schedule(body: ScheduleCreate, db: DbSession):
    if not db.get(Asset, body.asset_id):
        raise HTTPException(404, "Asset not found")
    if not db.get(ScanProfile, body.profile_id):
        raise HTTPException(404, "Profile not found")

    schedule = Schedule(**body.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    # TODO: register with APScheduler once scheduling is wired up

    return schedule


@router.patch("/{schedule_id}", response_model=ScheduleOut)
def update_schedule(schedule_id: int, body: ScheduleUpdate, db: DbSession):
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: int, db: DbSession):
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    db.delete(schedule)
    db.commit()
