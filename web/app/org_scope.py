"""Helpers for org-scoped queries."""
from fastapi import Request
from sqlalchemy.orm import Session


def get_org_id(request: Request) -> int | None:
    """Get the current user's org_id from session. None for superadmin."""
    return request.session.get("org_id")


def is_superadmin(request: Request) -> bool:
    """Check if the current user is a superadmin."""
    return request.session.get("is_superadmin", False)


def get_org_role(request: Request) -> str | None:
    """Get the current user's org role from session."""
    return request.session.get("org_role")


def can_edit(request: Request) -> bool:
    """Check if the current user can create/edit/delete resources.
    Superadmins, org owners, and org admins can edit. Members cannot."""
    if is_superadmin(request):
        return True
    role = get_org_role(request)
    return role in ("owner", "admin")


def org_filter(query, model, request: Request):
    """Apply org_id filter to a query. Superadmin sees everything."""
    if is_superadmin(request):
        return query
    org_id = get_org_id(request)
    return query.filter(model.org_id == org_id)
