# © 2026 Arsenal Decision Engine — Decision Intelligence Layer
# File: mev_service.py — Deterministic MEV Sandwich Audit & Cryptographic Seal
# Clean Architecture compliant (Uncle Bob). O(1) Reserves math (Torvalds).

import os
import time
import hmac
import hashlib
import json
from abc import ABC, abstractmethod
from web3 import Web3
from pydantic import BaseModel

# ==============================================================================
# 1. CONTRAT DE LECTURE BLOCKCHAIN (INVERSION DE DÉPENDANCE)
# ==============================================================================
class IBlockchainStateReader(ABC):
    @abstractmethod
    def get_reserves(self, pool_address: str) -> tuple:
        """Doit retourner (reserve0, reserve1) de la pool."""
        pass

# ==============================================================================
# 2. ADAPTATEUR CONCRET (DÉTAIL D'IMPLÉMENTATION)
# ==============================================================================
class UniswapV2RPCAdapter(IBlockchainStateReader):
    def __init__(self, rpc_url: str, timeout_seconds: float = 1.5):
        # CIRCUIT BREAKER : Rejet immédiat si timeout dépassé (Loi de Torvalds)
        self.w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': timeout_seconds}))
        self.pair_abi = '''[{"constant":true,"inputs":[],"name":"getReserves",
        "outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},
        {"internalType":"uint112","name":"_reserve1","type":"uint112"},
        {"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],
        "payable":false,"stateMutability":"view","type":"function"}]'''

    def get_reserves(self, pool_address: str) -> tuple:
        if not self.w3.is_connected():
            raise ConnectionError("[CIRCUIT BREAKER] Échec de connexion au nœud RPC Ethereum.")
        try:
            checksum_addr = self.w3.to_checksum_address(pool_address)
            contract = self.w3.eth.contract(address=checksum_addr, abi=self.pair_abi)
            reserves = contract.functions.getReserves().call()
            return reserves[0], reserves[1]
        except Exception as e:
            raise RuntimeError(f"[RPC ERROR] Impossible d'interroger la pool : {str(e)}")

# ==============================================================================
# 3. SERVICE D'ORCHESTRATION MÉTIER
# ==============================================================================
class MEVService:
    def __init__(self):
        # Configuration des endpoints et de la pool
        self.rpc_url = os.getenv("ETHEREUM_RPC_URL", "https://ethereum-rpc.publicnode.com")
        self.pool_address = os.getenv("USDC_WETH_POOL_ADDRESS", "0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc")
        self.secret_key = os.getenv("MEV_SIGNING_SECRET", "ANTIGRAVITY-SECURE-SECRET-KEY-2026").encode()
        
        # Initialisation de l'adaptateur
        self.adapter = UniswapV2RPCAdapter(self.rpc_url)

    @staticmethod
    def _get_amount_out(amount_in: float, reserve_in: float, reserve_out: float) -> float:
        """Formule de produit constant Uniswap V2 : x * y = k (avec 0.3% de frais)"""
        amount_in_with_fee = amount_in * 997.0
        numerator = amount_in_with_fee * reserve_out
        denominator = (reserve_in * 1000.0) + amount_in_with_fee
        return numerator / denominator

    def evaluate_sandwich_risk(self, victim_weth_in: float, attacker_weth_in: float) -> dict:
        """
        Interroge la blockchain et simule l'impact d'une attaque sandwich.
        Retourne un dictionnaire conforme au standard JSON décisionnel §4.
        """
        start_time = time.time()
        
        # 1. Ancrage au réel
        res0, res1 = self.adapter.get_reserves(self.pool_address)
        
        # USDC (token0, 6 decimals) | WETH (token1, 18 decimals)
        reserve_usdc = res0 / 1e6
        reserve_weth = res1 / 1e18
        spot_price = reserve_usdc / reserve_weth
        
        # 2. Simulation mathématique O(1) de l'attaque
        # Front-Run
        att_usdc_out_1 = self._get_amount_out(attacker_weth_in, reserve_weth, reserve_usdc)
        res_w_1 = reserve_weth + attacker_weth_in
        res_u_1 = reserve_usdc - att_usdc_out_1
        
        # Victime
        vic_usdc_out = self._get_amount_out(victim_weth_in, res_w_1, res_u_1)
        res_w_2 = res_w_1 + victim_weth_in
        res_u_2 = res_u_1 - vic_usdc_out
        
        # Back-Run
        att_weth_out_2 = self._get_amount_out(att_usdc_out_1, res_u_2, res_w_2)
        
        # Calcul du profit brut de l'attaquant
        profit_net_weth = att_weth_out_2 - attacker_weth_in
        
        # 3. Calcul de la perte évitée (Proof of Savings)
        avoided_loss_usd = 0.0
        if profit_net_weth > 0:
            avoided_loss_usd = round(profit_net_weth * spot_price, 2)
            signal = "DELAY"
            context = f"MEV sandwich risk: attacker profit {profit_net_weth:.4f} WETH. Execution delayed."
        else:
            signal = "EXECUTE"
            context = "No sandwich risk detected. Clear path to execute."

        # Censure de l'incertitude : Volatilité selon l'écart
        volatility = "LOW"
        if profit_net_weth > 0.05:
            volatility = "HIGH"
        elif profit_net_weth > 0.01:
            volatility = "MEDIUM"

        # Confiance basée sur la fraîcheur de l'exécution
        latency_ms = (time.time() - start_time) * 1000
        confidence = round(min(0.99, 1.0 - (latency_ms / 3000.0)), 2)

        # 4. Construction du payload de décision standardisé §4
        payload = {
            "value": round(profit_net_weth, 6),
            "change_pct": round((profit_net_weth / reserve_weth) * 100, 6),
            "volatility": volatility,
            "trend": "UP" if profit_net_weth > 0 else "DOWN",
            "confidence_score": confidence,
            "signal": signal,
            "context": context[:120],
            "data_freshness_seconds": 0,
            "source": "Antigravity Engine v1.0",
            # Champs étendus exigés par le CEO
            "avoided_loss_usd": avoided_loss_usd,
            "latency_ms": round(latency_ms, 2)
        }

        # 5. Sceau Cryptographique (HMAC-SHA256) pour garantir l'authenticité
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        signature = hmac.new(self.secret_key, payload_bytes, hashlib.sha256).hexdigest()
        payload["cryptographic_signature"] = signature

        return payload

mev_service = MEVService()
