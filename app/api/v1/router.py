"""API v1 router — aggregates all route modules."""
from fastapi import APIRouter
from app.api.v1.routes import auth, users, vendors, purchase_orders, health, approvals

api_router = APIRouter()

api_router.include_router(health.router,          prefix="/health",           tags=["Health"])
api_router.include_router(auth.router,            prefix="/auth",             tags=["Authentication"])
api_router.include_router(users.router,           prefix="/users",            tags=["Users"])
api_router.include_router(vendors.router,         prefix="/vendors",          tags=["Vendors"])
api_router.include_router(purchase_orders.router, prefix="/purchase-orders",  tags=["Purchase Orders"])
api_router.include_router(approvals.router,       prefix="/approvals",        tags=["Approvals"])
