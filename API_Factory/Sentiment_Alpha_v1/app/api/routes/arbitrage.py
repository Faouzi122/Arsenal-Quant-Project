# © 2026 Arsenal Decision Engine — Decision Intelligence Layer
# File: arbitrage.py — API Endpoint for MEV Risk Audits
# Clean Architecture compliant (Uncle Bob). Stateless REST (Torvalds).

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any
from app.core.mev_service import mev_service

router = APIRouter(prefix="/api/v1/arbitrage", tags=["MEV Arbitrage Audit"])

class MEVAuditRequest(BaseModel):
    victim_weth_in: float = Field(
        default=10.0, 
        description="Taille en WETH de la transaction de la victime à analyser (ex: 10 WETH)"
    )
    attacker_weth_in: float = Field(
        default=50.0, 
        description="Taille en WETH de la transaction de l'attaquant (front-run / sandwich size)"
    )

@router.post("/mev", response_model=Dict[str, Any])
async def audit_mev_risk(payload: MEVAuditRequest):
    """
    **Audit déterministe de risque MEV** (Sandwich Attack)
    Interroge l'état réel des réserves Uniswap V2 USDC/WETH sur Ethereum Mainnet,
    exécute une simulation d'attaque sandwich $O(1)$, et évalue la perte évitable (Proof of Savings).
    Le payload retourné inclut un Sceau Cryptographique (signature HMAC-SHA256) garantissant l'intégrité du calcul.
    """
    if payload.victim_weth_in <= 0 or payload.attacker_weth_in <= 0:
        raise HTTPException(status_code=422, detail="Les montants d'entrée doivent être strictement supérieurs à zéro.")
    try:
        decision = mev_service.evaluate_sandwich_risk(
            victim_weth_in=payload.victim_weth_in,
            attacker_weth_in=payload.attacker_weth_in
        )
        return decision
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Échec de la simulation MEV on-chain : {str(e)}")
