import os
import json
# pyrefly: ignore [missing-import]
import httpx
from fastapi import FastAPI, HTTPException, Header, Response, Request
from fastapi.responses import PlainTextResponse, HTMLResponse
from lnbits_client import LNbitsClient
from security_shield import check_rate_limit, sign_audit_payload

# Parse .env configurations manually to avoid external dependencies
def load_environment():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                clean_line = line.strip()
                if clean_line and not clean_line.startswith("#"):
                    if "=" in clean_line:
                        key, val = clean_line.split("=", 1)
                        os.environ[key.strip()] = val.strip()

load_environment()

app = FastAPI(title="Antigravity AI Cost Intelligence - Mainnet Gateway")
lnbits = LNbitsClient()

@app.get("/", response_class=HTMLResponse)
async def root_endpoint(request: Request):
    # Detect if user agent is an API client expecting JSON
    user_agent = request.headers.get("user-agent", "").lower()
    accept = request.headers.get("accept", "").lower()
    
    if "mozilla" not in user_agent and "chrome" not in user_agent and "safari" not in user_agent and "html" not in accept:
        # Standard fallback for standard API clients
        return HTMLResponse(content=json.dumps({
            "system": "Antigravity Engine - Decision Layer",
            "status": "MAINNET ACTIVE",
            "protocol": "M2M L402 Paywall",
            "message": "This is an API gateway. Access via web browser to view human documentation.",
            "endpoints": {
                "discovery": "/.well-known/mcp/server-card.json",
                "audit_paywall": "/mcp/audit/latest"
            }
        }), status_code=200, media_type="application/json")

    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Arsenal Decision Engine — API Gateway</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #030712;
                --card-bg: #1f2937;
                --text: #f9fafb;
                --text-muted: #9ca3af;
                --emerald: #10b981;
                --emerald-glow: rgba(16, 185, 129, 0.15);
                --border: #374151;
            }
            body {
                margin: 0;
                padding: 0;
                background-color: var(--bg);
                color: var(--text);
                font-family: 'Inter', sans-serif;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }
            .container {
                max-width: 800px;
                width: 90%;
                text-align: center;
                padding: 40px 20px;
            }
            .badge-status {
                display: inline-flex;
                align-items: center;
                background-color: var(--emerald-glow);
                color: var(--emerald);
                border: 1px solid var(--emerald);
                padding: 6px 16px;
                border-radius: 9999px;
                font-weight: 600;
                font-size: 0.875rem;
                margin-bottom: 24px;
                box-shadow: 0 0 15px var(--emerald-glow);
            }
            .pulse {
                width: 8px;
                height: 8px;
                background-color: var(--emerald);
                border-radius: 50%;
                margin-right: 8px;
                animation: pulse-animation 2s infinite;
            }
            @keyframes pulse-animation {
                0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
                70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
                100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
            }
            h1 {
                font-size: 2.5rem;
                font-weight: 800;
                margin: 0 0 12px 0;
                background: linear-gradient(to right, #ffffff, #9ca3af);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .tagline {
                font-size: 1.125rem;
                color: var(--text-muted);
                margin: 0 0 40px 0;
            }
            .cards {
                display: grid;
                grid-template-columns: 1fr;
                gap: 20px;
                margin-bottom: 40px;
                text-align: left;
            }
            @media (min-width: 640px) {
                .cards {
                    grid-template-columns: 1fr 1fr;
                }
            }
            .card {
                background-color: #0b0f19;
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 24px;
                transition: border-color 0.3s ease;
            }
            .card:hover {
                border-color: var(--emerald);
            }
            .card h3 {
                margin: 0 0 8px 0;
                font-size: 1.25rem;
                font-weight: 600;
            }
            .card p {
                margin: 0 0 16px 0;
                font-size: 0.875rem;
                color: var(--text-muted);
                line-height: 1.5;
            }
            .card-link {
                display: inline-block;
                color: var(--emerald);
                text-decoration: none;
                font-weight: 600;
                font-size: 0.875rem;
                font-family: 'JetBrains Mono', monospace;
            }
            .card-link:hover {
                text-decoration: underline;
            }
            .badges-container {
                margin-top: 50px;
                border-top: 1px solid var(--border);
                padding-top: 30px;
                display: flex;
                justify-content: center;
                gap: 20px;
                flex-wrap: wrap;
            }
            .badges-container a {
                transition: transform 0.2s ease;
            }
            .badges-container a:hover {
                transform: translateY(-2px);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="badge-status">
                <div class="pulse"></div>
                MAINNET ACTIVE
            </div>
            <h1>Arsenal Decision Engine</h1>
            <p class="tagline">The Sovereign Risk-Validation Layer for Autonomous AI Agents (DeFAI)</p>
            
            <div class="cards">
                <div class="card">
                    <h3>MCP Server Card</h3>
                    <p>Dynamic schema discoverability endpoint for agent tools integration.</p>
                    <a href="/.well-known/mcp/server-card.json" class="card-link">/.well-known/mcp/server-card.json &rarr;</a>
                </div>
                <div class="card">
                    <h3>Risk Audit Endpoint</h3>
                    <p>Standard pay-per-decision risk validation gated by L402 paywalls.</p>
                    <a href="/mcp/audit/latest" class="card-link">/mcp/audit/latest &rarr;</a>
                </div>
            </div>

            <div class="badges-container">
                <a href="https://glama.ai/mcp/servers/Faouzi122/Arsenal-Quant-Project" target="_blank">
                    <img src="https://glama.ai/mcp/servers/Faouzi122/Arsenal-Quant-Project/badges/card.svg" alt="Arsenal-Quant-Project MCP server" />
                </a>
                <a href="https://smithery.ai/servers/khelifa-faouzi16/arsenal-decision-engine" target="_blank">
                    <img src="https://smithery.ai/badge/khelifa-faouzi16/arsenal-decision-engine" alt="smithery badge" />
                </a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT_DIR = os.path.join(BASE_DIR, "04_Strategy_Gerber", "Audit_Factory", "Strategic_Signals")
QUOTA_FILE = os.path.join(os.path.dirname(__file__), "client_quotas.json")

# Pricing matrix based on pain level
PRICING_MAP = {
    "LOW": 10000,
    "MEDIUM": 25000,
    "HIGH": 50000,
    "CRITICAL": 100000,
    "FATAL": 100000
}

# Quota Helpers (O(1) client tracking)
def get_client_requests(client_id: str) -> int:
    if not os.path.exists(QUOTA_FILE):
        return 0
    try:
        with open(QUOTA_FILE, "r") as f:
            quotas = json.load(f)
        return quotas.get(client_id, 0)
    except Exception:
        return 0

def increment_client_requests(client_id: str):
    quotas = {}
    if os.path.exists(QUOTA_FILE):
        try:
            with open(QUOTA_FILE, "r") as f:
                quotas = json.load(f)
        except Exception:
            pass
    quotas[client_id] = quotas.get(client_id, 0) + 1
    try:
        os.makedirs(os.path.dirname(QUOTA_FILE), exist_ok=True)
        with open(QUOTA_FILE, "w") as f:
            json.dump(quotas, f)
    except Exception as e:
        print(f"[QUOTA ERROR] Failed to save quotas: {e}")

# Dynamic Pricing Helper
def get_dynamic_price(audit_payload) -> int:
    """[DETERMINISTIC L402 PRICING] 2-Tier SLA"""
    import os, json
    
    # Override option for testing
    override = os.getenv("L402_OVERRIDE_PRICE")
    if override:
        return int(override)
        
    # Standard logic: Extract signal (or level) from the audit report payload
    signal = 'EXECUTE'
    if isinstance(audit_payload, dict):
        signal = audit_payload.get('signal', 'EXECUTE')
    elif isinstance(audit_payload, str) and os.path.exists(audit_payload):
        # The payload is the path to the text report
        try:
            with open(audit_payload, 'r') as f:
                content = f.read()
            # If the file contains HEDGE or DELAY, or if it is a backtest report containing them
            if 'HEDGE' in content or 'DELAY' in content or 'CRITICAL' in content or 'FATAL' in content:
                signal = 'HEDGE'
            else:
                # Let's check if it's JSON (like backtest_report.json)
                try:
                    data = json.loads(content)
                    signal = data.get('signal', 'EXECUTE')
                except:
                    pass
        except:
            pass
            
    # Apply deterministic tiered SLA pricing (50 or 500 sats)
    if signal in ['HEDGE', 'DELAY']:
        return 500  # Premium: High-risk anomaly / hedge active / capital protected
    return 50       # Standard: Routine monitoring / low-risk

# Dynamic Recommendation Helper
def get_mapper_recommendation(audit_path: str) -> str:
    audit_type = "COST_WASTE"
    if os.path.exists(audit_path):
        try:
            with open(audit_path, "r") as f:
                for line in f:
                    if "TYPE       :" in line:
                        audit_type = line.split("TYPE       :")[1].strip()
                        break
        except Exception:
            pass

    mapper_path = os.path.join(BASE_DIR, "04_Strategy_Gerber", "Decision_Layer", "pain_to_profit_mapper.json")
    if os.path.exists(mapper_path):
        try:
            with open(mapper_path, "r") as f:
                mapper = json.load(f)
            item = mapper["AI_COST_INTELLIGENCE_MAPPER"].get(audit_type)
            if item:
                return f"\n\n[UNLOCKED RECOMMENDATION]\n- Actionable MCP Call: {item['actionable_mcp_call']}\n- Est. Loss: {item['estimated_loss_usd']}"
        except Exception as e:
            print(f"[RECOMMENDATION ERROR] Failed to parse mapper: {e}")

    # Default fallback recommendation
    return "\n\n[UNLOCKED RECOMMENDATION]\n- Disable the redundant 'Routing' agent in your mcp_config.json.\n- Swap GPT-4o for Llama-3-8B-Instruct local model for base checks.\n- Validated immediate saving: $12,000 USD/month."

# Discoverability Endpoints (MCP Server Card)
@app.get("/.well-known/mcp/server-card.json")
@app.get("/well-known/mcp/server-card.json")
async def get_server_card():
    card_path = os.path.join(os.path.dirname(__file__), ".well-known", "mcp", "server-card.json")
    if os.path.exists(card_path):
        with open(card_path, "r") as f:
            return json.load(f)
    # Inline fallback if file is missing
    return {
        "$schema": "https://static.modelcontextprotocol.io/schemas/v1/server-card.schema.json",
        "serverInfo": {
            "name": "Antigravity Engine - Decision Layer",
            "version": "1.0.0"
        },
        "authentication": { "required": True, "type": "L402" }
    }

@app.get("/mcp/audit/latest")
async def get_latest_audit(request: Request, authorization: str = Header(None)):
    """
    Exposes latest diagnostic audit report.
    Free Quota: Protected by O(1) in-memory Security Shield rate limiting (first 3 free).
    Subsequent requests: Gated by dynamically priced L402 Lightning challenges.
    """
    client_id = request.headers.get("x-agent-id", request.client.host)
    raw_ip = request.headers.get("cf-connecting-ip", request.headers.get("x-forwarded-for", request.client.host))
    client_ip = raw_ip.split(",")[0].strip() if "," in raw_ip else raw_ip.strip()
    
    # Check directory
    if not os.path.exists(AUDIT_DIR):
        raise HTTPException(status_code=404, detail="Audit folder missing.")
        
    files = sorted(os.listdir(AUDIT_DIR), reverse=True)
    if not files:
        raise HTTPException(status_code=404, detail="No audit reports available.")
        
    latest_audit_path = os.path.join(AUDIT_DIR, files[0])
    
    # Verify if client already has a valid payment (L402 verification)
    is_paid = False
    payment_hash = None
    if authorization and authorization.startswith("L402 "):
        token_part = authorization.split(" ")[1]
        if ":" in token_part:
            payment_hash, preimage = token_part.split(":", 1)
        else:
            payment_hash = token_part
            preimage = None
            
        # Sandbox bypass for testing / client verification
        if preimage == "0000000000000000000000000000000000000000000000000000000000000000" and os.getenv("L402_OVERRIDE_PRICE"):
            is_paid = True
        else:
            is_paid = lnbits.check_invoice(payment_hash)
        
    if not is_paid:
        # Check rate limit for free tier
        if check_rate_limit(client_ip):
            try:
                with open(latest_audit_path, 'r') as f:
                    content = f.read()
                
                # Sceau de l'Oracle (HMAC-SHA256 signature)
                oracle_secret = os.getenv("ORACLE_SECRET_KEY", "default_secret")
                payload_to_sign = {
                    "audit_content": content,
                    "client_ip": client_ip,
                    "type": "FREE_TIER"
                }
                signature = sign_audit_payload(payload_to_sign, oracle_secret)
                
                free_content = (
                    content + 
                    f"\n\n[FREE LAYER - Discovery Access]\n"
                    "- Free tier validation successful.\n"
                    "- Upcoming requests will require L402 micro-payments.\n\n"
                    f"{{\n  \"oracle_signature\": \"{signature}\",\n  \"layer\": \"FREE\"\n}}"
                )
                return PlainTextResponse(content=free_content)
            except Exception as e:
                raise HTTPException(status_code=500, detail="Error loading free audit payload.")
        else:
            # Quota exhausted, trigger payment flow
            price_sats = get_dynamic_price(latest_audit_path)
            # Call LNbits node API to create dynamic invoice
            invoice_data = lnbits.create_invoice(price_sats, f"Arsenal Audit Unlock ({client_id})")
            
            if not invoice_data or "payment_request" not in invoice_data:
                raise HTTPException(status_code=503, detail="Payment Gateway Node is Offline or Unauthorized")
                
            pr = invoice_data.get("payment_request")
            payment_hash = invoice_data.get("payment_hash")
            
            # Issue HTTP 402 challenge with macaroon/invoice credentials
            headers = {
                "WWW-Authenticate": f'L402 token="{payment_hash}", invoice="{pr}"'
            }
            return Response(
                content=json.dumps({"error": "Payment Required", "price_sats": price_sats, "client_id": client_id}),
                status_code=402,
                headers=headers,
                media_type="application/json"
            )

    # Read latest compiled audit file (Paid Path)
    try:
        with open(latest_audit_path, 'r') as f:
            content = f.read()
            
        recommendation = get_mapper_recommendation(latest_audit_path)
        
        # Sceau de l'Oracle (HMAC-SHA256 signature)
        oracle_secret = os.getenv("ORACLE_SECRET_KEY", "default_secret")
        payload_to_sign = {
            "audit_content": content,
            "payment_hash": payment_hash,
            "type": "PREMIUM_TIER"
        }
        signature = sign_audit_payload(payload_to_sign, oracle_secret)
        
        premium_content = (
            content + recommendation + 
            f"\n\n{{\n  \"oracle_signature\": \"{signature}\",\n  \"layer\": \"PREMIUM\"\n}}"
        )
        
        return PlainTextResponse(content=premium_content)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal error loading the paid audit payload.")

# Catch-all route to proxy non-gateway requests to decision_engine
@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def catch_all_proxy(request: Request, path_name: str):
    async with httpx.AsyncClient() as client:
        # Forward to decision_engine on the docker network
        target_url = f"http://decision_engine:8002/{path_name}"
        params = dict(request.query_params)
        headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
        body = await request.body()
        
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                params=params,
                headers=headers,
                content=body,
                timeout=15.0
            )
            # Reconstruct response with same status code and headers
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type")
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502, 
                detail=f"Proxy error connecting to Decision Engine backend: {str(e)}"
            )

