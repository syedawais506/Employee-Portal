from fastapi import APIRouter

from app.api.v1.endpoints import (
    assets,
    auth,
    clients,
    companies,
    departments,
    document_types,
    employees,
    leave,
    notifications,
    onboarding,
    projects,
    reports,
    roles,
    timesheets,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(departments.router)
api_router.include_router(roles.router)
api_router.include_router(document_types.router)
api_router.include_router(onboarding.onboarding_router)
api_router.include_router(employees.router)
api_router.include_router(onboarding.management_router)
api_router.include_router(clients.router)
api_router.include_router(projects.router)
api_router.include_router(timesheets.router)
api_router.include_router(leave.router)
api_router.include_router(assets.router)
api_router.include_router(reports.router)
api_router.include_router(notifications.router)
