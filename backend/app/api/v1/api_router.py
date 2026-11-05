from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.departments import router as departments_router
from app.api.v1.designations import router as designations_router
from app.api.v1.employees import router as employees_router
from app.api.v1.attendance import router as attendance_router
from app.api.v1.leaves import router as leaves_router
from app.api.v1.salary import router as salary_router
from app.api.v1.payroll import router as payroll_router
from app.api.v1.payslips import router as payslips_router
from app.api.v1.reports import router as reports_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(departments_router)
api_router.include_router(designations_router)
api_router.include_router(employees_router)
api_router.include_router(attendance_router)
api_router.include_router(leaves_router)
api_router.include_router(salary_router)
api_router.include_router(payroll_router)
api_router.include_router(payslips_router)
api_router.include_router(reports_router)
