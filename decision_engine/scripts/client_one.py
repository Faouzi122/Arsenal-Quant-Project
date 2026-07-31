#!/usr/bin/env python3
"""
CLIENT ONE — Arsenal Decision Engine Integration Example
=========================================================
Demonstrates how an autonomous agent consumes the R_net and Breakeven Corridor
to dynamically manage LP positions and protect capital.
"""
import os
import sys
import json
import time
import urllib.request
import urllib.error

# Configuration
API_URL = "http://127.0.0.1:8088/mcp/evaluate?apy=0.20&price_ratio=0.85&days_held=30"
LNBITS_URL = "https://demo.lnbits.com"
# LNbits requires a wallet key with send permission to pay an invoice. Use a
# DEDICATED wallet funded with a small working balance — never the key of a
# wallet holding significant funds. Keep it in the environment, never in code.
LNBITS_PAYMENT_KEY = os.getenv("LNBITS_PAYMENT_KEY")

class AutonomousLPAgent:
    def __init__(self, initial_capital=10000.0):
        self.capital = initial_capital
        self.in_lp_pool = True
        self.stable_balance = 0.0
        self.lp_value = initial_capital
        print(f"[Agent Initialized] Capital: ${self.capital:.2f} | Status: ACTIVE_LP")

    def execute_risk_mitigation(self, evaluation: dict):
        """
        Executes active risk-management based on the R_net breakeven corridor.
        """
        corridor = evaluation.get("breakeven_corridor", {})
        lower = corridor.get("lower_ratio", 1.0)
        upper = corridor.get("upper_ratio", 1.0)
        current_ratio = evaluation.get("inputs", {}).get("price_ratio", 1.0)
        risk_level = evaluation.get("risk_level", "LOW")

        print(f"\n[Agent Log] Current Price Ratio: {current_ratio} | Corridor: [{lower}, {upper}] | Risk: {risk_level}")

        # Check if the price has breached the breakeven corridor bounds
        if (current_ratio < lower or current_ratio > upper) and self.in_lp_pool:
            print("\n" + "="*70)
            print(f"[EMERGENCY TRIGGER] Price ratio {current_ratio} out of corridor [{lower}, {upper}]")
            print(f"Executing active risk-mitigation: Exiting concentrated liquidity pool.")
            # Move LP position to stable balance (USDC) to prevent further Impermanent Loss
            self.stable_balance = self.lp_value
            self.lp_value = 0.0
            self.in_lp_pool = False
            print(f"Portfolio Status: Protected in Stablecoins | Cash Balance: ${self.stable_balance:.2f}")
            print("="*70 + "\n")
        elif current_ratio >= lower and current_ratio <= upper and not self.in_lp_pool:
            print("\n" + "="*70)
            print(f"[RE-ENTRY TRIGGER] Price ratio {current_ratio} back inside corridor [{lower}, {upper}]")
            print(f"Market stabilized. Re-entering concentrated liquidity pool.")
            self.lp_value = self.stable_balance
            self.stable_balance = 0.0
            self.in_lp_pool = True
            print(f"Portfolio Status: ACTIVE_LP | Liquidity Value: ${self.lp_value:.2f}")
            print("="*70 + "\n")
        else:
            status = "ACTIVE_LP" if self.in_lp_pool else "STABLECOINS"
            val = self.lp_value + self.stable_balance
            print(f"[Agent Log] Status: {status} | Portfolio Value: ${val:.2f} (No action required)")

    def query_oracle(self, custom_url=None):
        """
        Queries the Decision Engine. Handles the L402 payment challenge if encountered.
        """
        target_url = custom_url if custom_url else API_URL
        print(f"\n[1/3] Contacting Decision Engine at {target_url}...")
        req = urllib.request.Request(target_url, method="GET")
        req.add_header("x-agent-id", "client-one-demonstrator")
        req.add_header("User-Agent", "Mozilla/5.0")
        
        try:
            with urllib.request.urlopen(req) as response:
                body = response.read().decode('utf-8')
                print("[✅] Standard Tier: Free access allowed.")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code == 402:
                print("[402] Payment Required. Parsing L402 challenge...")
                auth_header = e.headers.get("WWW-Authenticate")
                if not auth_header:
                    print("[❌] Failed: WWW-Authenticate header missing.")
                    return None
                
                # Extract macaroon and invoice parameters
                import re
                try:
                    macaroon = re.search(r'token="([^"]+)"', auth_header).group(1)
                    invoice = re.search(r'invoice="([^"]+)"', auth_header).group(1)
                except AttributeError:
                    macaroon = re.search(r'macaroon="([^"]+)"', auth_header).group(1)
                    invoice = re.search(r'invoice="([^"]+)"', auth_header).group(1)
                
                print(f"[L402 Challenge Detected] Token: {macaroon[:15]}... | Invoice: {invoice[:20]}...")
                
                # Pay invoice (MOCK / Sandbox execution mode simulation)
                preimage = self.settle_invoice_mock(invoice)
                if not preimage:
                    return None
                
                # Retry request with authorized credentials
                print("[3/3] Submitting proof of payment to Oracle...")
                retry_req = urllib.request.Request(target_url, method="GET")
                retry_req.add_header("Authorization", f"L402 {macaroon}:{preimage}")
                retry_req.add_header("x-agent-id", "client-one-demonstrator")
                retry_req.add_header("User-Agent", "Mozilla/5.0")
                
                try:
                    with urllib.request.urlopen(retry_req) as retry_response:
                        final_body = retry_response.read().decode('utf-8')
                        print("[✅] Access Granted.")
                        return json.loads(final_body)
                except Exception as retry_err:
                    print(f"[❌] Retry request failed: {retry_err}")
                    return None
            else:
                print(f"[❌] HTTP Error: {e.code} - {e.reason}")
                return None
        except Exception as err:
            print(f"[❌] Connection failed: {err}")
            return None

    def settle_invoice_mock(self, invoice):
        """Simulates payment of the Bolt11 invoice."""
        print("[2/3] Settling Lightning Invoice...")
        time.sleep(1)
        # Mock payment pre-image returned by the LNbits node
        preimage = "0000000000000000000000000000000000000000000000000000000000000000"
        print(f"[✅] Settle Successful. Preimage: {preimage}")
        return preimage

