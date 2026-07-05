#!/usr/bin/env python3
"""
Arsenal Decision Engine — Empirical R_net Validation v2.0
==========================================================
Validates the R_net EVALUATOR (not an oracle) on real market data.

Paradigm shift (v1 → v2):
──────────────────────────
v1: "Did the oracle correctly predict when to exit?" (prediction → often wrong)
v2: "Is the R_net calculation mathematically accurate?" (measurement → always correct)

Methodology:
─────────────
For each day D in the dataset, for each holding period N:
  1. Simulate entering a 50/50 LP position at close[D]
  2. After N days, compute ACTUAL R_net = yield - IL
  3. Compare the evaluator's risk_level at each monitoring day
     against the actual final outcome
  4. Measure: how often does risk_level correctly predict
     whether R_net will be positive or negative at maturity?

This validates the USEFULNESS of the risk signal,
not the accuracy of the math (which is trivially 100%).

Usage:
    python3 run_empirical_backtest.py [csv_path]
"""
import csv
import math
import json
import sys
import time
import os

# Import the core entity
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from evaluate_pool import calculate_il, classify_risk, calculate_breakeven_ratio


# ═══════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════

def load_prices(csv_path):
    """Load closing prices and dates from CSV."""
    dates, prices = [], []
    with open(csv_path, "r") as f:
        for row in csv.DictReader(f):
            dates.append(row["date"])
            prices.append(float(row["close"]))
    return dates, prices


# ═══════════════════════════════════════════════════════
# BACKTEST ENGINE v2 — R_NET EVALUATOR VALIDATION
# ═══════════════════════════════════════════════════════

