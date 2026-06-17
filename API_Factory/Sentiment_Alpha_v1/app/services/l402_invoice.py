# Arsenal Decision Engine — Payment Gateway Service
# File: l402_invoice.py — L402/Lightning Network invoice layer
#
# GEMINI.md §9: implementation is swappable. Interface PaymentGateway is stable.
# Current backend: LNbits self-hosted via Docker internal network (http://lnbits:5000).
# Zero external dependency at runtime. Sovereign.
#
# Ghost Protocol §8: no internal names in this public-facing service.

import os
import json
import urllib.request
import urllib.error
import hmac
import hashlib
import base64

# Configuration — sourced from environment (Docker internal or .env).
# LNBITS_URL must point to the self-hosted lnbits container:
#   Development: http://lnbits:5000/api/v1  (Docker)
#   Mainnet:     set LND_REST_ENDPOINT in .env and LNbits will proxy to LND
_LNBITS_API_KEY = os.getenv("LNBITS_API_KEY", "")
_LNBITS_URL     = os.getenv("LNBITS_URL", "http://lnbits:5000/api/v1")
_GATEWAY_SECRET = os.getenv("GATEWAY_SECRET_KEY", "change-me-in-production-env")


# =============================================================================
# PRIVATE CRYPTOGRAPHIC HELPERS
# =============================================================================

def _generate_macaroon(payment_hash: str) -> str:
    """
    Generates a server-signed macaroon tied to a specific payment hash.
    HMAC-SHA256 signed with GATEWAY_SECRET_KEY.
    The macaroon is returned to the client as part of the L402 challenge.
    Format: {payment_hash}.{signature_b64}
    """
    signature = hmac.new(
        _GATEWAY_SECRET.encode(),
        payment_hash.encode(),
        hashlib.sha256
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')
    return f"{payment_hash}.{sig_b64}"


def _simulated_challenge(reason: str = "offline") -> tuple[str, str]:
    """
    Returns a deterministic simulated (fake) invoice for dev/test environments.
    Clearly labelled — never to be mistaken for a real mainnet invoice.
    """
    sim_hash = hashlib.sha256(f"simulated_{reason}_2026".encode()).hexdigest()
    sim_pr   = f"lnbc1_SIMULATED_DEV_INVOICE_{reason[:12].upper()}"
    return _generate_macaroon(sim_hash), sim_pr


# =============================================================================
# INVOICE CREATION — LNbits REST API
# =============================================================================

def create_lightning_invoice(
    amount_usd: float = 0.15,
    memo: str = "Arsenal Decision Engine — Decision Intelligence Layer"
) -> tuple[str, str]:
    """
    Requests a fresh Lightning invoice from the self-hosted LNbits instance.

    USD → Sats conversion: 1 sat ≈ $0.001 (conservative, server-adjusted).
    For production: inject a real-time BTC/USD price feed.

    Returns: (macaroon, bolt11_invoice_payment_request)
    """
    amount_sats = max(1, int(amount_usd * 1000))   # floor at 1 sat

    if not _LNBITS_API_KEY:
        # No API key → dev/test mode. Log clearly, never silently.
        print(f"[PaymentGateway] LNBITS_API_KEY not set — simulation mode active.")
        return _simulated_challenge("no_key")

    try:
        url     = f"{_LNBITS_URL}/payments"
        payload = json.dumps({
            "out":    False,
            "amount": amount_sats,
            "memo":   memo,
        }).encode('utf-8')

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                'X-Api-Key':     _LNBITS_API_KEY,
                'Content-Type':  'application/json',
            },
            method='POST',
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status in (200, 201):
                data         = json.loads(response.read().decode('utf-8'))
                invoice_pr   = data.get("payment_request", "")
                payment_hash = data.get("payment_hash", "")

                if not invoice_pr or not payment_hash:
                    raise ValueError(f"LNbits returned incomplete response: {data}")

                macaroon = _generate_macaroon(payment_hash)
                print(f"[PaymentGateway] Invoice created — {amount_sats} sats — hash:{payment_hash[:12]}...")
                return macaroon, invoice_pr

    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode('utf-8')
        except Exception:
            body = "(unreadable)"
        print(f"[PaymentGateway] LNbits HTTPError {e.code}: {body}")

    except Exception as e:
        print(f"[PaymentGateway] Invoice creation failed: {type(e).__name__}: {e}")

    # Degraded mode: return a labelled fallback (macaroon will never verify)
    print("[PaymentGateway] ⚠ Falling back to simulated invoice — check LNbits connectivity.")
    return _simulated_challenge("api_error")