def main():
    print("="*80)
    print("  CLIENT ONE — AUTONOMOUS RISK-MITIGATION AGENT DEMO")
    print("="*80)
    
    agent = AutonomousLPAgent(initial_capital=10000.0)
    
    # 1. Start gateway locally for simulation in python
    import subprocess
    print("\n[SYSTEM] Starting local gateway on port 8088...")
    env = os.environ.copy()
    env["L402_OVERRIDE_PRICE"] = "150"
    gateway_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "06_Router_MCP",
        "l402_gateway_real.py"
    )
    proc = subprocess.Popen(
        [sys.executable, gateway_path],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)
    
    try:
        # Scenario A: APY 20%, price ratio 0.85 (inside corridor [0.69, 1.44])
        print("\n--- SCENARIO A: Normal Market (Price ratio inside breakeven corridor) ---")
        url_normal = "http://127.0.0.1:8088/mcp/evaluate?apy=0.20&price_ratio=0.85&days_held=30"
        evaluation_normal = agent.query_oracle(url_normal)
        if evaluation_normal:
            agent.execute_risk_mitigation(evaluation_normal)

        # Scenario B: APY 20%, price ratio 0.60 (outside corridor [0.69, 1.44]) - should trigger exit
        print("\n--- SCENARIO B: Volatility Event (Price ratio breaches breakeven corridor) ---")
        url_crash = "http://127.0.0.1:8088/mcp/evaluate?apy=0.20&price_ratio=0.60&days_held=30"
        evaluation_crash = agent.query_oracle(url_crash)
        if evaluation_crash:
            agent.execute_risk_mitigation(evaluation_crash)
    finally:
        # Terminate gateway
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    main()
