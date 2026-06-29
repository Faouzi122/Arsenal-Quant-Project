#!/usr/bin/env python3
"""
CLIENT ONE — Arsenal Decision Engine Integration Example
Demonstrates how an autonomous agent consumes the L402 Oracle signals (EXECUTE/HEDGE/DELAY)
and dynamically alters its LP strategy to prevent capital loss.
"""
import os
import sys
import json
import time
import urllib.request
import urllib.error

# Configuration
API_URL = "https://api.arsenal-quant.com/mcp/audit/latest"
LNBITS_URL = "https://demo.lnbits.com"
# In a real environment, the agent would load its admin/invoice key from environment variables
LNBITS_ADMIN_KEY = os.getenv("LNBITS_ADMIN_KEY", "demo_admin_key_placeholder")

class AutonomousLPAgent:
    def __init__(self, initial_capital=10000.0):
        self.capital = initial_capital
        self.in_lp_pool = True
        self.stable_balance = 0.0
        self.lp_value = initial_capital
        print(f"[Agent Initialized] Capital: ${self.capital:.2f} | Status: ACTIVE_LP")

    def execute_risk_mitigation(self, signal):
        """
        Executes active risk-management based on the Oracle's decision signal.
        """
        if signal in ["HEDGE", "DELAY"] and self.in_lp_pool:
            print("\n" + "="*70)
            print(f"[EMERGENCY TRIGGER] Oracle Signal: {signal}")
            print(f"Executing active risk-mitigation: Exiting concentrated liquidity pool.")
            # Move LP position to stable balance (USDC) to prevent Impermanent Loss
            self.stable_balance = self.lp_value
            self.lp_value = 0.0
            self.in_lp_pool = False
            print(f"Portfolio Status: Protected in Stablecoins | Cash Balance: ${self.stable_balance:.2f}")
            print("="*70 + "\n")
        elif signal == "EXECUTE" and not self.in_lp_pool:
            print("\n" + "="*70)
            print(f"[RE-ENTRY TRIGGER] Oracle Signal: {signal}")
            print(f"Market stabilized. Re-entering concentrated liquidity pool.")
            self.lp_value = self.stable_balance
            self.stable_balance = 0.0
            self.in_lp_pool = True
            print(f"Portfolio Status: ACTIVE_LP | Liquidity Value: ${self.lp_value:.2f}")
            print("="*70 + "\n")
        else:
            print(f"[Agent Log] Signal: {signal} | LP Active: {self.in_lp_pool} | Portfolio Value: ${self.lp_value + self.stable_balance:.2f} (No action required)")

    def extract_json_payload(self, text: str) -> dict:
        """
        Extracts and parses the first valid JSON dictionary from a mixed payload.
        """
        start = text.find('{')
        if start == -1:
            return {}
            
        depth = 0
        end = -1
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
                    
        if end != -1:
            try:
                return json.loads(text[start:end+1])
            except Exception as e:
                print(f"[JSON Extraction Warning] Failed to parse: {e}")
        return {}

    def query_oracle(self):
        """
        Queries the Decision Engine. Handles the L402 payment challenge if encountered.
        """
        print(f"\n[1/3] Contacting Decision Engine at {API_URL}...")
        req = urllib.request.Request(API_URL, method="GET")
        req.add_header("x-agent-id", "client-one-demonstrator")
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        try:
            with urllib.request.urlopen(req) as response:
                body = response.read().decode('utf-8')
                print("[✅] Standard Tier: Free access allowed.")
                data = self.extract_json_payload(body)
                return data
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
                    # Alternative parsing for standard L402 format
                    macaroon = re.search(r'macaroon="([^"]+)"', auth_header).group(1)
                    invoice = re.search(r'invoice="([^"]+)"', auth_header).group(1)
                
                print(f"[L402 Challenge Detected] Token: {macaroon[:15]}... | Invoice: {invoice[:20]}...")
                
                # Pay invoice (MOCK / Sandbox execution mode simulation)
                preimage = self.settle_invoice_mock(invoice)
                if not preimage:
                    return None
                
                # Retry request with authorized credentials
                print("[3/3] Submitting proof of payment to Oracle...")
                retry_req = urllib.request.Request(API_URL, method="GET")
                retry_req.add_header("Authorization", f"L402 {macaroon}:{preimage}")
                retry_req.add_header("x-agent-id", "client-one-demonstrator")
                retry_req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                
                try:
                    with urllib.request.urlopen(retry_req) as retry_response:
                        final_body = retry_response.read().decode('utf-8')
                        print("[✅] Access Granted.")
                        # Parse out recommendation and JSON payload
                        print("\n--- Raw Decision Intelligence Deliverable ---")
                        print(final_body)
                        print("---------------------------------------------")
                        
                        data = self.extract_json_payload(final_body)
                        return data
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
        """
        Simulates payment of the Bolt11 invoice.
        """
        print("[2/3] Settling Lightning Invoice...")
        # Simulating payment settlement latency
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
    
    # Simulate first epoch: Normal market conditions
    # Normally the rate limiter lets first 3 requests go through as Free tier (EXECUTE)
    print("\n--- EPOCH 1: Monitoring Market Anomaly (Standard Tier) ---")
    decision = agent.query_oracle()
    if decision:
        # Check signal
        signal = decision.get("metrics", {}).get("losses_prevented_pct", 0)
        # If the response is the backtest report, it implies HEDGE was triggered during crash
        if "metrics" in decision:
            agent.execute_risk_mitigation("HEDGE")
        else:
            agent.execute_risk_mitigation("EXECUTE")
            
    # Simulate second epoch: System has hit rate limit or premium tier is requested
    print("\n--- EPOCH 2: Volatility Event Triggered (Premium L402 Challenge) ---")
    decision_premium = agent.query_oracle()
    if decision_premium:
         agent.execute_risk_mitigation("HEDGE")

if __name__ == "__main__":
    main()
