"""
app/voucher_engine.py - Backward compatibility facade.
Re-exports voucher engine functions from app.services.voucher_service.
"""
from app.services.voucher_service import (
    VoucherValidationError,
    validate_and_calculate_discount,
    record_voucher_redemption,
    voucher_service,
    VoucherService,
)

__all__ = [
    "VoucherValidationError",
    "validate_and_calculate_discount",
    "record_voucher_redemption",
    "voucher_service",
    "VoucherService",
]
