# Arsenal Decision Engine — Decision Intelligence Layer

[![MCP Server](https://img.shields.io/badge/MCP-Server-blue?logo=modelcontextprotocol)](https://api.arsenal-quant.com/.well-known/mcp/server-card.json)
[![L402 Paywall](https://img.shields.io/badge/Payment-L402%20Lightning-orange)](./AGENTS.md#mcp-integration-pay-per-decision-via-l402)
[![DeFAI Ready](https://img.shields.io/badge/DeFAI-MEV%20%7C%20IL%20%7C%20Funding%20Rate-purple)](./AGENTS.md)
[![Latency](https://img.shields.io/badge/P99%20Latency-%3C%2015ms-brightgreen)]()

> **For A2A / DeFi agent integration → see [AGENTS.md](./AGENTS.md)**

> **Mission**: Transform economic uncertainty into actionable decisions.

An API that consumes raw text (news, RSS feeds, market data) and returns
machine-parseable **decision signals** — not data dumps. Built for autonomous
agents operating in the A2A economy.

```json
{
  "signal":           "EXECUTE",
  "value":            80,
  "volatility":       "EXTREME",
  "confidence_score": 0.9,
  "context":          "Routes:suez_europe Risk:80 Carriers:maersk,msc",
  "source":           "Arsenal Decision Engine v1.0"
}
```

---

## What This Engine Does

The Decision Intelligence Layer covers three economic domains:

| Domain | What it detects | Output signal |
|---|---|---|
| **Market Psychology** | Fear/Greed in financial news | `EXECUTE` / `HEDGE` / `DELAY` |
| **Maritime Freight** | Disruption risk per corridor + True Price | `ALERT` / `MONITOR` / `HEDGE` |
| **DeFi Arbitrage** | R_net vs flash loan cost (6-filter matrix) | `EXECUTE` / `HEDGE` / `DELAY` |

The engine does **not** expose raw scores. Every response is a decision.

---

## Signal Reference

All endpoints return the **§4 Standard Decision Output**. Read `signal` first:

| Signal | Meaning | Recommended agent action |
|---|---|---|
| `EXECUTE` | All conditions confirmed, positive expected value | Proceed if `confidence_score` ≥ 0.85 |
| `HEDGE` | Negative expected value or extreme fear | Exit / protect positions |
| `DELAY` | Insufficient signal or conditions misaligned | Re-evaluate in 15–60 min |
| `ALERT` | Urgent disruption detected | Escalate immediately |
| `MONITOR` | Neutral — no immediate action needed | Schedule re-evaluation |

**Confidence gating rule** (mandatory for autonomous agents):
```
confidence_score >= 0.85  → autonomous execution permitted
confidence_score <  0.60  → human review required
arbitration_required=true → human review mandatory (overrides score)
```

---

## Quick Start

### 1. Get an API Key

Contact the provisioning endpoint or subscribe via the billing portal.

### 2. Analyze a news headline

```bash
curl -X POST https://api.arsenal-quant.com/analyze \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"text": "Markets crash in panic sell-off. Banks face bankruptcy amid recession fears."}'
```

**Response:**
```json
{
  "value": 10,
  "change_pct": 0.0,
  "volatility": "HIGH",
  "trend": "DOWN",
  "confidence_score": 0.9,
  "signal": "HEDGE",
  "context": "Bull:0 Bear:3 Net:-3 Hits:3",
  "data_freshness_seconds": 0,
  "source": "Arsenal Decision Engine v1.0"
}
```

### 3. Maritime freight risk

```bash
curl -X POST https://api.arsenal-quant.com/analyze/maritime \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Houthi missile strikes in Red Sea. Maersk rerouting via Cape of Good Hope.",
    "zone": "suez_europe"
  }'
```

### 4. DeFi arbitrage evaluation

```bash
curl -X POST https://api.arsenal-quant.com/analyze/arbitrage \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "entry_price_usd": 100.0,
    "exit_price_usd": 115.0,
    "stop_loss_price_usd": 95.0,
    "position_size_usd": 10000.0,
    "gross_yield_usd": 1500.0,
    "gas_usd": 8.0,
    "flash_loan_amount_usd": 10000.0,
    "atr_values": [1.2, 1.5, 1.8],
    "resistance_level_usd": 98.0,
    "candle_close_4h_usd": 101.5,
    "volume_24h": 5500000,
    "volume_sma_20": 3000000,
    "volume_stddev": 1200000
  }'
```

---

## Authentication

### REST Endpoints (`/analyze/*`, `/pulse`)

All REST endpoints require an API key:

```http
X-API-Key: YOUR_SUBSCRIPTION_KEY
```

### MCP Tool Execution (`/mcp/v1/tools/execute`)

The MCP execution endpoint uses the **L402 Lightning Network protocol** for
pay-per-decision billing.

---

## L402 Monetization — How It Works

The `/mcp/v1/tools/execute` endpoint implements native A2A paywall using
the L402 protocol (RFC-compatible Lightning Network authentication).

### The Payment Flow

```
┌─────────────────┐         ┌──────────────────────────┐
│   AI Agent      │         │   Decision Intelligence  │
│   (Caller)      │         │   Layer (This API)       │
└────────┬────────┘         └──────────┬───────────────┘
         │                              │
         │  POST /mcp/v1/tools/execute  │
         │  (no Authorization header)   │
         │─────────────────────────────▶│
         │                              │
         │  HTTP 402 Payment Required   │
         │  WWW-Authenticate: L402      │
         │    macaroon="<token>"        │
         │    invoice="lnbc150n1p..."   │
         │◀─────────────────────────────│
         │                              │
         │  [Agent pays Lightning       │
         │   invoice via wallet]        │
         │  preimage obtained           │
         │                              │
         │  POST /mcp/v1/tools/execute  │
         │  Authorization: L402         │
         │    <macaroon>:<preimage>     │
         │─────────────────────────────▶│
         │                              │
         │  HTTP 200 — Tool output      │
         │  §4 Decision JSON            │
         │◀─────────────────────────────│
```

### Pricing Model

| Access tier | Method | Price | Scope |
|---|---|---|---|
| **Pay-per-decision** | L402 Lightning | **$0.15 / call** | `/mcp/v1/tools/execute` |
| **Subscription** | API Key | Negotiated | All REST `/analyze/*` endpoints |

### L402 Integration — Agent Code Examples

**Python (with L402 library):**
```python
import httpx

# Step 1: Request (will return 402)
resp = httpx.post(
    "https://api.arsenal-quant.com/mcp/v1/tools/execute",
    json={"name": "analyze_maritime_freight_risk", "arguments": {"text": "Suez disruption"}}
)

if resp.status_code == 402:
    # Step 2: Parse WWW-Authenticate header
    auth_header = resp.headers["WWW-Authenticate"]
    # macaroon and invoice extracted from: L402 macaroon="...", invoice="lnbc..."
    invoice = parse_l402_header(auth_header)["invoice"]

    # Step 3: Pay the Lightning invoice (via your wallet API)
    preimage = pay_lightning_invoice(invoice)
    macaroon = parse_l402_header(auth_header)["macaroon"]

    # Step 4: Retry with proof of payment
    resp = httpx.post(
        "https://api.arsenal-quant.com/mcp/v1/tools/execute",
        headers={"Authorization": f"L402 {macaroon}:{preimage}"},
        json={"name": "analyze_maritime_freight_risk", "arguments": {"text": "Suez disruption"}}
    )

decision = resp.json()
print(decision["content"][0]["text"])
```

**LangChain Tool (subscription key):**
```python
from langchain.tools import Tool
import requests

def analyze_maritime(text: str, zone: str = None) -> dict:
    """
    Analyzes maritime freight disruption risk. Returns signal=ALERT if freight
    rates will surge. signal=HEDGE if unusual drop detected. signal=MONITOR if stable.
    Always read confidence_score before acting — threshold for autonomous action: 0.85.
    """
    payload = {"text": text}
    if zone:
        payload["zone"] = zone
    resp = requests.post(
        "https://api.arsenal-quant.com/analyze/maritime",
        headers={"X-API-Key": "YOUR_KEY"},
        json=payload
    )
    return resp.json()

maritime_tool = Tool(
    name="analyze_maritime_freight_risk",
    func=analyze_maritime,
    description=analyze_maritime.__doc__
)
```

**Google ADK (MCP auto-discovery):**
```python
from google.adk.tools import MCPToolset

# ADK fetches the server card and auto-registers all tools
toolset = MCPToolset.from_server_card(
    url="https://api.arsenal-quant.com/.well-known/mcp/server-card.json",
    auth={"type": "api_key", "value": "YOUR_KEY"}
)
# Tools available: analyze_market_psychology, analyze_maritime_freight_risk,
#                  compare_freight_corridors, evaluate_arbitrage_opportunity
```

---

## API Reference

### Full Specification

OpenAPI 3.1.0 spec: [`openapi.yaml`](./openapi.yaml)

MCP Server Card: [`mcp-server.json`](./mcp-server.json)
— also served live at `GET /.well-known/mcp/server-card.json`

### Endpoints

| Method | Path | Description | Auth |
|---|---|---|---|
| `POST` | `/analyze` | Market Psychology Index (Fear/Greed) | API Key |
| `POST` | `/analyze/maritime` | Maritime freight risk per corridor | API Key |
| `POST` | `/analyze/compare` | True Price corridor comparison (Transpacific vs Suez) | API Key |
| `POST` | `/analyze/arbitrage` | DeFi arbitrage decision (6-filter matrix + R_net) | API Key |
| `GET`  | `/pulse` | Live market pulse event feed | API Key |
| `GET`  | `/mcp/v1/tools` | MCP tool registry | API Key |
| `POST` | `/mcp/v1/tools/execute` | MCP tool execution — pay-per-decision | L402 |
| `GET`  | `/.well-known/mcp/server-card.json` | MCP discovery (no auth) | None |

---

## Deployment

### Docker (recommended)

```bash
cp .env.example .env
# Edit .env: set ENGINE_API_KEY, LIGHTNING_API_KEY, LIGHTNING_URL
docker compose up -d
```

The stack includes:
- **Decision Intelligence Layer** (FastAPI on port 8002)
- **Lightning Hub** (Alby Hub on port 8080 — for L402 invoice generation)
- **Cloudflare Tunnel** (public HTTPS exposure — no port forwarding required)

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ENGINE_API_KEY` | ✅ | Primary subscription key for REST endpoints |
| `LIGHTNING_API_KEY` | For L402 | API key for the Lightning wallet backend |
| `LIGHTNING_URL` | For L402 | Lightning wallet API URL (default: demo instance) |
| `SENSOR_INTERVAL` | No | RSS scan interval in seconds (default: 900) |
| `PORT` | No | Exposed port (default: 8002) |

---

## Architecture

```
External News / RSS Feeds
          │
          ▼
  ┌───────────────────┐
  │  Autonomous       │  Scans feeds every 15min
  │  Execution Core   │  Detects critical signals (risk > 65 or < 35)
  │  (RSS Sensor)     │  Writes to MARKET_PULSE.json
  └───────┬───────────┘
          │
          ▼
  ┌───────────────────────────────────────────────────────┐
  │            Decision Intelligence Layer                 │
  │                                                       │
  │  ┌─────────────────┐  ┌──────────────────────────┐   │
  │  │ Market Psychology│  │ Autonomous Execution Core│   │
  │  │ Index Engine     │  │ Maritime Module          │   │
  │  │ (Fear/Greed)     │  │ (Freight Risk + Pricing) │   │
  │  └─────────────────┘  └──────────────────────────┘   │
  │                                                       │
  │  ┌─────────────────────────────────────────────────┐  │
  │  │ Autonomous Execution Core — Arbitrage Module    │  │
  │  │ (6-filter quant. matrix + R_net + FL cost)      │  │
  │  └─────────────────────────────────────────────────┘  │
  │                                                       │
  │  ┌──────────────────────────────────────────────────┐ │
  │  │ Payment Gateway (L402 interface — §9)            │ │
  │  │ Current impl: L402/Lightning. Swappable to x402. │ │
  │  └──────────────────────────────────────────────────┘ │
  └───────────────────────────────────────────────────────┘
          │
          ▼
  HTTP REST + MCP Bridge
  (FastAPI · Port 8002 · <2ms p95 latency)
```

**Performance target**: < 15ms end-to-end for all decision endpoints.
**Optimization**: O(1) set operations — no external NLP models, no GPU required.

---

## A2A Compatibility

| Framework | Integration method | Status |
|---|---|---|
| **Google ADK** | MCP auto-discovery via server card | ✅ Compatible |
| **LangChain** | Tool wrapper or direct HTTP | ✅ Compatible |
| **Composio** | MCP connector | ✅ Compatible |
| **AutoGen** | Function calling / HTTP | ✅ Compatible |
| **Claude** | MCP tool use | ✅ Compatible |
| **x402** | Future — interface ready (§9 PaymentGateway) | 🔬 Planned |

---

*Arsenal Decision Engine — Decision Intelligence Layer v4.1.0*
*"Transform economic uncertainty into actionable decisions."*
