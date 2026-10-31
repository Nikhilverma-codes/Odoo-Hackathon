from fastapi import APIRouter

from app.api.v1 import (
    auth,
    customers,
    discounts,
    invoices,
    payments,
    plans,
    products,
    quotation_templates,
    reports,
    subscriptions,
    taxes,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(customers.router)
api_router.include_router(taxes.router)
api_router.include_router(products.router)
api_router.include_router(plans.router)
api_router.include_router(quotation_templates.router)
api_router.include_router(discounts.router)
api_router.include_router(subscriptions.router)
api_router.include_router(invoices.router)
api_router.include_router(payments.router)
api_router.include_router(reports.router)
