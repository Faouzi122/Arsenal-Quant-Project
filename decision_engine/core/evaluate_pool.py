#!/usr/bin/env python3
"""
Arsenal Decision Engine — R_net Evaluator (Entity Layer)
=========================================================
Pure mathematical evaluation of LP position health.
Does NOT dictate action. Delivers intelligence. The agent decides.

Formula:
    IL  = |2√d / (1+d) - 1|  where d = P_current / P_entry
    R_net = Yield - IL
    Risk_Level = f(R_net depth)

Complexity: O(1) time, O(1) memory.
Dependencies: zero (math + sys only).

Usage:
    python3 evaluate_pool.py <APY> <PRICE_RATIO> [DAYS_HELD]
    python3 evaluate_pool.py 0.12 0.85 30
"""
import sys
import math
import json


# ═══════════════════════════════════════════════════════
# CORE MATH — The Entity (immutable, stateless)
# ═══════════════════════════════════════════════════════

def calculate_il(price_ratio: float) -> float:
    """Impermanent Loss for a 50/50 constant-product AMM."""
    if price_ratio <= 0:
        return 1.0
    return abs((2 * math.sqrt(price_ratio) / (1 + price_ratio)) - 1)


def calculate_breakeven_ratio(apy: float, days: int) -> tuple:
    """
    Calculate the price ratio bounds at which IL exactly equals yield.
    Returns (lower_bound, upper_bound) — the safe corridor.
    At these boundaries, R_net = 0.
    Solved numerically (Newton's method, O(1) iterations).
    """
    target_yield = apy * (days / 365.0)
    if target_yield <= 0:
        return (1.0, 1.0)

    # Search for lower bound (d < 1 where IL = yield)
    lo = 0.01
    for _ in range(50):  # Newton converges in <10 iterations
        il = calculate_il(lo)
        if abs(il - target_yield) < 1e-8:
            break
        # Bisection between lo and 1.0
        mid = (lo + 1.0) / 2
        if calculate_il(mid) > target_yield:
            lo = mid
        else:
            lo = (lo + mid) / 2

    # Binary search for precise lower bound
    left, right = 0.001, 1.0
    for _ in range(64):
        mid = (left + right) / 2
        if calculate_il(mid) > target_yield:
            left = mid
        else:
            right = mid
    lower = (left + right) / 2

    # Binary search for upper bound (d > 1)
    left, right = 1.0, 100.0
    for _ in range(64):
        mid = (left + right) / 2
        if calculate_il(mid) > target_yield:
            right = mid
        else:
            left = mid
    upper = (left + right) / 2

    return (round(lower, 4), round(upper, 4))


def classify_risk(r_net: float) -> str:
    """
    Risk classification based on R_net depth.
    Pure math, no prediction, no opinion.
    """
    if r_net >= 0.005:      # +0.5% or better
        return "LOW"
    elif r_net >= 0.0:      # 0% to +0.5%
        return "MODERATE"
    elif r_net >= -0.02:    # 0% to -2%
        return "HIGH"
    else:                   # worse than -2%
        return "CRITICAL"


# ═══════════════════════════════════════════════════════
# EVALUATOR — The Use Case
# ═══════════════════════════════════════════════════════

def evaluate(apy: float, price_ratio: float, days_held: int = 30) -> dict:
    """
    Evaluate the health of an LP position.
    Returns a standardized JSON payload — the agent decides what to do.
    """
    il = calculate_il(price_ratio)
    accumulated_yield = apy * (days_held / 365.0)
    r_net = accumulated_yield - il
    il_to_yield = (il / accumulated_yield) if accumulated_yield > 0 else float("inf")
    risk_level = classify_risk(r_net)
    lower, upper = calculate_breakeven_ratio(apy, days_held)

    return {
        "impermanent_loss_pct": round(il * 100, 4),
        "accumulated_yield_pct": round(accumulated_yield * 100, 4),
        "r_net_pct": round(r_net * 100, 4),
        "il_to_yield_ratio": round(il_to_yield, 2),
        "risk_level": risk_level,
        "breakeven_corridor": {
            "lower_ratio": lower,
            "upper_ratio": upper,
            "interpretation": f"Position remains profitable if price ratio stays within [{lower}, {upper}]"
        },
        "inputs": {
            "apy": apy,
            "price_ratio": price_ratio,
            "days_held": days_held
        },
        "source": "Arsenal Decision Engine v2.0"
    }


def print_evaluation(result: dict):
    """Human-readable output for terminal use."""
    print()
    print("═" * 56)
    print("  ARSENAL DECISION ENGINE — R_NET EVALUATOR v2.0")
    print("═" * 56)
    print(f"  Inputs:")
    print(f"    APY assumed      : {result['inputs']['apy']*100:.1f}%")
    print(f"    Price ratio (d)  : {result['inputs']['price_ratio']:.4f}")
    print(f"    Days held        : {result['inputs']['days_held']}")
    print(f"{'─' * 56}")
    print(f"  Results:")
    print(f"    Impermanent Loss : {result['impermanent_loss_pct']:+.4f}%")
    print(f"    Accumulated Yield: {result['accumulated_yield_pct']:+.4f}%")
    print(f"    IL / Yield ratio : {result['il_to_yield_ratio']:.2f}x")
    print(f"{'─' * 56}")
    print(f"  ★ R_NET            : {result['r_net_pct']:+.4f}%")
    print(f"  ★ RISK LEVEL       : {result['risk_level']}")
    print(f"{'─' * 56}")
    be = result['breakeven_corridor']
    print(f"  Breakeven corridor : [{be['lower_ratio']}, {be['upper_ratio']}]")
    print(f"  (Position profitable while price ratio is inside this range)")
    print(f"{'═' * 56}")
    print()
    print("  JSON payload (for M2M / agent consumption):")
    print(json.dumps(result, indent=2))
    print()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 evaluate_pool.py <APY> <PRICE_RATIO> [DAYS_HELD]")
        print("Example: python3 evaluate_pool.py 0.12 0.85 30")
        print()
        print("Output: R_net evaluation + risk level + breakeven corridor.")
        print("The agent decides. The engine evaluates.")
        sys.exit(1)

    apy = float(sys.argv[1])
    ratio = float(sys.argv[2])
    days = int(sys.argv[3]) if len(sys.argv) > 3 else 30

    result = evaluate(apy, ratio, days)
    print_evaluation(result)