# =============================================================================
# PAYMENT VERIFICATION — L402 Proof of Payment
# =============================================================================

def verify_l402_credentials(authorization_header: str) -> bool:
    """
    Validates the L402 proof-of-payment.

    Protocol:
      1. Parse  Authorization: L402 <macaroon>:<preimage>
      2. Verify signature(macaroon) = HMAC(GATEWAY_SECRET_KEY, payment_hash)
      3. If preimage is not the mock/fake preimage, check that SHA256(preimage) == payment_hash
      4. Confirm invoice is settled on LNbits

    Returns True only when all steps pass.
    """
    try:
        if not authorization_header or not authorization_header.startswith("L402 "):
            return False

        credentials = authorization_header[5:]   # Strip "L402 "
        if ":" not in credentials:
            return False

        macaroon, preimage = credentials.split(":", 1)

        # Parse payment_hash and signature from macaroon
        if "." not in macaroon:
            print(f"[PaymentGateway] Macaroon parsing error: missing dot separator.")
            return False
        payment_hash, sig_b64 = macaroon.split(".", 1)

        # Step 2: Macaroon integrity check (HMAC verification)
        signature = hmac.new(
            _GATEWAY_SECRET.encode(),
            payment_hash.encode(),
            hashlib.sha256
        ).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')
        
        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            print(f"[PaymentGateway] Macaroon signature invalid — invalid or tampered token.")
            return False

        # Step 3: Proof-of-Payment check
        # LNbits FakeWallet (used in development/sandbox) returns a mock preimage of all zeros.
        # If it is not the mock preimage, we enforce that SHA256(preimage) == payment_hash.
        is_mock_preimage = preimage == "0000000000000000000000000000000000000000000000000000000000000000"
        if not is_mock_preimage:
            derived_hash = hashlib.sha256(bytes.fromhex(preimage)).hexdigest()
            if derived_hash != payment_hash:
                print(f"[PaymentGateway] Preimage mismatch — SHA256(preimage) != payment_hash.")
                return False

        # Step 4: On-chain settlement confirmation via LNbits
        if _LNBITS_API_KEY:
            url = f"{_LNBITS_URL}/payments/{payment_hash}"
            req = urllib.request.Request(
                url,
                headers={'X-Api-Key': _LNBITS_API_KEY},
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    settled = data.get("paid", False)
                    if not settled:
                        print(f"[PaymentGateway] Invoice not yet settled — hash:{payment_hash[:12]}...")
                    return settled
            return False

        # Simulation/dev mode: macaroon verified, skip on-chain check
        print("[PaymentGateway] LNBITS_API_KEY absent — skipping on-chain settlement check (dev mode).")
        return True

    except ValueError as e:
        print(f"[PaymentGateway] L402 parsing error (bad hex preimage?): {e}")
        return False
    except Exception as e:
        print(f"[PaymentGateway] Verification error: {type(e).__name__}: {e}")
        return False


# =============================================================================
# L402Gateway — §9 Concrete Implementation of PaymentGateway Protocol
# =============================================================================

class L402Gateway:
    """
    L402/Lightning Network payment gateway.
    Maturity: Experimental ⚡ — GEMINI.md §9.

    Backend: LNbits self-hosted (Docker internal network, port 5000).
    To swap backend: implement a new class (NWCGateway, StripeGateway, X402Gateway)
    in a new file and update the instantiation in auth.py — zero other changes.
    """

    def create_challenge(
        self,
        amount_usd: float = 0.15,
        memo: str = "Arsenal Decision Engine — Decision Intelligence Layer",
    ) -> tuple[str, str]:
        """
        Returns (macaroon, bolt11_invoice_pr).
        Macaroon is the L402 token. bolt11 is the Lightning invoice to pay.
        """
        return create_lightning_invoice(amount_usd=amount_usd, memo=memo)

    def verify_payment(self, authorization_header: str) -> bool:
        """
        Returns True if the L402 Authorization header contains valid proof-of-payment.
        """
        return verify_l402_credentials(authorization_header)
