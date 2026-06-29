#!/usr/bin/env python3
"""
DECISION INTELLIGENCE LAYER - IL & FUNDING BACKTEST ENGINE
Simulates 10,000 blocks of concentrated liquidity (Uniswap v3 ETH/USDC)
under high-volatility regime (simulating the ETH crash of August).
Evaluates the efficiency of active risk management (exit to stable) on capital preservation.
"""
import os
import json
import math
import random

# Seed for deterministic simulation
random.seed(42)

def calculate_v3_lp_value(price, p_a, p_b, initial_capital):
    """
    Calculates the value of a Uniswap v3 LP position at a given price,
    normalized to initial capital at price p_0 = 3000.
    """
    p_0 = 3000.0
    L = initial_capital / (2.0 * math.sqrt(p_0) - math.sqrt(p_a) - p_0 / math.sqrt(p_b))
    
    if price < p_a:
        val_at_pa = L * (math.sqrt(p_b) - math.sqrt(p_a))
        return val_at_pa * (price / p_a)
    elif price > p_b:
        return L * price * (1.0 / math.sqrt(p_a) - 1.0 / math.sqrt(p_b))
    else:
        return L * (2.0 * math.sqrt(price) - math.sqrt(p_a) - price / math.sqrt(p_b))

def calculate_v3_hodl_value(price, p_a, p_b, initial_capital):
    """
    Calculates the value of holding the initial asset composition outside the pool.
    """
    p_0 = 3000.0
    L = initial_capital / (2.0 * math.sqrt(p_0) - math.sqrt(p_a) - p_0 / math.sqrt(p_b))
    
    x = L * (1.0 / math.sqrt(p_0) - 1.0 / math.sqrt(p_b))
    y = L * (math.sqrt(p_0) - math.sqrt(p_a))
    
    return x + y * (price / p_0)

