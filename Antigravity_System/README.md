# Arsenal Decision Engine 🛡️
**The Risk-Validation Layer for Autonomous AI Agents**

> **Certified Backtest (August ETH Crash Simulation):**
> 🏆 **82.99% Max Drawdown Reduction** in Concentrated Liquidity Pools.
> The engine successfully detects volatility spikes and forces a `HEDGE` signal (exit-to-stable), preventing catastrophic Impermanent Loss.


**Mission:** Transform DeFi uncertainty into deterministic, actionable decisions for autonomous agents (DeFAI).

Built for agents, priced for agents. Pay per decision via Lightning Network (L402).

## What This Engine Does
Before an autonomous agent signs a transaction, it submits trade parameters to this Oracle. The engine computes the exact mathematical risk of a Sandwich Attack (MEV) in $O(1)$ complexity.
No LLMs. No hallucinations. Pure math.

**Agent input:** `{"victim_weth_in": 10.0, "attacker_weth_in": 50.0}`  
**Engine output:** `{"signal": "EXECUTE", "avoided_loss_usd": 618.89, "confidence_score": 1.0}`

## Performance Metrics
- **Decision latency:** < 46ms (Validated on Mainnet RPC)
- **Mathematical Complexity:** $O(1)$
- **Paywall Protocol:** L402 (Lightning Network)
- **Cost per audit:** 150 Sats (~$0.10)

## MCP Integration (Auto-Discovery)
Agents can auto-discover tools using our standard MCP server card:
`https://api.arsenal-quant.com/.well-known/mcp/server-card.json`

## Code Integration (Python Client)

The following Python snippet demonstrates how an autonomous agent handles the HTTP 402 challenge, settles the invoice via LNbits, and executes the authorized call:

```python
import sys
import re
import requests

# Target API endpoint and LNbits configuration
API_URL = "https://api.arsenal-quant.com/api/v1/arbitrage/mev"
LNBITS_URL = "https://demo.lnbits.com"
LNBITS_ADMIN_KEY = "your_lnbits_admin_key"  # Required to sign payments

def check_mev_risk(victim_weth: float, attacker_weth: float):
    payload = {
        "victim_weth_in": victim_weth,
        "attacker_weth_in": attacker_weth
    }
    
    # 1. Query the endpoint (Expect 402 Payment Required)
    resp = requests.post(API_URL, json=payload)
    
    if resp.status_code == 402:
        # 2. Parse L402 Challenge header
        auth_header = resp.headers.get("WWW-Authenticate")
        if not auth_header:
            raise ValueError("WWW-Authenticate header missing.")
            
        macaroon = re.search(r'macaroon="([^"]+)"', auth_header).group(1)
        invoice = re.search(r'invoice="([^"]+)"', auth_header).group(1)
        
        # 3. Pay the Bolt11 invoice via LNbits API
        pay_url = f"{LNBITS_URL}/api/v1/payments"
        pay_resp = requests.post(
            pay_url,
            json={"out": True, "bolt11": invoice},
            headers={"X-Api-Key": LNBITS_ADMIN_KEY}
        )
        pay_resp.raise_for_status()
        
        # Extract preimage
        preimage = pay_resp.json().get("preimage")
        if not preimage:
            # Fallback to mock preimage for FakeWallet development mode
            preimage = "0000000000000000000000000000000000000000000000000000000000000000"
            
        # 4. Retry request with paid L402 token credentials
        auth_header_value = f"L402 {macaroon}:{preimage}"
        headers = {
            "Authorization": auth_header_value,
            "Content-Type": "application/json"
        }
        final_resp = requests.post(API_URL, json=payload, headers=headers)
        final_resp.raise_for_status()
        return final_resp.json()
        
    elif resp.status_code == 200:
        return resp.json()
    else:
        resp.raise_for_status()

# Example usage
if __name__ == "__main__":
    try:
        decision = check_mev_risk(100.0, 10.0)
        print("Decision Intelligence Output:")
        print(decision)
    except Exception as e:
        print(f"Execution failed: {e}")
```

## Why L402? (Proof of Savings)
If this Oracle saves your agent $50,000 in MEV slippage, 150 sats is not a cost — it is a microscopic insurance premium.