def simulate_position_v2(prices, entry_idx, hold_days, annual_apy):
    """
    Simulate one LP position and evaluate how the R_net evaluator
    performs at each monitoring checkpoint.
    """
    entry_price = prices[entry_idx]
    exit_price = prices[entry_idx + hold_days]

    # Actual outcome at maturity
    final_ratio = exit_price / entry_price
    final_il = calculate_il(final_ratio)
    total_yield = annual_apy * (hold_days / 365.0)
    actual_r_net = total_yield - final_il
    actual_risk = classify_risk(actual_r_net)

    # Evaluate the position at multiple checkpoints (daily monitoring)
    checkpoints = []
    for day in range(1, hold_days + 1):
        current_price = prices[entry_idx + day]
        current_ratio = current_price / entry_price
        current_il = calculate_il(current_ratio)
        current_yield = annual_apy * (day / 365.0)
        current_r_net = current_yield - current_il
        current_risk = classify_risk(current_r_net)

        checkpoints.append({
            "day": day,
            "ratio": round(current_ratio, 4),
            "il_pct": round(current_il * 100, 4),
            "r_net_pct": round(current_r_net * 100, 4),
            "risk_level": current_risk,
        })

    # Was the mid-point risk level predictive of the final outcome?
    mid_check = checkpoints[len(checkpoints) // 2]  # halfway checkpoint
    mid_was_negative = mid_check["r_net_pct"] < 0
    final_was_negative = actual_r_net < 0

    return {
        "entry_price": entry_price,
        "exit_price": exit_price,
        "final_ratio": round(final_ratio, 4),
        "final_il_pct": round(final_il * 100, 4),
        "total_yield_pct": round(total_yield * 100, 4),
        "actual_r_net_pct": round(actual_r_net * 100, 4),
        "actual_risk_level": actual_risk,
        "mid_risk_level": mid_check["risk_level"],
        "mid_predicted_correctly": mid_was_negative == final_was_negative,
        "worst_checkpoint": min(checkpoints, key=lambda c: c["r_net_pct"]),
        "breakeven_corridor": calculate_breakeven_ratio(annual_apy, hold_days),
        "price_stayed_in_corridor": True,  # calculated below
    }


def run_backtest(csv_path, holding_periods=None, apy_scenarios=None):
    """Run the R_net evaluator validation."""
    if holding_periods is None:
        holding_periods = [7, 14, 30]
    if apy_scenarios is None:
        apy_scenarios = [0.10, 0.20, 0.35]

    dates, prices = load_prices(csv_path)
    total_days = len(prices)
    all_results = {}

    for apy in apy_scenarios:
        for hold in holding_periods:
            if total_days <= hold:
                continue

            key = f"APY_{int(apy*100)}pct_Hold_{hold}d"
            positions = []
            lower_be, upper_be = calculate_breakeven_ratio(apy, hold)

            for entry in range(total_days - hold):
                pos = simulate_position_v2(prices, entry, hold, apy)

                # Check if the price ratio ever left the breakeven corridor
                entry_price = prices[entry]
                corridor_breached = False
                for day in range(1, hold + 1):
                    ratio = prices[entry + day] / entry_price
                    if ratio < lower_be or ratio > upper_be:
                        corridor_breached = True
                        break
                pos["price_stayed_in_corridor"] = not corridor_breached

                positions.append(pos)

            n = len(positions)

            # ── R_net Distribution ──
            r_nets = [p["actual_r_net_pct"] for p in positions]
            positive_r_net = sum(1 for r in r_nets if r > 0)
            negative_r_net = sum(1 for r in r_nets if r <= 0)
            avg_r_net = sum(r_nets) / n if n > 0 else 0
            min_r_net = min(r_nets) if r_nets else 0
            max_r_net = max(r_nets) if r_nets else 0

            # ── Risk Level Distribution ──
            risk_dist = {"LOW": 0, "MODERATE": 0, "HIGH": 0, "CRITICAL": 0}
            for p in positions:
                risk_dist[p["actual_risk_level"]] += 1

            # ── Mid-checkpoint Predictive Accuracy ──
            correct_predictions = sum(1 for p in positions if p["mid_predicted_correctly"])
            predictive_accuracy = (correct_predictions / n * 100) if n > 0 else 0

            # ── Breakeven Corridor Accuracy ──
            corridor_held = sum(1 for p in positions if p["price_stayed_in_corridor"])
            # Of positions that stayed in corridor, how many ended positive?
            in_corridor_positive = sum(
                1 for p in positions
                if p["price_stayed_in_corridor"] and p["actual_r_net_pct"] > 0
            )
            corridor_accuracy = (
                (in_corridor_positive / corridor_held * 100) if corridor_held > 0 else 0
            )

            all_results[key] = {
                "assumed_apy_pct": int(apy * 100),
                "holding_period_days": hold,
                "total_positions": n,
                "breakeven_corridor": [lower_be, upper_be],
                "r_net_distribution": {
                    "positive_positions": positive_r_net,
                    "negative_positions": negative_r_net,
                    "avg_r_net_pct": round(avg_r_net, 4),
                    "min_r_net_pct": round(min_r_net, 4),
                    "max_r_net_pct": round(max_r_net, 4),
                },
                "risk_level_distribution": risk_dist,
                "evaluator_accuracy": {
                    "mid_checkpoint_predictive_pct": round(predictive_accuracy, 1),
                    "corridor_held_positions": corridor_held,
                    "corridor_positive_outcome_pct": round(corridor_accuracy, 1),
                },
                "date_range": f"{dates[0]} → {dates[-1]}",
                "data_points": total_days,
            }

    return all_results


# ═══════════════════════════════════════════════════════
# REPORT OUTPUT
# ═══════════════════════════════════════════════════════

def print_report(results, exec_ms):
    """Print human-readable report."""
    print()
    print("═" * 64)
    print("  ARSENAL DECISION ENGINE — R_NET EVALUATOR VALIDATION v2.0")
    print("  Data: Real ETH/USDC daily prices (Binance)")
    print("  Paradigm: Measurement (not prediction)")
    print("═" * 64)

    for key, r in results.items():
        rd = r["r_net_distribution"]
        ea = r["evaluator_accuracy"]
        rl = r["risk_level_distribution"]
        be = r["breakeven_corridor"]

        print(f"\n{'─' * 64}")
        print(f"  {key}")
        print(f"  Period: {r['date_range']} ({r['data_points']} days)")
        print(f"  Breakeven corridor: [{be[0]}, {be[1]}]")
        print(f"{'─' * 64}")
        print(f"  Positions simulated     : {r['total_positions']}")
        print(f"  R_net positive (profit) : {rd['positive_positions']}")
        print(f"  R_net negative (loss)   : {rd['negative_positions']}")
        print(f"  Avg R_net               : {rd['avg_r_net_pct']:+.4f}%")
        print(f"  Range                   : [{rd['min_r_net_pct']:+.4f}%, {rd['max_r_net_pct']:+.4f}%]")
        print()
        print(f"  Risk level distribution:")
        print(f"    LOW: {rl['LOW']} | MODERATE: {rl['MODERATE']} | HIGH: {rl['HIGH']} | CRITICAL: {rl['CRITICAL']}")
        print()
        print(f"  ★ EVALUATOR ACCURACY:")
        print(f"    Mid-checkpoint prediction : {ea['mid_checkpoint_predictive_pct']}%")
        print(f"    Corridor → positive R_net : {ea['corridor_positive_outcome_pct']}%")
        print(f"    (of {ea['corridor_held_positions']} positions that stayed in corridor)")

    print(f"\n{'═' * 64}")
    print(f"  Execution: {exec_ms:.1f}ms | Memory: O(N) | Dependencies: 0")
    print(f"{'═' * 64}\n")


def save_report(results, output_path):
    """Save machine-readable JSON report."""
    report = {
        "engine": "Arsenal Decision Engine v2.0",
        "source": "Antigravity Engine v1.0",
        "paradigm": "R_net evaluation (measurement, not prediction)",
        "methodology": {
            "description": "Simulated 50/50 LP positions on real ETH/USDC daily close prices",
            "data_source": "Binance public API (daily OHLCV, no API key)",
            "il_formula": "IL = |2*sqrt(d)/(1+d) - 1|",
            "r_net_formula": "R_net = Yield(APY, days) - IL(price_ratio)",
            "validation": "Mid-checkpoint risk level vs actual maturity outcome",
            "breakeven_validation": "Corridor boundaries vs actual R_net sign",
        },
        "results": results,
    }

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"[EXPORT] JSON report → {output_path}")


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "eth_usdc_real.csv"
    )

    if not os.path.exists(csv_path):
        print(f"[ERROR] File not found: {csv_path}")
        print("[HINT]  Run fetch_real_data.py first.")
        sys.exit(1)

    start = time.time()
    results = run_backtest(csv_path)
    elapsed = (time.time() - start) * 1000

    print_report(results, elapsed)

    json_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "backtest_v2_results.json"
    )
    save_report(results, json_path)
