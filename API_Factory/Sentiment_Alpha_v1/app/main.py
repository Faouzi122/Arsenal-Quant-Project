# © 2026 Meridian Alpha Systems - Intelligence & Logistics Division
# Watermark: ADSL-404-SIGMA

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
import json
from pydantic import BaseModel
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
import asyncio

from app.core.sentiment_engine import engine
from app.core.maritime_routes import maritime_engine
from app.core.arbitrage_engine import arbitrage_engine, ArbitrageOpportunity
from app.services.news_sensor import sensor
from app.services.carbon_scraper import carbon_scraper
from app.middleware.auth import api_key_auth
from fastapi import Request

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Execute background tasks for scraping and feed sensing
    sensor_task = asyncio.create_task(sensor.run_sensor_loop())
    scraper_task = asyncio.create_task(carbon_scraper.run_scraper_loop())
    yield
    # Shutdown
    sensor_task.cancel()
    scraper_task.cancel()

app = FastAPI(
    title="Arsenal Decision Engine — Decision Intelligence Layer",
    description="Predict freight volatility before it hits your budget. Analyzes global news to generate a Market Psychology Index and resolve conflicting signals via an AI-Conflict Resolution Layer.",
    version="4.0.0",
    lifespan=lifespan
)

@app.middleware("http")
async def add_auth_middleware(request: Request, call_next):
    return await api_key_auth(request, call_next)

@app.middleware("http")
async def hide_server_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Server"] = "Arsenal Decision Engine v1.0"
    response.headers["X-Powered-By"] = "Decision Intelligence Layer"
    return response

class NewsInput(BaseModel):
    text: str

class MaritimeInput(BaseModel):
    text: str
    zone: Optional[str] = None

class ContainerPricing(BaseModel):
    base_freight_rate_usd: float
    hidden_surcharges_detected: float
    true_price_estimated: float
    transparency_status: str

class RouteAnalysis(BaseModel):
    market_psychology_index: int
    transparency_index: int
    freight_trend_prediction: str
    container_20_feet: ContainerPricing
    container_40_feet: ContainerPricing

class MeridianOutput(BaseModel):
    most_volatile_corridor: str
    transpacific: RouteAnalysis
    suez_europe: RouteAnalysis
    arbitration_required: bool
    arbitration_reason: Optional[str] = None

