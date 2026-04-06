from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import DbSession
from app.auth import hash_password, verify_password
from app.models import User

router = APIRouter(tags=["views"])


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    from app.main import templates
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "auth/login.html", {"error": None})


@router.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, db: DbSession, username: str = Form(...), password: str = Form(...)):
    from app.main import templates
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request, "auth/login.html", {"error": "Invalid username or password"}, status_code=401,
        )
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["org_id"] = user.org_id
    request.session["is_superadmin"] = user.is_superadmin
    request.session["org_role"] = user.org_role.value if user.org_role else None
    return RedirectResponse("/", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request, db: DbSession):
    from app.main import templates
    if db.query(User).first():
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "auth/setup.html", {"error": None})


@router.post("/setup", response_class=HTMLResponse)
def setup_submit(
    request: Request,
    db: DbSession,
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
):
    from app.main import templates
    if db.query(User).first():
        return RedirectResponse("/login", status_code=303)

    if password != password_confirm:
        return templates.TemplateResponse(
            request, "auth/setup.html", {"error": "Passwords do not match"}, status_code=400,
        )

    if len(password) < 8:
        return templates.TemplateResponse(
            request, "auth/setup.html", {"error": "Password must be at least 8 characters"}, status_code=400,
        )

    user = User(username=username, password_hash=hash_password(password), is_superadmin=True)
    db.add(user)
    db.commit()

    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["org_id"] = None
    request.session["is_superadmin"] = True
    request.session["org_role"] = None
    return RedirectResponse("/", status_code=303)
