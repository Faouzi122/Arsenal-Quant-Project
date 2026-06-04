# © 2026 Arsenal Decision Engine — Decision Intelligence Layer
# File: auth.py — HTTP Authentication & A2A Paywall Middleware
# GEMINI.md §9: auth depends on the PaymentGateway interface, not the implementation.
# To swap payment protocol: change the gateway instantiation only (line marked below).

from fastapi import Request
from fastapi.responses import JSONResponse
import os

from app.interfaces.payment_gateway import PaymentGateway
from app.services.l402_invoice import L402Gateway
from app.services.uncertainty_pricing import (
    calculate_uncertainty_premium,
    log_dup_shadow,
)

# Performance optimization: Constant time O(1) set lookup (Torvalds).
API_KEY: str        = os.getenv("MERIDIAN_API_KEY", "FAOUZI-ELITE-KEY-2026")
ENGINE_API_KEY: str = os.getenv("ENGINE_API_KEY", "")
VALID_API_KEYS: set[str] = {k for k in [API_KEY, ENGINE_API_KEY] if k}
DEBUG_BYPASS_KEY: str = "2026"

# DUP — Dynamic Uncertainty Pricing (§ Prospect Theory / Kahneman & Tversky).
# Shadow Mode: log dynamic amount, enforce baseline until DUP_STRICT_MODE=true.
DUP_STRICT_MODE: bool = os.getenv("DUP_STRICT_MODE", "false").lower() == "true"

# §9 — Single line to swap: replace L402Gateway() with StripeGateway() or X402Gateway()
# The rest of this file never changes when the payment protocol changes.
_payment_gateway: PaymentGateway = L402Gateway()


async def api_key_auth(request: Request, call_next):
    # Protect standard analytical REST endpoints
    if request.url.path.startswith("/analyze"):
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key not in VALID_API_KEYS:
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized: Invalid or missing API Key. Paywall Active."}
            )

    # Protect A2A / MCP endpoints via the PaymentGateway interface
    if request.url.path == "/mcp/v1/tools/execute":
        # 1. CEO debug bypass
        debug_mode = request.headers.get("X-Debug-Mode")
        if debug_mode == DEBUG_BYPASS_KEY:
            return await call_next(request)

        # 2. Check proof of payment through the stable gateway interface
        l402_token = request.headers.get("Authorization")
        api_key    = request.headers.get("X-API-Key")

        is_payment_valid = l402_token and _payment_gateway.verify_payment(l402_token)
        is_key_valid     = api_key and api_key in VALID_API_KEYS

        if not is_payment_valid and not is_key_valid:
            # ── DUP — Dynamic Uncertainty Pricing ──────────────────────────────
            # O(1) lookup from Shadow State. No I/O. No network. < 0.01ms.
            dynamic_amount_usd, reason, volatility = calculate_uncertainty_premium()
            dynamic_sats = int(dynamic_amount_usd * 1000)

            # Shadow Mode: always enforce baseline (150 sats = $0.15) until strict mode.
            # Strict Mode: enforce the full dynamic premium.
            effective_amount_usd = dynamic_amount_usd if DUP_STRICT_MODE else 0.15

            log_dup_shadow(volatility, dynamic_sats, DUP_STRICT_MODE)

            memo = f"Arsenal Decision Engine — {reason} [{volatility}]"
            challenge_token, payment_request = _payment_gateway.create_challenge(
                amount_usd=effective_amount_usd,
                memo=memo,
            )

            return JSONResponse(
                status_code=402,
                headers={"WWW-Authenticate": f'L402 macaroon="{challenge_token}", invoice="{payment_request}"'},
                content={
                    "error":   "Payment Required",
                    "message": "This A2A capability requires a micro-payment via L402 Lightning Protocol or a valid subscription Master Key.",
                    # §4 Standard output — decision_intelligence_fee field
                    "decision_intelligence_fee": {
                        "protocol":        "L402",
                        "currency":        "SAT",
                        "dynamic_amount":  dynamic_sats,
                        "enforced_amount": int(effective_amount_usd * 1000),
                        "reason":          reason,
                        "volatility":      volatility,
                        "strict_mode":     DUP_STRICT_MODE,
                    },
                }
            )

    return await call_next(request)