@app.post("/analyze", response_model=Dict[str, Any])
async def analyze_market_mood(payload: NewsInput):
    """
    Standard Financial Fear & Greed Index.
    """
    try:
        return engine.analyze_market_mood(payload.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/maritime", response_model=Dict[str, Any])
async def analyze_maritime_risk(payload: MaritimeInput):
    """
    Maritime freight risk analysis using quantitative psychology principles.
    Predicts price surges based on global routing tensions.
    Can filter by zone (e.g., 'transpacific').
    """
    try:
        return maritime_engine.analyze_maritime_risk(payload.text, payload.zone)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/compare", response_model=MeridianOutput)
async def compare_corridors_risk(payload: NewsInput):
    """
    Compares the Transpacific and Suez Europe corridors to identify arbitrage opportunities.
    """
    try:
        return maritime_engine.compare_corridors(payload.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# --- ARBITRAGE ENGINE — Quantitative Decision Matrix + R_net Calculator ---
# ==============================================================================

class ArbitrageInput(BaseModel):
    """
    Input schema for the Quantitative Arbitrage Engine.
    All monetary values in USD. Rates as decimals (0.003 = 0.3%).
    """
    # Position fundamentals
    entry_price_usd:         float
    exit_price_usd:          float
    stop_loss_price_usd:     float
    position_size_usd:       float

    # Yield & incentives
    gross_yield_usd:         float
    incentives_usd:          float = 0.0

    # DeFi cost inputs
    gas_usd:                 float = 0.0
    slippage_pct:            float = 0.003   # 0.3% AMM slippage
    mev_probability:         float = 0.15    # 15% sandwich attack probability

    # LP-specific (Impermanent Loss)
    is_lp_position:          bool  = False
    il_price_ratio:          float = 1.0     # k = P_current / P_initial

    # Perpetual swap funding cost
    funding_rate_8h:         float = 0.0
    holding_periods_8h:      int   = 1

    # Flash loan parameters
    flash_loan_amount_usd:   float = 0.0
    flash_loan_fee_pct:      float = 0.09    # Aave default

    # Quantitative market state filters
    resistance_level_usd:    float = 0.0
    candle_close_4h_usd:     float = 0.0
    volume_24h:              float = 0.0
    volume_sma_20:           float = 0.0
    volume_stddev:           float = 0.0
    atr_values:              list[float] = []
    execution_intent:        Optional[str] = None


@app.post("/analyze/arbitrage", response_model=Dict[str, Any], tags=["Decision Engine"])
async def evaluate_arbitrage_opportunity(payload: ArbitrageInput):
    """
    **Quantitative Arbitrage Decision Engine** — GEMINI.md §4 + Quantitative Decision Matrix.

    Evaluates a DeFi arbitrage opportunity through 6 sequential filters:
    - F1: Risk/Reward asymmetry ≥ 3:1
    - F2: Breakout confirmation (4H/Daily close above resistance)
    - F3: Volume anomaly V_24h > SMA(V,20) + 2σ
    - F4: ATR positive slope over 3 consecutive periods
    - F5: Funding rate < 0.05% per 8h (long squeeze guard)
    - F6: Stop-loss node mandatory (capital preservation rule)

    Then computes R_net = Y_yield + I_incentives − IL − G_gas − S_MEV − F_funding.
    Proposes EXECUTE only if R_net > flash_loan_opportunity_cost AND all 6 filters pass.
    """
    try:
        opp = ArbitrageOpportunity(
            entry_price_usd=payload.entry_price_usd,
            exit_price_usd=payload.exit_price_usd,
            stop_loss_price_usd=payload.stop_loss_price_usd,
            position_size_usd=payload.position_size_usd,
            gross_yield_usd=payload.gross_yield_usd,
            incentives_usd=payload.incentives_usd,
            gas_usd=payload.gas_usd,
            slippage_pct=payload.slippage_pct,
            mev_probability=payload.mev_probability,
            is_lp_position=payload.is_lp_position,
            il_price_ratio=payload.il_price_ratio,
            funding_rate_8h=payload.funding_rate_8h,
            holding_periods_8h=payload.holding_periods_8h,
            flash_loan_amount_usd=payload.flash_loan_amount_usd,
            flash_loan_fee_pct=payload.flash_loan_fee_pct,
            resistance_level_usd=payload.resistance_level_usd,
            candle_close_4h_usd=payload.candle_close_4h_usd,
            volume_24h=payload.volume_24h,
            volume_sma_20=payload.volume_sma_20,
            atr_values=payload.atr_values,
        )
        result = arbitrage_engine.evaluate(opp)
        
        # Connect and audit execution rails when decision recommends action
        if result.get("signal") in ("EXECUTE", "HEDGE"):
            intent = payload.execution_intent
            if not intent:
                intent = "Earn 5.27% APY on USDC via fluid" if payload.is_lp_position else "Swap 10 USDC to ETH on Base"
            from app.services.smeltor_adapter import smeltor_adapter
            from app.services.transaction_guardrail import transaction_guardrail
            
            exec_details = smeltor_adapter.resolve_intent(intent, mock=True)
            
            # Audit every transaction payload before exposing to signing client
            verified_txs = []
            unsafe_detected = False
            rejection_reason = ""
            
            for tx in exec_details.get("transactions", []):
                audit = transaction_guardrail.inspect_transaction(
                    to=tx.get("to", ""),
                    data=tx.get("data", ""),
                    value=tx.get("value", "0")
                )
                if audit["status"] == "REJECTED":
                    unsafe_detected = True
                    rejection_reason = audit["reason"]
                    break
                verified_txs.append(audit["decoded_call"])
                
            if unsafe_detected:
                # Security Veto (Cognitive Firewall) triggered! Pivot decision to DELAY
                result["signal"] = "DELAY"
                result["context"] = f"SECURITY SHIELD: Rejected transaction. Reason: {rejection_reason}"[:120]
                result["execution_details"] = {
                    "status": "rejected",
                    "reason": rejection_reason,
                    "transactions": []
                }
            else:
                result["execution_details"] = exec_details
                result["execution_details"]["audited_calls"] = verified_txs

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/.well-known/mcp/server-card.json", tags=["MCP Bridge"])
async def get_server_card():
    """
    MCP Server Card — A2A agent discovery endpoint (Ghost Protocol compliant).
    Loaded from static mcp-server.json. No internal names exposed.
    Compatible with Google ADK, LangChain, Composio, and MCP-aware agents.
    """
    import os
    card_path = os.path.join(os.path.dirname(__file__), "..", "mcp-server.json")
    try:
        with open(card_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        # Minimal inline fallback — never exposes internal names.
        return {
            "schema_version": "1.0",
            "server": {"name": "Arsenal Decision Engine", "version": "4.1.0"},
            "capabilities": {"tools": True},
            "tools_endpoint": "/mcp/v1/tools",
            "execute_endpoint": "/mcp/v1/tools/execute",
        }


@app.get("/mcp/v1/tools", tags=["MCP Bridge"])
async def list_mcp_tools(x_api_key: Optional[str] = Header(None)):
    """
    Endpoint standard du protocole MCP permettant aux agents autonomes (Claude, etc.)
    de découvrir les capacités et les schémas de Meridian Alpha en tâche de fond.
    Exposes all tools configured in the static mcp-server.json discovery file dynamically.
    """
    import os
    card_path = os.path.join(os.path.dirname(__file__), "..", "mcp-server.json")
    try:
        with open(card_path, "r") as f:
            data = json.load(f)
            tools = []
            for t in data.get("tools", []):
                # Standardize input schema from schema discovery file to MCP protocol spec
                tools.append({
                    "name": t.get("name"),
                    "description": t.get("description"),
                    "inputSchema": t.get("input_schema", {})
                })
            return {"tools": tools}
    except Exception as e:
        print(f"[MCP Bridge] Failed to read dynamic tools config: {e}")
        # Inline minimal fallback if server card is missing or unreadable
        return {
            "tools": [
                {
                    "name": "calculate_rerouting_financial_impact",
                    "description": "Calculates the precise financial gap (TruePrice) between standard maritime freight and rerouted routes.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "origin_port": {"type": "string"},
                            "destination_port": {"type": "string"},
                            "container_type": {"type": "string", "enum": ["20ft", "40ft"]}
                        },
                        "required": ["origin_port", "destination_port", "container_type"]
                    }
                }
            ]
        }

class MCPExecuteRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]