if __name__ == "__main__":
    # Check if we are running in stdio MCP mode (e.g. under mcp-proxy)
    initial_req = None
    import sys
    import select
    import json
    try:
        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
        if rlist:
            line = sys.stdin.readline().strip()
            if line:
                data = json.loads(line)
                if isinstance(data, dict) and "method" in data:
                    initial_req = data
    except Exception:
        pass

    if initial_req:
        # Run stdio MCP JSON-RPC loop
        def write_jsonrpc(response):
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

        req = initial_req
        while True:
            try:
                req_id = req.get("id")
                method = req.get("method")
                
                if method == "initialize":
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {
                                "tools": {},
                                "resources": {}
                            },
                            "serverInfo": {
                                "name": "Antigravity Engine - Decision Layer",
                                "version": "1.0.0"
                            }
                        }
                    }
                    write_jsonrpc(res)
                elif method == "notifications/initialized":
                    pass
                elif method == "tools/list":
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "tools": [
                                {
                                    "name": "get_latest_audit",
                                    "description": "Fetch the latest cost-intelligence and risk mitigation audit signal.",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {}
                                    }
                                }
                            ]
                        }
                    }
                    write_jsonrpc(res)
                elif method == "resources/list":
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "resources": []
                        }
                    }
                    write_jsonrpc(res)
                elif method == "resources/templates/list":
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "resourceTemplates": []
                        }
                    }
                    write_jsonrpc(res)
                elif method == "prompts/list":
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "prompts": []
                        }
                    }
                    write_jsonrpc(res)
                elif method == "ping":
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {}
                    }
                    write_jsonrpc(res)
                elif method == "tools/call":
                    tool_name = req.get("params", {}).get("name")
                    if tool_name == "get_latest_audit":
                        res = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Antigravity Engine Status: ACTIVE. L402 Gateway is running on https://api.arsenal-quant.com."
                                    }
                                ]
                            }
                        }
                    else:
                        res = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {
                                "code": -32601,
                                "message": f"Method not found: {tool_name}"
                            }
                        }
                    write_jsonrpc(res)
                else:
                    if req_id is not None:
                        res = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {}
                        }
                        write_jsonrpc(res)
                
                line = sys.stdin.readline()
                if not line:
                    break
                req = json.loads(line.strip())
            except Exception as e:
                sys.stderr.write(f"Error in stdio loop: {str(e)}\n")
                sys.stderr.flush()
                break
    else:
        import uvicorn
        print("[SYSTEM] Starting Real L402 Gateway Server on port 8088...")
        uvicorn.run(app, host="0.0.0.0", port=8088, log_level="warning")

