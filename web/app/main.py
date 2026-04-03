from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.seed import seed_default_profiles
from app.api import assets, profiles, scans, schedules, internal
from app.api import auth as api_auth
from app.views import dashboard as dashboard_views
from app.views import assets as asset_views
from app.views import profiles as profile_views
from app.views import schedules as schedule_views
from app.views import scans as scan_views
from app.views import auth as auth_views

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

# Public paths that don't require login
PUBLIC_PATHS = {"/login", "/setup", "/api/v1/health", "/api/v1/auth/token"}
PUBLIC_PREFIXES = ("/static/", "/api/v1/internal/")


# NOTE: @app.middleware("http") must be registered BEFORE SessionMiddleware
# so that SessionMiddleware wraps it (outermost) and the session is available.
@app.middleware("http")
async def require_login(request: Request, call_next):
    path = request.url.path
    # Allow public paths
    if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
        return await call_next(request)
    # Allow API requests with Authorization header (JWT checked by endpoint dependency)
    if path.startswith("/api/") and request.headers.get("authorization"):
        return await call_next(request)
    # Check session for web UI
    if not request.session.get("user_id"):
        # Check if any users exist; if not, redirect to setup
        db = SessionLocal()
        try:
            from app.models import User
            if not db.query(User).first():
                return RedirectResponse("/setup", status_code=303)
        finally:
            db.close()
        return RedirectResponse("/login", status_code=303)
    return await call_next(request)


# SessionMiddleware must be added AFTER @app.middleware("http") so it is outermost
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# API routers
app.include_router(api_auth.router, prefix="/api/v1")
app.include_router(assets.router, prefix="/api/v1")
app.include_router(profiles.router, prefix="/api/v1")
app.include_router(scans.router, prefix="/api/v1")
app.include_router(schedules.router, prefix="/api/v1")
app.include_router(internal.router, prefix="/api/v1")

# View routers
app.include_router(auth_views.router)
app.include_router(dashboard_views.router)
app.include_router(asset_views.router)
app.include_router(profile_views.router)
app.include_router(schedule_views.router)
app.include_router(scan_views.router)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
