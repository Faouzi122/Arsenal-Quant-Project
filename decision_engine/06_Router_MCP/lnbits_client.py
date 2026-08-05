import urllib.request
import urllib.error
import json
import os
import sys

# Default LNbits I/O timeout in seconds. A bare `urllib.request.urlopen`
# without `timeout=` defaults to the system socket default (often None =
# wait forever). These calls run inside async request handlers on the
# asyncio event loop: an LNbits node that accepts the TCP connection but
# never answers would otherwise hang the whole service, not just the
# request that triggered it.
_LNBITS_TIMEOUT_DEFAULT = 8


def _load_timeout_seconds() -> float:
    """
    Reads LNBITS_TIMEOUT_SECONDS from the environment. Any non-numeric or
    non-positive value falls back to the default, and the anomaly is
    reported on stderr instead of failing silently (No Silent Fails).
    """
    raw = os.getenv("LNBITS_TIMEOUT_SECONDS")
    if raw is None:
        return _LNBITS_TIMEOUT_DEFAULT
    try:
        value = float(raw)
    except (TypeError, ValueError):
        sys.stderr.write(
            f"[LNBITS CLIENT WARNING] Invalid LNBITS_TIMEOUT_SECONDS={raw!r} "
            f"(not numeric), falling back to default {_LNBITS_TIMEOUT_DEFAULT}s\n"
        )
        sys.stderr.flush()
        return _LNBITS_TIMEOUT_DEFAULT
    if value <= 0:
        sys.stderr.write(
            f"[LNBITS CLIENT WARNING] Invalid LNBITS_TIMEOUT_SECONDS={raw!r} "
            f"(must be > 0), falling back to default {_LNBITS_TIMEOUT_DEFAULT}s\n"
        )
        sys.stderr.flush()
        return _LNBITS_TIMEOUT_DEFAULT
    return value


LNBITS_TIMEOUT_SECONDS = _load_timeout_seconds()

# Tri-state result of check_invoice(): distinguishes a confirmed-unpaid
# invoice from a verification that could not be performed at all (timeout,
# network failure, unreadable response, non-2xx HTTP status). Treating the
# latter as "unpaid" would let a client who already paid be re-invoiced
# during an LNbits outage.
PAYMENT_PAID = "paid"
PAYMENT_UNPAID = "unpaid"
PAYMENT_UNKNOWN = "unknown"


class LNbitsClient:
    """
    Lightweight REST API interface client for LNbits.
    Uses Python standard library urllib to minimize latency and memory bloat.
    """

    def __init__(self):
        # Retrieve configuration from environment or use default fallbacks
        base = os.getenv("LNBITS_URL", "http://localhost:5000").rstrip("/")
        if base.endswith("/api/v1"):
            base = base[:-7]
        self.base_url = base
        self.api_key = os.getenv("LNBITS_INVOICE_KEY", "votre_cle_api_lnbits_ici")

    def create_invoice(self, amount_sats: int, memo: str) -> dict:
        """
        Generates a Lightning Network invoice on the LNbits node.
        """
        url = f"{self.base_url}/api/v1/payments"
        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = json.dumps({
            "out": False,
            "amount": amount_sats,
            "memo": memo
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=LNBITS_TIMEOUT_SECONDS) as response:
                raw_data = response.read().decode("utf-8")
                return json.loads(raw_data)
        except Exception as e:
            print(f"[LNBITS CLIENT ERROR] Failed to create invoice: {e}")
            return {}

    def check_invoice(self, payment_hash: str) -> str:
        """
        Queries LNbits to verify if the payment corresponding to the hash is
        settled. Returns one of PAYMENT_PAID, PAYMENT_UNPAID, PAYMENT_UNKNOWN
        rather than a plain bool, so callers can tell "confirmed unpaid"
        apart from "could not verify" and avoid re-invoicing a client who
        may have already paid.
        """
        url = f"{self.base_url}/api/v1/payments/{payment_hash}"
        headers = {
            "X-Api-Key": self.api_key
        }

        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=LNBITS_TIMEOUT_SECONDS) as response:
                raw_data = response.read().decode("utf-8")
                result = json.loads(raw_data)
                return PAYMENT_PAID if result.get("paid", False) else PAYMENT_UNPAID
        except Exception as e:
            print(f"[LNBITS CLIENT ERROR] Failed to check invoice: {e}")
            return PAYMENT_UNKNOWN
