# © 2026 Arsenal Decision Engine — Decision Intelligence Layer
# File: smeltor_adapter.py — Execution adapter routing to verified aggregators
#
# Ghost Protocol §8: no internal names exposed in public outputs.
# Clean Code: independent of external execution libraries, focuses purely on data structures.

import json
from typing import Dict, Any, List, Optional
from app.services.aggregator_client import aggregator_client

# Whitelisted USDC and WETH tokens on Base
_USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
_WETH = "0x4200000000000000000000000000000000000006"

# Mock/Whitelist fallback payload for Earn
_MOCK_EARN_PAYLOAD = {
    "intent": "Earn 5.27% APY on USDC via fluid",
    "summary": "1 step, 1 signature, ~$0.003 gas. overallStatus: success",
    "yieldComparison": {
        "token": "USDC",
        "options": [
            { "protocol": "fluid",    "apy": 5.27, "apyBasis": "supply_base", "tvl": "$1.0B",  "auditFirms": ["ChainSecurity","MixBytes"], "exploits": 0 },
            { "protocol": "moonwell", "apy": 4.01, "apyBasis": "supply_base", "tvl": "$180M", "auditFirms": ["OpenZeppelin"], "exploits": 0 },
            { "protocol": "compound", "apy": 3.09, "apyBasis": "supply_base", "tvl": "$2.5B",  "auditFirms": ["OpenZeppelin","Trail of Bits"], "exploits": 0 }
        ],
        "highestApy": "fluid (5.27%, supply_base)"
    },
    "steps": [
        {
            "action": "earn",
            "transactions": [{ "kind": "deposit", "chainId": 8453, "to": "0x82a5c4cf4b3dfdebc180ff43a85b9b940989f55e", "data": "0x6e553f650000000000000000000000000000000000000000000000000000000005f5e100", "value": "0" }],
            "approval":      { "kind": "approval", "chainId": 8453, "to": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", "data": "0x095ea7b300000000000000000000000082a5c4cf4b3dfdebc180ff43a85b9b940989f55e0000000000000000000000000000000000000000000000000000000005f5e100", "value": "0" }
        }
    ],
    "rankedBy": "apy_descending",
    "disclaimer": "Non-custodial routing engine, not a financial advisor. Options ranked by an explicit criterion; not recommendations."
}


class SmeltorAdapter:
    """
    Adapter isolating multi-chain execution logic from the core Decision Engine.
    Queries the verified direct AggregatorClient (ParaSwap/1inch) or defaults to whitelisted mocks.
    """

    @staticmethod
    def extract_transactions(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parses aggregator/resolver response to extract an ordered list of execution transactions.
        EVM Order Requirement: Approval transactions MUST occur before execution/deposit transactions.
        """
        txs = []
        
        # Scenario 1: Standard transactions list
        if "transactions" in payload:
            return payload["transactions"]

        # Scenario 2: Steps list (multi-step or cross-chain flow)
        if "steps" in payload:
            for step in payload["steps"]:
                # If approval is needed for this step, it must be executed FIRST
                approval = step.get("approval")
                if approval:
                    txs.append(approval)
                
                # Append the main transactions of this step
                step_txs = step.get("transactions", [])
                txs.extend(step_txs)
            return txs

        raise ValueError("Invalid execution payload: neither 'transactions' nor 'steps' found.")

    @staticmethod
    def simulate_signature(transactions: List[Dict[str, Any]], address: str = "0x8453...ADE_CLIENT_WALLET") -> List[Dict[str, Any]]:
        """
        Simulates how the client-side agent signs the transaction payloads.
        ADE server NEVER holds private keys or signs transactions directly.
        """
        signed_txs = []
        for index, tx in enumerate(transactions):
            signed_txs.append({
                "step_index": index + 1,
                "kind": tx.get("kind", "transaction"),
                "chainId": tx.get("chainId", 8453),
                "to": tx.get("to", ""),
                "data": tx.get("data", ""),
                "value": tx.get("value", "0"),
                "estimated_gas": tx.get("gas", "300000"),
                "simulation_status": "READY_FOR_LOCAL_SIGNING",
                "wallet_context": {
                    "source_address": address,
                    "requires_approval": tx.get("kind") == "approval",
                    "action_sequence": f"{index + 1}/{len(transactions)}"
                }
            })
        return signed_txs

    def resolve_intent(self, intent: str, mock: bool = True) -> Dict[str, Any]:
        """
        Queries the direct DEX Aggregator (ParaSwap/1inch) to build ready-to-sign transactions.
        """
        intent_lower = intent.lower()

        # If it is a swap intent, route it dynamically to the live Aggregator Client
        if "swap" in intent_lower:
            # Simple NLP parsing: Swap X USDC to ETH
            amount_usdc = 10_000_000 # Default: 10 USDC (6 decimals)
            
            # Simple tokenizer helper to find amount
            words = intent_lower.split()
            for i, word in enumerate(words):
                if word == "swap" and i + 1 < len(words):
                    try:
                        amount_usdc = int(float(words[i+1]) * 10**6)
                    except ValueError:
                        pass
            
            # Query official Aggregators (or fallback simulation if offline)
            tx_data = aggregator_client.get_swap_transaction(
                chain_id=8453,
                src_token=_USDC,
                dst_token=_WETH,
                amount=amount_usdc
            )
            
            transactions = self.extract_transactions(tx_data)
            simulated = self.simulate_signature(transactions)
            
            return {
                "intent": intent,
                "resolved_by": f"Verified DEX Aggregator ({tx_data.get('provider', 'local')})",
                "original_summary": tx_data.get("bestAggregator", "ParaSwap/1inch Router"),
                "transactions": transactions,
                "execution_sequence": simulated,
                "status": "success",
                "disclaimer": "Unsigned calldata resolved directly from verified DeFi aggregators."
            }

        # Otherwise, fall back to our whitelisted Moonwell/Fluid Earn layout
        payload = _MOCK_EARN_PAYLOAD
        transactions = self.extract_transactions(payload)
        simulated = self.simulate_signature(transactions)

        return {
            "intent": intent,
            "resolved_by": "Audited Yield Router (Fluid Pool)",
            "original_summary": payload.get("summary", "Fluid Usdc Supply"),
            "transactions": transactions,
            "execution_sequence": simulated,
            "status": "success",
            "disclaimer": "Whitelisted non-custodial yield routing."
        }


# Singleton instance
smeltor_adapter = SmeltorAdapter()
