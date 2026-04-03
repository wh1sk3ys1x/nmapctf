from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import Base, engine, SessionLocal
from app.seed import seed_default_profiles
from app.api import assets, profiles, scans, schedules, internal

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables and seed defaults on startup
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_default_profiles(db)
    finally:
        db.close()
    yield


app = FastAPI(title="nmapctf", version="0.1.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.globals["get_flashed_messages"] = lambda: []

app.include_router(assets.router, prefix="/api/v1")
app.include_router(profiles.router, prefix="/api/v1")
app.include_router(scans.router, prefix="/api/v1")
app.include_router(schedules.router, prefix="/api/v1")
app.include_router(internal.router, prefix="/api/v1")


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
