"""Import every model so `Base.metadata` is complete."""

from app.models.discount import (
    Discount,
    DiscountRedemption,
    DiscountScope,
    DiscountType,
    SubscriptionDiscount,
)
from app.models.invoice import (
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Payment,
    PaymentMethod,
)
from app.models.plan import BillingInterval, Plan
from app.models.product import Product, ProductType, ProductVariant, Tax
from app.models.quotation import QuotationTemplate, QuotationTemplateLine
from app.models.subscription import (
    STATUS_TRANSITIONS,
    Subscription,
    SubscriptionLine,
    SubscriptionStatus,
    SubscriptionStatusHistory,
)
from app.models.user import Customer, PasswordResetToken, Role, User

__all__ = [
    "BillingInterval",
    "Customer",
    "Discount",
    "DiscountRedemption",
    "DiscountScope",
    "DiscountType",
    "Invoice",
    "InvoiceLine",
    "InvoiceStatus",
    "PasswordResetToken",
    "Payment",
    "PaymentMethod",
    "Plan",
    "Product",
    "ProductType",
    "ProductVariant",
    "QuotationTemplate",
    "QuotationTemplateLine",
    "Role",
    "STATUS_TRANSITIONS",
    "Subscription",
    "SubscriptionDiscount",
    "SubscriptionLine",
    "SubscriptionStatus",
    "SubscriptionStatusHistory",
    "Tax",
    "User",
]
