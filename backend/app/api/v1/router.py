from fastapi import APIRouter

from app.api.v1.endpoints import auth, companies, departments, employees, roles

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(departments.router)
api_router.include_router(roles.router)
api_router.include_router(employees.router)
