# © 2026 Arsenal Decision Engine — Decision Intelligence Layer
# File: payment_gateway.py — Stable A2A Monetization Contract
# GEMINI.md §9: "l'implémentation change, l'interface PaymentGateway reste."
# Ghost Protocol: internal identity purged for public compatibility.

from typing import Protocol, Tuple, runtime_checkable


@runtime_checkable
class PaymentGateway(Protocol):
    """
    Stable contract for A2A monetization. §9 Global Rules v3.0.

    This interface is the single stable boundary between the auth middleware
    and any payment implementation (L402/Lightning, Stripe, x402, USDT).
    The middleware depends ONLY on this interface — never on a concrete class.

    Supported implementations (§9 maturity table):
        - L402Gateway    : L402/Lightning — Experimental ⚡
        - StripeGateway  : Stripe/pay-call — Production ✅ (future)
        - X402Gateway    : x402 HTTP      — Emerging 🔬 (future)
    """

    def create_challenge(self, amount_usd: float, memo: str) -> Tuple[str, str]:
        """
        Generates a payment challenge for an unpaid request.

        Args:
            amount_usd: Price in USD for this API call.
            memo:       Human-readable description of the purchase.

        Returns:
            Tuple (challenge_token, payment_request)
            - challenge_token : opaque string to include in WWW-Authenticate header
            - payment_request : protocol-specific payment URI (Lightning invoice, Stripe URL...)
        """
        ...

    def verify_payment(self, authorization_header: str) -> bool:
        """
        Validates a proof of payment submitted by the calling agent.

        Args:
            authorization_header: Raw value of the Authorization HTTP header.

        Returns:
            True if payment is confirmed and the request may proceed.
            False if payment is absent, invalid, or unconfirmed.
        """
        ...
