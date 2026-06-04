# Arsenal Decision Engine — Dynamic Uncertainty Pricing (DUP)
# File: uncertainty_pricing.py
#
# Theoretical basis:
#   - Prospect Theory (Kahneman & Tversky, 1979): loss-avoidance signals
#     command 2× to 33× premium over standard confirmation signals.
#   - §4 Global Rules: volatility tier drives decision value, not CPU cost.
#   - Torvalds constraint: O(1) dict lookup, < 0.01ms. Zero I/O. Zero network.
#
# Ghost Protocol §8: no internal names exposed in this module.

import os
import time
import threading

# =============================================================================
# DUP PRICING TABLE — §4 Prospect Theory (Kahneman & Tversky)
# =============================================================================
# Format: volatility_tier → (sats, reason_string)
# Baseline: 150 sats ($0.15) for standard LOW confirmation.
# Premium tiers reflect loss-avoidance value, not CPU cost.
#
#   LOW:     150 sats  — Standard confirmation signal. Trend follow.
#   MEDIUM:  300 sats  — Confirmed signal. Moderate capital at risk.
#   HIGH:   1500 sats  — High-volatility signal. Significant risk exposure.
#   EXTREME: 5000 sats — Loss-avoidance signal. Liquidation risk detected.
#
_DUP_TABLE: dict[str, tuple[int, str]] = {
    "LOW":     (150,  "Standard signal — trend confirmation"),
    "MEDIUM":  (300,  "Confirmed signal — moderate risk exposure"),
    "HIGH":    (1500, "High-volatility signal — capital at risk"),
    "EXTREME": (5000, "Loss-avoidance signal — liquidation risk"),
}

# =============================================================================
# SHADOW STATE — In-memory market state (O(1) read/write)
# =============================================================================
# Thread-safe via a lock. The engine writes the last known volatility after
# each analysis. The next payment challenge reads it instantly.
# This is a SharedPlan state (Grosz 1996) — partial knowledge propagation.
#
_state_lock   = threading.Lock()
_market_state = {
    "volatility":  "LOW",
    "updated_at":  0.0,    # Unix timestamp of last update
    "total_calls": 0,      # Shadow mode: count of requests priced dynamically
}


def update_market_state(volatility: str) -> None:
    """
    Called by the engine after each analysis to update the shadow state.
    Thread-safe write. Latency: < 0.01ms (lock + dict write).

    Args:
        volatility: One of LOW | MEDIUM | HIGH | EXTREME (§4 standard).
    """
    if volatility not in _DUP_TABLE:
        return  # Ignore unknown tiers — never mutate on bad input.

    with _state_lock:
        _market_state["volatility"]  = volatility
        _market_state["updated_at"]  = time.time()
        _market_state["total_calls"] += 1


def get_market_state() -> dict:
    """
    Returns the current shadow state snapshot (read-only copy).
    Safe to call from any thread.
    """
    with _state_lock:
        return dict(_market_state)


# =============================================================================
# CORE PRICING FUNCTION — O(1)
# =============================================================================

def calculate_uncertainty_premium() -> tuple[float, str, str]:
    """
    Calculates the dynamic API price based on the current market volatility.

    Returns:
        (amount_usd, reason, volatility_level)
        - amount_usd      : price to inject into the L402 invoice
        - reason          : human-readable justification for the price
        - volatility_level: the tier that triggered this price (for logging)

    Latency guarantee: < 0.01ms. Pure dict lookup + float division.
    No network calls. No disk I/O. No external dependencies.
    """
    with _state_lock:
        current_volatility = _market_state["volatility"]

    sats, reason = _DUP_TABLE.get(current_volatility, _DUP_TABLE["LOW"])
    amount_usd   = round(sats / 1000.0, 4)   # sats → USD at 1 sat = $0.001

    return amount_usd, reason, current_volatility


# =============================================================================
# SHADOW MODE LOGGER
# =============================================================================

def log_dup_shadow(volatility: str, dynamic_sats: int, enforced: bool) -> None:
    """
    Shadow Mode: logs what DUP would have charged vs. what was actually enforced.
    This data feeds the Lean Startup 'Measure' phase before enabling strict mode.

    Args:
        volatility   : current market tier
        dynamic_sats : what DUP would charge
        enforced     : True if DUP_STRICT_MODE=true (strict) else False (shadow)
    """
    base_sats = 150
    premium   = dynamic_sats - base_sats
    mode      = "STRICT" if enforced else "SHADOW"

    print(
        f"[DUP/{mode}] volatility={volatility} "
        f"dynamic={dynamic_sats}sats "
        f"premium=+{premium}sats "
        f"enforced={enforced}"
    )