def run_backtest():
    steps = 10000
    initial_capital = 10000.0  # $10,000 USDC initial capital
    p_0 = 3000.0               # Initial ETH price
    p_a = 2700.0               # Lower bound of LP range
    p_b = 3300.0               # Upper bound of LP range
    
    # Generate prices (Geometric Brownian Motion + Volatility Shock)
    prices = [p_0]
    current_price = p_0
    volatility = 0.0012  # Base step volatility
    
    for t in range(steps - 1):
        # Volatility shock around step 3000 to 6000 (representing ETH crash)
        if 3000 <= t <= 6000:
            current_vol = volatility * 5.0  # Volatility spikes 5x
            drift = -0.0003  # Downward price pressure
        else:
            current_vol = volatility
            drift = 0.00001
            
        change = random.normalvariate(drift, current_vol)
        current_price = current_price * math.exp(change)
        prices.append(current_price)
        
    # Portfolio Trackers
    port_no_shield = initial_capital
    port_with_shield = initial_capital
    
    # Drawdown trackers
    peak_no_shield = initial_capital
    peak_with_shield = initial_capital
    max_dd_no_shield = 0.0
    max_dd_with_shield = 0.0
    
    in_position = True
    cash_balance = initial_capital
    lp_shares = 1.0
    
    fees_no_shield = 0.0
    fees_with_shield = 0.0
    
    signals_count = {
        "EXECUTE": 0,
        "HEDGE": 0,
        "DELAY": 0
    }
    
    # Run simulation
    for t in range(1, steps):
        p_prev = prices[t - 1]
        p_curr = prices[t]
        
        # Estimate short-term volatility (rolling 30 steps)
        window = prices[max(0, t - 30):t]
        if len(window) > 1:
            mean = sum(window) / len(window)
            variance = sum((x - mean) ** 2 for x in window) / (len(window) - 1)
            est_vol = math.sqrt(variance) / mean
        else:
            est_vol = volatility
            
        # Fee collection per step
        step_fee_rate = (0.22 / 525600.0) * (1.0 + est_vol * 120.0)
        
        # Calculate current asset values
        lp_val = calculate_v3_lp_value(p_curr, p_a, p_b, initial_capital)
        hodl_val = calculate_v3_hodl_value(p_curr, p_a, p_b, initial_capital)
        il = max(0.0, hodl_val - lp_val)
        
        # --- DECISION ENGINE LOGIC ---
        il_pct = il / hodl_val if hodl_val > 0 else 0.0
        
        # If volatility is high or IL is substantial, switch to HEDGE/DELAY (Risk-Off)
        if est_vol > 0.0035:
            signal = "HEDGE" if in_position else "DELAY"
            new_in_position = False
        elif il_pct > 0.015:
            signal = "HEDGE" if in_position else "DELAY"
            new_in_position = False
        else:
            signal = "EXECUTE"
            new_in_position = True
            
        signals_count[signal] += 1
        
        # --- PORTFOLIO UPDATES ---
        # 1. No Shield (Always LP)
        fee_no_shield = port_no_shield * step_fee_rate
        fees_no_shield += fee_no_shield
        port_no_shield = calculate_v3_lp_value(p_curr, p_a, p_b, initial_capital) + fees_no_shield
        
        if port_no_shield > peak_no_shield:
            peak_no_shield = port_no_shield
        dd = (peak_no_shield - port_no_shield) / peak_no_shield
        if dd > max_dd_no_shield:
            max_dd_no_shield = dd
            
        # 2. With Shield (Active Management)
        if new_in_position:
            if not in_position:
                # Transition: Cash -> LP position
                # Buy back into LP shares based on current cash balance
                lp_val_ref = calculate_v3_lp_value(p_curr, p_a, p_b, initial_capital)
                lp_shares = cash_balance / lp_val_ref
                in_position = True
            
            # Update value based on active LP shares
            port_with_shield = lp_shares * calculate_v3_lp_value(p_curr, p_a, p_b, initial_capital)
            # Collect fees on the active position
            fee_with_shield = port_with_shield * step_fee_rate
            fees_with_shield += fee_with_shield
            port_with_shield += fee_with_shield
            cash_balance = port_with_shield
        else:
            if in_position:
                # Transition: Exit LP -> Cash (Locked in USDC)
                cash_balance = port_with_shield
                in_position = False
            
            # Value remains flat in USDC
            port_with_shield = cash_balance
            
        # Track Max Drawdown for Shield
        if port_with_shield > peak_with_shield:
            peak_with_shield = port_with_shield
        dd = (peak_with_shield - port_with_shield) / peak_with_shield
        if dd > max_dd_with_shield:
            max_dd_with_shield = dd
            
    # Calculate final improvement
    losses_prevented_pct = 0.0
    if max_dd_no_shield > 0:
        losses_prevented_pct = (max_dd_no_shield - max_dd_with_shield) / max_dd_no_shield * 100.0
        
    report = {
        "engine": "Decision Intelligence Layer",
        "regime": "August High Volatility ETH Crash Simulation",
        "steps": steps,
        "initial_eth_price": p_0,
        "final_eth_price": prices[-1],
        "lp_range": f"[{p_a}, {p_b}]",
        "metrics": {
            "max_drawdown_without_shield_pct": round(max_dd_no_shield * 100, 2),
            "max_drawdown_with_shield_pct": round(max_dd_with_shield * 100, 2),
            "losses_prevented_pct": round(losses_prevented_pct, 2),
            "final_value_without_shield_usd": round(port_no_shield, 2),
            "final_value_with_shield_usd": round(port_with_shield, 2),
            "execute_signals": signals_count["EXECUTE"],
            "hedge_signals": signals_count["HEDGE"],
            "delay_signals": signals_count["DELAY"]
        }
    }
    
    # Save report
    out_dir = "/home/faouzi/Antigravity_System/04_Strategy_Gerber/Audit_Factory/Strategic_Signals"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "backtest_report.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
        
    print("================================================================")
    print("  DECISION INTELLIGENCE ENGINE — BACKTEST RESULTS")
    print("================================================================")
    print(f"  Regime      : {report['regime']}")
    print(f"  Blocks      : {report['steps']}")
    print(f"  Range LP    : {report['lp_range']}")
    print(f"  Initial ETH : ${p_0:.2f}  -->  Final ETH : ${prices[-1]:.2f}")
    print("  --------------------------------------------------------------")
    print(f"  Max Drawdown WITHOUT Shield : {report['metrics']['max_drawdown_without_shield_pct']}%")
    print(f"  Max Drawdown WITH Shield    : {report['metrics']['max_drawdown_with_shield_pct']}%")
    print(f"  LOSSES PREVENTED (MDD)      : {report['metrics']['losses_prevented_pct']}% 🏆")
    print("  --------------------------------------------------------------")
    print(f"  Final Portfolio (No Shield) : ${report['metrics']['final_value_without_shield_usd']:.2f}")
    print(f"  Final Portfolio (Shield)    : ${report['metrics']['final_value_with_shield_usd']:.2f}")
    print("  --------------------------------------------------------------")
    print(f"  Signals Triggered           : EXECUTE={signals_count['EXECUTE']} | HEDGE={signals_count['HEDGE']} | DELAY={signals_count['DELAY']}")
    print(f"  Report saved to             : {out_path}")
    print("================================================================")

if __name__ == "__main__":
    run_backtest()
