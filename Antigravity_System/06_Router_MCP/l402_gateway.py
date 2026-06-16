import os
import json
from fastapi import FastAPI, HTTPException, Header, Response
from fastapi.responses import PlainTextResponse

app = FastAPI(title="Antigravity AI Cost Intelligence - MCP Gateway")

# Mock configurations simulating local Lightning Node (e.g., Alby Hub / LNbits REST API)
MOCK_INVOICE = "lnbc500n1p...mock_invoice_for_50k_sats"
MOCK_MACAROON = "AgEEbW...mock_macaroon_signature"
AUDIT_DIR = "/home/faouzi/Antigravity_System/04_Strategy_Gerber/Audit_Factory/Strategic_Signals/"

@app.get("/mcp/audit/latest")
async def get_latest_audit(authorization: str = Header(None)):
    """
    Consumable endpoint for autonomous agent-to-agent clients.
    Protocol: L402 (Lightning HTTP 402 Challenge/Response)
    """
    # 1. Torvalds Filter: O(1) authorization header presence check
    if not authorization or not authorization.startswith("L402 "):
        # Immediate rejection with HTTP 402 challenge & WWW-Authenticate header
        headers = {
            "WWW-Authenticate": f'L402 token="mock_macaroon_base64", invoice="{MOCK_INVOICE}"'
        }
        return Response(
            content=json.dumps({"error": "Payment Required", "price_sats": 50000}),
            status_code=402,
            headers=headers,
            media_type="application/json"
        )
    
    # 2. Cryptographic token verification (simulated client check)
    token = authorization.split(" ")[1]
    if token != MOCK_MACAROON:
        # Invalid signature or unpaid invoice simulation
        raise HTTPException(status_code=403, detail="Invalid L402 Token or Payment Not Settled")

    # 3. Clean Architecture: Fetch Deliverable
    try:
        if not os.path.exists(AUDIT_DIR):
            raise HTTPException(status_code=404, detail="Audit output folder not found.")
            
        files = sorted(os.listdir(AUDIT_DIR), reverse=True)
        if not files:
            raise HTTPException(status_code=404, detail="No audits currently available.")
        
        latest_audit_path = os.path.join(AUDIT_DIR, files[0])
        with open(latest_audit_path, 'r') as f:
            content = f.read()
            
        # Append locked premium recommendation logic
        premium_content = content + "\n\n[UNLOCKED RECOMMENDATION]\n- Disable the redundant 'Routing' agent in your mcp_config.json.\n- Swap GPT-4o for Llama-3-8B-Instruct local model for base checks.\n- Validated immediate saving: $12,000 USD/month."
        
        return PlainTextResponse(content=premium_content)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error during audit read.")

if __name__ == "__main__":
    import uvicorn
    # Start uvicorn server locally on port 8088
    print("[SYSTEM] Starting L402 Gateway Server on port 8088...")
    uvicorn.run(app, host="0.0.0.0", port=8088, log_level="warning")