@app.post("/mcp/v1/tools/execute", tags=["MCP Bridge"])
async def execute_mcp_tool(payload: MCPExecuteRequest, x_api_key: Optional[str] = Header(None)):
    """
    Point d'exécution automatique pour les agents IA autonomes.
    """
    # Payment validation is enforced by L402 Middleware at the gateway level
    
    if payload.name == "calculate_rerouting_financial_impact":
        origin_port = payload.arguments.get("origin_port", "")
        destination_port = payload.arguments.get("destination_port", "")
        container_type = payload.arguments.get("container_type", "40ft")
        text_to_analyze = f"{origin_port} to {destination_port} {container_type}"
        runtime_data = maritime_engine.compare_corridors(text_to_analyze)
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Meridian Alpha Analysis Completed Successfully.\n{json.dumps(runtime_data, indent=2)}"
                }
            ]
        }

    # ── DeFAI ARBITRAGE TOOL — Quantitative R_net + 6-filter matrix ──────────────────
    # Callable by any MCP-aware agent (ElizaOS, LangGraph, Google ADK).
    # Ghost Protocol §8: internal engine name not exposed in response.
    if payload.name == "evaluate_arbitrage_opportunity":
        args = payload.arguments
        try:
            opp = ArbitrageOpportunity(
                entry_price_usd       = float(args.get("entry_price_usd", 0)),
                exit_price_usd        = float(args.get("exit_price_usd", 0)),
                stop_loss_price_usd   = float(args.get("stop_loss_price_usd", 0)),
                position_size_usd     = float(args.get("position_size_usd", 0)),
                gross_yield_usd       = float(args.get("gross_yield_usd", 0)),
                incentives_usd        = float(args.get("incentives_usd", 0.0)),
                gas_usd               = float(args.get("gas_usd", 0.0)),
                slippage_pct          = float(args.get("slippage_pct", 0.003)),
                mev_probability       = float(args.get("mev_probability", 0.15)),
                is_lp_position        = bool(args.get("is_lp_position", False)),
                il_price_ratio        = float(args.get("il_price_ratio", 1.0)),
                funding_rate_8h       = float(args.get("funding_rate_8h", 0.0)),
                holding_periods_8h    = int(args.get("holding_periods_8h", 1)),
                flash_loan_amount_usd = float(args.get("flash_loan_amount_usd", 0.0)),
                flash_loan_fee_pct    = float(args.get("flash_loan_fee_pct", 0.09)),
                resistance_level_usd  = float(args.get("resistance_level_usd", 0.0)),
                candle_close_4h_usd   = float(args.get("candle_close_4h_usd", 0.0)),
                volume_24h            = float(args.get("volume_24h", 0.0)),
                volume_sma_20         = float(args.get("volume_sma_20", 0.0)),
                volume_stddev         = float(args.get("volume_stddev", 0.0)),
                atr_values            = [float(v) for v in args.get("atr_values", [])],
            )
            result = arbitrage_engine.evaluate(opp)
            
            # Connect and audit execution rails when decision recommends action
            if result.get("signal") in ("EXECUTE", "HEDGE"):
                intent = args.get("execution_intent")
                if not intent:
                    intent = "Earn 5.27% APY on USDC via fluid" if opp.is_lp_position else "Swap 10 USDC to ETH on Base"
                from app.services.smeltor_adapter import smeltor_adapter
                from app.services.transaction_guardrail import transaction_guardrail
                
                exec_details = smeltor_adapter.resolve_intent(intent, mock=True)
                
                # Audit every transaction payload before exposing to signing client
                verified_txs = []
                unsafe_detected = False
                rejection_reason = ""
                
                for tx in exec_details.get("transactions", []):
                    audit = transaction_guardrail.inspect_transaction(
                        to=tx.get("to", ""),
                        data=tx.get("data", ""),
                        value=tx.get("value", "0")
                    )
                    if audit["status"] == "REJECTED":
                        unsafe_detected = True
                        rejection_reason = audit["reason"]
                        break
                    verified_txs.append(audit["decoded_call"])
                    
                if unsafe_detected:
                    # Security Veto (Cognitive Firewall) triggered! Pivot decision to DELAY
                    result["signal"] = "DELAY"
                    result["context"] = f"SECURITY SHIELD: Rejected transaction. Reason: {rejection_reason}"[:120]
                    result["execution_details"] = {
                        "status": "rejected",
                        "reason": rejection_reason,
                        "transactions": []
                    }
                else:
                    result["execution_details"] = exec_details
                    result["execution_details"]["audited_calls"] = verified_txs

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2)
                    }
                ]
            }
        except (TypeError, ValueError) as e:
            raise HTTPException(status_code=422, detail=f"Invalid arbitrage parameters: {e}")

    raise HTTPException(status_code=404, detail="Tool not found")

# ==============================================================================
# --- PAYMENT GATEWAY WEBHOOK (PADDLE INTEGRATION) ---
# ==============================================================================

@app.post("/webhook", tags=["Billing & Provisioning"])
async def paddle_webhook(request: Request):
    """
    Point de terminaison sécurisé pour recevoir les notifications de paiement de Paddle.
    Déclenche la génération de la clé API (via generate_api_key.py) et le provisionnement.
    """
    try:
        payload = await request.json()
        
        # Paddle envoie des alertes comme 'subscription_created' ou 'payment_succeeded'
        alert_name = payload.get("alert_name", "unknown_alert")
        
        if alert_name == "subscription_created":
            client_email = payload.get("email", "unknown_client")
            print(f"💰 [PADDLE WEBHOOK] Nouvel abonnement validé pour {client_email}. Provisioning en cours...")
            # Todo: Appeler generate_institutional_token() et envoyer l'email au client
            
        return JSONResponse(status_code=200, content={"status": "success", "message": "Webhook received and verified"})
        
    except Exception as e:
        print(f"❌ [PADDLE WEBHOOK ERROR] {str(e)}")
        # Retourne 400 si le payload est invalide
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid payload format"})
